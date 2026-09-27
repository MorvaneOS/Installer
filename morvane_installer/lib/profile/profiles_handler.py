import importlib.util
import inspect
import sys
from collections import Counter
from pathlib import Path
from tempfile import NamedTemporaryFile
from types import ModuleType
from typing import TYPE_CHECKING, NotRequired, TypedDict

from morvane_installer.default_profiles.profile import CustomSetting, GreeterType, Profile
from morvane_installer.lib.hardware import GfxDriver, GfxPackage
from morvane_installer.lib.log import debug, error, info, warn
from morvane_installer.lib.models.profile import ProfileConfiguration
from morvane_installer.lib.networking import fetch_data_from_url
from morvane_installer.lib.translationhandler import tr

if TYPE_CHECKING:
	from morvane_installer.lib.installer import Installer


def _write_session_bus_wrapper(install_session: Installer, name: str, wrapped: str) -> None:
	"""
	MorvaneOS: on systemd the user manager provides a D-Bus session bus before any
	session starts. runit doesn't, and GNOME, Cosmic, Hyprland, Sway's bar, portals
	and notification daemons need one. X sessions under LightDM would get one from
	dbus-runit's xinitrc.d script, but Wayland sessions get nothing. This wraps a
	display manager's session script, re-running itself under dbus-run-session
	whenever there's no bus yet.

	Some sessions (Artix's niri) start themselves with `dbus-launch --exit-with-session`
	for the same reason. Without an X display to watch, that bus exits straight away and
	leaves the session pointed at a dead bus, so the wrapper drops it: there's always a
	bus by the time the session runs. Display managers pass the session command either
	split into words (LightDM) or as one string (SDDM), so both are handled.

	It also starts PipeWire. The installer's XDG autostart entry for it (see
	applications/audio.py) only runs in desktops that handle autostart: not window
	managers, and not GNOME, whose sysvinit session doesn't. The launcher does nothing
	when PipeWire is already running, so desktops that also autostart it are fine.
	"""
	wrapper = install_session.target / 'usr/local/bin' / name
	wrapper.parent.mkdir(parents=True, exist_ok=True)
	wrapper.write_text(
		'#!/bin/sh\n'
		"# MorvaneOS: give the session a D-Bus session bus and PipeWire, which runit doesn't start\n"
		'case "$1" in\n'
		'dbus-launch) [ "$2" = --exit-with-session ] && shift 2 ;;\n'
		'\'dbus-launch --exit-with-session \'*) cmd=${1#dbus-launch --exit-with-session }; shift; set -- "$cmd" "$@" ;;\n'
		'esac\n'
		'if [ -z "$DBUS_SESSION_BUS_ADDRESS" ] && [ ! -S "${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/bus" ]; then\n'
		'\texec dbus-run-session "$0" "$@"\n'
		'fi\n'
		# In a subshell so it isn't left a zombie child of the session once it exits
		'if command -v artix-pipewire-launcher >/dev/null; then\n'
		'\t(artix-pipewire-launcher >/dev/null 2>&1 &)\n'
		'fi\n'
		f'exec {wrapped} "$@"\n'
	)
	wrapper.chmod(0o755)


class ProfileSerialization(TypedDict):
	main: NotRequired[str]
	details: NotRequired[list[str]]
	custom_settings: NotRequired[dict[str, dict[CustomSetting, str | None]]]
	path: NotRequired[str]


class ProfileHandler:
	def __init__(self) -> None:
		self._profiles: list[Profile] | None = None

		# special variable to keep track of a profile url configuration
		# it is merely used to be able to export the path again when a user
		# wants to save the configuration
		self._url_path: str | None = None

	def to_json(self, profile: Profile | None) -> ProfileSerialization:
		"""
		Serialize the selected profile setting to JSON
		"""
		data: ProfileSerialization = {}

		if profile is not None:
			data = {
				'main': profile.name,
				'details': [profile.name for profile in profile.current_selection],
				'custom_settings': {profile.name: profile.custom_settings for profile in profile.current_selection},
			}

		if self._url_path is not None:
			data['path'] = self._url_path

		return data

	def parse_profile_config(self, profile_config: ProfileSerialization) -> Profile | None:
		"""
		Deserialize JSON configuration for profile
		"""
		profile: Profile | None = None

		# the order of these is important, we want to
		# load all the default_profiles from url and custom
		# so that we can then apply whatever was specified
		# in the main/detail sections
		if url_path := profile_config.get('path', None):
			self._url_path = url_path
			local_path = Path(url_path)

			if local_path.is_file():
				profiles = self._process_profile_file(local_path)
				self.remove_custom_profiles(profiles)
				self.add_custom_profiles(profiles)
			else:
				self._import_profile_from_url(url_path)

		if main := profile_config.get('main', None):
			profile = self.get_profile_by_name(main) if main else None

		if not profile:
			return None

		valid_sub_profiles: list[Profile] = []
		invalid_sub_profiles: list[str] = []
		details: list[str] = profile_config.get('details', [])

		if details:
			for detail in filter(None, details):
				# [2024-04-19] TODO: Backwards compatibility after naming change: https://github.com/archlinux/archinstall/pull/2421
				# 'Kde' is deprecated, remove this block in a future version
				if detail == 'Kde':
					detail = 'KDE Plasma'

				if sub_profile := self.get_profile_by_name(detail):
					valid_sub_profiles.append(sub_profile)
				else:
					invalid_sub_profiles.append(detail)

			if invalid_sub_profiles:
				info('No profile definition found: {}'.format(', '.join(invalid_sub_profiles)))

		custom_settings = profile_config.get('custom_settings', {})
		profile.current_selection = valid_sub_profiles

		for sub_profile in valid_sub_profiles:
			sub_profile_settings = custom_settings.get(sub_profile.name, {})
			if sub_profile_settings:
				sub_profile.custom_settings = sub_profile_settings

		return profile

	@property
	def profiles(self) -> list[Profile]:
		"""
		List of all available default_profiles
		"""
		self._profiles = self._profiles or self._find_available_profiles()
		return self._profiles

	def add_custom_profiles(self, profiles: Profile | list[Profile]) -> None:
		if not isinstance(profiles, list):
			profiles = [profiles]

		for profile in profiles:
			self.profiles.append(profile)

		self._verify_unique_profile_names(self.profiles)

	def remove_custom_profiles(self, profiles: Profile | list[Profile]) -> None:
		if not isinstance(profiles, list):
			profiles = [profiles]

		remove_names = [p.name for p in profiles]
		self._profiles = [p for p in self.profiles if p.name not in remove_names]

	def get_profile_by_name(self, name: str) -> Profile | None:
		return next(filter(lambda x: x.name == name, self.profiles), None)

	def get_top_level_profiles(self) -> list[Profile]:
		return [p for p in self.profiles if p.is_top_level_profile()]

	def get_server_profiles(self) -> list[Profile]:
		return [p for p in self.profiles if p.is_server_type_profile()]

	def get_desktop_profiles(self) -> list[Profile]:
		return [p for p in self.profiles if p.is_desktop_type_profile()]

	def get_custom_profiles(self) -> list[Profile]:
		return [p for p in self.profiles if p.is_custom_type_profile()]

	def install_greeter(self, install_session: Installer, greeter: GreeterType) -> None:
		packages = []
		service = None
		service_disable = None

		# MorvaneOS: GDM can't run without systemd (the menu no longer offers it), but
		# older configuration files may still ask for it
		if greeter == GreeterType.Gdm:
			warn('GDM needs systemd and does not work on MorvaneOS; installing SDDM instead')
			greeter = GreeterType.Sddm

		match greeter:
			case GreeterType.LightdmSlick:
				packages = ['lightdm', 'lightdm-slick-greeter']
				service = ['lightdm']
			case GreeterType.Lightdm:
				packages = ['lightdm', 'lightdm-gtk-greeter']
				service = ['lightdm']
			case GreeterType.Sddm:
				packages = ['sddm']
				service = ['sddm']
			case GreeterType.Gdm:
				packages = ['gdm']
				service = ['gdm']
			case GreeterType.Ly:
				packages = ['ly']
				service = ['ly@tty1']
				service_disable = ['getty@tty1']
			case GreeterType.CosmicSession:
				packages = ['cosmic-greeter']
				service = ['cosmic-greeter']
			case GreeterType.PlasmaLoginManager:
				packages = ['plasma-login-manager']
				service = ['plasmalogin']
			case GreeterType.GreetdDms:
				packages = ['greetd']
				service = ['greetd']

		if packages:
			install_session.add_additional_packages(packages)
		if service:
			install_session.enable_service(service)
		if service_disable:
			install_session.disable_service(service_disable)

		# MorvaneOS: sessions get their D-Bus session bus from these wrappers
		match greeter:
			case GreeterType.Sddm:
				_write_session_bus_wrapper(install_session, 'morvane-wayland-session', '/usr/share/sddm/scripts/wayland-session')
				sddm_conf = install_session.target / 'etc/sddm.conf.d/10-morvane-session-bus.conf'
				sddm_conf.parent.mkdir(parents=True, exist_ok=True)
				sddm_conf.write_text('[Wayland]\nSessionCommand=/usr/local/bin/morvane-wayland-session\n')
			case GreeterType.Lightdm | GreeterType.LightdmSlick:
				_write_session_bus_wrapper(install_session, 'morvane-lightdm-session', '/etc/lightdm/Xsession')
				# lightdm.conf is read after lightdm.conf.d/ and sets session-wrapper
				# itself, so it has to be changed there
				path = install_session.target / 'etc/lightdm/lightdm.conf'
				path.write_text(
					path.read_text().replace(
						'session-wrapper=/etc/lightdm/Xsession',
						'session-wrapper=/usr/local/bin/morvane-lightdm-session',
					)
				)

		# slick-greeter requires a config change
		if greeter == GreeterType.LightdmSlick:
			path = install_session.target.joinpath('etc/lightdm/lightdm.conf')
			with open(path) as file:
				filedata = file.read()

			filedata = filedata.replace('#greeter-session=example-gtk-gnome', 'greeter-session=lightdm-slick-greeter')

			with open(path, 'w') as file:
				file.write(filedata)

		if greeter == GreeterType.GreetdDms:
			greetd_config = install_session.target / 'etc/greetd/config.toml'
			greetd_config.parent.mkdir(parents=True, exist_ok=True)
			greetd_config.write_text(
				'[terminal]\n'
				'vt = 1\n'
				'\n'
				'[default_session]\n'
				'user = "greeter"\n'
				'command = "/usr/share/quickshell/dms/Modules/Greetd/assets/dms-greeter --command niri -p /usr/share/quickshell/dms"\n',
			)

			tmpfiles = install_session.target / 'etc/tmpfiles.d/dms-greeter.conf'
			tmpfiles.parent.mkdir(parents=True, exist_ok=True)
			tmpfiles.write_text(
				'#  Path                    Mode User    Group   Age Argument\n'
				'd /var/cache/dms-greeter   0750 greeter greeter -\n'
				'd /var/lib/greeter         0755 greeter greeter -\n',
			)

	def install_gfx_driver(self, install_session: Installer, driver: GfxDriver) -> None:
		debug(f'Installing GFX driver: {driver.value}')

		driver_pkgs = driver.gfx_packages()
		pkg_names = [p.value for p in driver_pkgs]

		# For Nvidia open kernel modules, use nvidia-open instead of nvidia-open-dkms
		# when all selected kernels are mainline (no dkms needed). This avoids
		# installing dkms + kernel headers and speeds up installation.
		if driver == GfxDriver.NvidiaOpenKernel:
			needs_dkms = any('-' in k for k in install_session.kernels)

			if needs_dkms:
				headers = [f'{kernel}-headers' for kernel in install_session.kernels]
				install_session.add_additional_packages(headers)
			else:
				pkg_names = [GfxPackage.NvidiaOpen.value if p == GfxPackage.NvidiaOpenDkms.value else p for p in pkg_names]
				pkg_names = [p for p in pkg_names if p != GfxPackage.Dkms.value]

		install_session.add_additional_packages(pkg_names)

	def install_profile_config(self, install_session: Installer, profile_config: ProfileConfiguration) -> None:
		profile = profile_config.profile

		if not profile:
			return

		if profile_config.gfx_driver and (profile.is_xorg_type_profile() or profile.is_desktop_profile()):
			self.install_gfx_driver(install_session, profile_config.gfx_driver)

		profile.install(install_session)

		if profile_config.greeter:
			self.install_greeter(install_session, profile_config.greeter)

	def _import_profile_from_url(self, url: str) -> None:
		"""
		Import default_profiles from a url path
		"""
		try:
			data = fetch_data_from_url(url)
			b_data = bytes(data, 'utf-8')

			with NamedTemporaryFile(delete=False, suffix='.py') as fp:
				fp.write(b_data)
				filepath = Path(fp.name)

			profiles = self._process_profile_file(filepath)
			self.remove_custom_profiles(profiles)
			self.add_custom_profiles(profiles)
		except ValueError:
			err = tr('Unable to fetch profile from specified url: {}').format(url)
			error(err)

	def _load_profile_class(self, module: ModuleType) -> list[Profile]:
		"""
		Load all default_profiles defined in a module
		"""
		profiles = []
		for v in module.__dict__.values():
			if isinstance(v, type) and v.__module__ == module.__name__:
				bases = inspect.getmro(v)

				if Profile in bases:
					try:
						cls_ = v()
						if isinstance(cls_, Profile):
							profiles.append(cls_)
					except Exception:
						debug(f'Cannot import {module}, it does not appear to be a Profile class')

		return profiles

	def _verify_unique_profile_names(self, profiles: list[Profile]) -> None:
		"""
		All profile names have to be unique, this function will verify
		that the provided list contains only default_profiles with unique names
		"""
		counter = Counter([p.name for p in profiles])
		duplicates = [x for x in counter.items() if x[1] != 1]

		if len(duplicates) > 0:
			err = tr('Profiles must have unique name, but profile definitions with duplicate name found: {}').format(duplicates[0][0])
			error(err)
			sys.exit(1)

	def _is_legacy(self, file: Path) -> bool:
		"""
		Check if the provided profile file contains a
		legacy profile definition
		"""
		with open(file) as fp:
			for line in fp.readlines():
				if '__packages__' in line:
					return True
		return False

	def _process_profile_file(self, file: Path) -> list[Profile]:
		"""
		Process a file for profile definitions
		"""
		if self._is_legacy(file):
			info(f'Cannot import {file} because it is no longer supported, please use the new profile format')
			return []

		if not file.is_file():
			info(f'Cannot find profile file {file}')
			return []

		name = file.name.removesuffix(file.suffix)
		debug(f'Importing profile: {file}')

		try:
			if spec := importlib.util.spec_from_file_location(name, file):
				imported = importlib.util.module_from_spec(spec)
				if spec.loader is not None:
					spec.loader.exec_module(imported)
					return self._load_profile_class(imported)
		except Exception as e:
			error(f'Unable to parse file {file}: {e}')

		return []

	def _find_available_profiles(self) -> list[Profile]:
		"""
		Search the profile path for profile definitions
		"""
		profiles_path = Path(__file__).parents[2] / 'default_profiles'
		profiles = []
		for file in profiles_path.glob('**/*.py'):
			# ignore the abstract base classes
			if file.name == 'profile.py':
				continue
			if file.relative_to(profiles_path).as_posix() in _UNAVAILABLE_PROFILES:
				continue
			profiles += self._process_profile_file(file)

		self._verify_unique_profile_names(profiles)
		return profiles

	def reset_top_level_profiles(self, exclude: list[Profile] = []) -> None:
		"""
		Reset all top level profile configurations, this is usually necessary
		when a new top level profile is selected
		"""
		excluded_profiles = [p.name for p in exclude]
		for profile in self.get_top_level_profiles():
			if profile.name not in excluded_profiles:
				profile.reset()


# MorvaneOS: profiles whose main packages aren't in the Artix repos. Skipped here
# rather than deleted, so merging upstream changes to them stays conflict-free.
_UNAVAILABLE_PROFILES = {
	'desktops/budgie.py',
	'desktops/deepin.py',
	'desktops/enlightenment.py',
	'desktops/niri_dms.py',
	'desktops/qtile.py',
	'desktops/xmonad.py',
	'servers/cockpit.py',
	'servers/tomcat.py',
}

profile_handler = ProfileHandler()
