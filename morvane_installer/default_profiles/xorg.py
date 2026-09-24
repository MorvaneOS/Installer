from typing import TYPE_CHECKING, override

from morvane_installer.default_profiles.profile import DisplayServerType, Profile, ProfileType

if TYPE_CHECKING:
	from morvane_installer.lib.installer import Installer


class XorgProfile(Profile):
	def __init__(
		self,
		name: str = 'Xorg',
		profile_type: ProfileType = ProfileType.Xorg,
	):
		super().__init__(
			name,
			profile_type,
			support_gfx_driver=True,
			display_server=DisplayServerType.Xorg,
		)

	@property
	@override
	def packages(self) -> list[str]:
		return [
			'xorg-server',
			'xorg-xinit',
		]

	@override
	def install(self, install_session: Installer) -> None:
		install_session.add_additional_packages(self.packages)
