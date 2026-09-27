from typing import override

from morvane_installer.default_profiles.profile import DisplayServerType, GreeterType, Profile, ProfileType


class LxqtProfile(Profile):
	def __init__(self) -> None:
		super().__init__(
			'Lxqt',
			ProfileType.DesktopEnv,
			support_gfx_driver=True,
			display_server=DisplayServerType.Xorg,
		)

	# NOTE: SDDM is the only officially supported greeter for LXQt, so unlike other DEs, lightdm is not used here.
	# LXQt works with lightdm, but since this is not supported, we will not default to this.
	# https://github.com/lxqt/lxqt/issues/795
	@property
	@override
	def packages(self) -> list[str]:
		return [
			'morvane-lxqt-theme',  # MorvaneOS look
			'lxqt',
			'breeze-icons',
			'oxygen-icons',
			'xdg-utils',
			# MorvaneOS: Arch's old ttf-freefont is gnu-free-fonts in the Artix repos
			'gnu-free-fonts',
			# MorvaneOS: l3afpad isn't in the Artix repos
			'slock',
		]

	@property
	@override
	def default_greeter_type(self) -> GreeterType:
		return GreeterType.Sddm
