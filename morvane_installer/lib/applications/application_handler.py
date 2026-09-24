from typing import TYPE_CHECKING

from morvane_installer.applications.audio import AudioApp
from morvane_installer.applications.bluetooth import BluetoothApp
from morvane_installer.applications.firewall import FirewallApp
from morvane_installer.applications.fonts import FontsApp
from morvane_installer.applications.power_management import PowerManagementApp
from morvane_installer.applications.print_service import PrintServiceApp
from morvane_installer.lib.models import Audio
from morvane_installer.lib.models.application import ApplicationConfiguration
from morvane_installer.lib.models.users import User

if TYPE_CHECKING:
	from morvane_installer.lib.installer import Installer


class ApplicationHandler:
	def __init__(self) -> None:
		pass

	def install_applications(self, install_session: Installer, app_config: ApplicationConfiguration, users: list[User] | None = None) -> None:
		if app_config.bluetooth_config and app_config.bluetooth_config.enabled:
			BluetoothApp().install(install_session)

		if app_config.audio_config and app_config.audio_config.audio != Audio.NO_AUDIO:
			AudioApp().install(
				install_session,
				app_config.audio_config,
				users,
			)

		if app_config.power_management_config:
			PowerManagementApp().install(
				install_session,
				app_config.power_management_config,
			)

		if app_config.print_service_config and app_config.print_service_config.enabled:
			PrintServiceApp().install(install_session)

		if app_config.firewall_config:
			FirewallApp().install(
				install_session,
				app_config.firewall_config,
			)

		if app_config.fonts_config:
			FontsApp().install(
				install_session,
				app_config.fonts_config,
			)
