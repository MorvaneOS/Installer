from typing import override

from morvane_installer.default_profiles.profile import DisplayServerType, GreeterType, Profile, ProfileType
from morvane_installer.lib.installer import Installer
from morvane_installer.lib.models.users import User


class BspwmProfile(Profile):
	def __init__(self) -> None:
		super().__init__(
			'Bspwm',
			ProfileType.WindowMgr,
			support_gfx_driver=True,
			display_server=DisplayServerType.Xorg,
		)

	@property
	@override
	def packages(self) -> list[str]:
		return [
			'morvane-bspwm-theme',  # MorvaneOS look
			'bspwm',
			'sxhkd',
			'dmenu',
			'xdo',
			'rxvt-unicode',
		]

	@property
	@override
	def default_greeter_type(self) -> GreeterType:
		return GreeterType.Lightdm

	@override
	def provision(self, install_session: Installer, users: list[User]) -> None:
		# MorvaneOS: bspwm's examples in the MorvaneOS look (morvane-bspwm-theme)
		for user in users:
			install_session.arch_chroot('mkdir -p ~/.config/bspwm ~/.config/sxhkd', run_as=user.username)
			install_session.arch_chroot('cp /usr/share/morvane-bspwm-theme/bspwmrc ~/.config/bspwm/', run_as=user.username)
			install_session.arch_chroot('cp /usr/share/morvane-bspwm-theme/sxhkdrc ~/.config/sxhkd/', run_as=user.username)
			install_session.arch_chroot('chmod +x ~/.config/bspwm/bspwmrc', run_as=user.username)
