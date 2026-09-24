from typing import TYPE_CHECKING

from archinstall.lib.hardware import SysInfo
from archinstall.lib.log import debug
from archinstall.lib.models.application import Audio, AudioConfiguration
from archinstall.lib.models.users import User

if TYPE_CHECKING:
	from archinstall.lib.installer import Installer


class AudioApp:
	@property
	def pulseaudio_packages(self) -> list[str]:
		return [
			'pulseaudio',
		]

	@property
	def pipewire_packages(self) -> list[str]:
		return [
			'pipewire',
			'pipewire-alsa',
			'pipewire-jack',
			'pipewire-pulse',
			'gst-plugin-pipewire',
			'libpulse',
			'wireplumber',
		]

	def _enable_pipewire(
		self,
		install_session: Installer,
		users: list[User] | None = None,
	) -> None:
		# MorvaneOS: no systemd user services. Artix's pipewire package ships
		# artix-pipewire-launcher, which starts pipewire, pipewire-pulse and
		# wireplumber; desktops run it at login through XDG autostart. Window
		# managers without autostart support need it added to their own config.
		autostart = install_session.target / 'etc/xdg/autostart/artix-pipewire-launcher.desktop'
		autostart.parent.mkdir(parents=True, exist_ok=True)
		autostart.write_text(
			'[Desktop Entry]\nType=Application\nName=PipeWire\nComment=Start the PipeWire audio server\nExec=artix-pipewire-launcher\nNoDisplay=true\n'
		)

	def install(
		self,
		install_session: Installer,
		audio_config: AudioConfiguration,
		users: list[User] | None = None,
	) -> None:
		debug(f'Installing audio server: {audio_config.audio.value}')

		if audio_config.audio == Audio.NO_AUDIO:
			debug('No audio server selected, skipping installation.')
			return

		if SysInfo.requires_sof_fw():
			install_session.add_additional_packages('sof-firmware')

		if SysInfo.requires_alsa_fw():
			install_session.add_additional_packages('alsa-firmware')

		match audio_config.audio:
			case Audio.PIPEWIRE:
				install_session.add_additional_packages(self.pipewire_packages)
				self._enable_pipewire(install_session, users)
			case Audio.PULSEAUDIO:
				install_session.add_additional_packages(self.pulseaudio_packages)
