from typing import override

from morvane_installer.default_profiles.profile import DisplayServerType, GreeterType, Profile, ProfileType
from morvane_installer.lib.log import warn
from morvane_installer.lib.packages.packages import package_group_info


class GnomeProfile(Profile):
	def __init__(self) -> None:
		super().__init__(
			'GNOME',
			ProfileType.DesktopEnv,
			support_gfx_driver=True,
			display_server=DisplayServerType.Wayland,
		)

	@property
	@override
	def packages(self) -> list[str]:
		# MorvaneOS: GDM needs systemd (its greeter users come from systemd's userdb), and
		# Artix's gnome-session-sysvinit, which runs the session without systemd, conflicts
		# with it. So: the gnome group minus gdm, plus gnome-session-sysvinit, with SDDM
		# (whose setup also gives the session the D-Bus session bus GNOME needs).
		group = package_group_info('gnome')
		if group is not None:
			gnome = [p for p in group.packages if p != 'gdm']
		else:
			warn('Could not list the gnome package group, installing a minimal GNOME')
			gnome = ['gnome-shell', 'gnome-session', 'gnome-control-center', 'gnome-console', 'nautilus']

		return ['morvane-gnome-theme', *gnome, 'gnome-session-sysvinit', 'gnome-tweaks']

	@property
	@override
	def default_greeter_type(self) -> GreeterType:
		return GreeterType.Sddm
