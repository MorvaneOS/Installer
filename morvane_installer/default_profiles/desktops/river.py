from typing import TYPE_CHECKING, override

from morvane_installer.default_profiles.profile import DisplayServerType, GreeterType, Profile, ProfileType
from morvane_installer.lib.models.users import User

if TYPE_CHECKING:
	from morvane_installer.lib.installer import Installer


class RiverProfile(Profile):
	def __init__(self) -> None:
		super().__init__(
			'River',
			ProfileType.WindowMgr,
			support_gfx_driver=True,
			display_server=DisplayServerType.Wayland,
		)

	@property
	@override
	def packages(self) -> list[str]:
		return [
			'morvane-river-theme',  # MorvaneOS look
			'foot',
			'xdg-desktop-portal-wlr',
			# MorvaneOS: river 0.4 in the Artix repos only draws windows; it needs a separate
			# window manager, and none is packaged. river-classic is the usual River
			# (riverctl, rivertile, an example init).
			'river-classic',
		]

	@property
	@override
	def default_greeter_type(self) -> GreeterType:
		return GreeterType.Lightdm

	@override
	def provision(self, install_session: Installer, users: list[User]) -> None:
		# MorvaneOS: River does everything, key bindings included, from ~/.config/river/init,
		# so without one a new user gets a black screen they can't do anything in. The
		# init is river-classic's example in the MorvaneOS look (morvane-river-theme).
		for user in users:
			install_session.arch_chroot('mkdir -p ~/.config/river', run_as=user.username)
			install_session.arch_chroot('cp /usr/share/morvane-river-theme/init ~/.config/river/init', run_as=user.username)
			install_session.arch_chroot('chmod +x ~/.config/river/init', run_as=user.username)
