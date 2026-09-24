"""MorvaneOS: /etc/default/grub gets the MorvaneOS name and theme."""

from pathlib import Path

from morvane_installer.lib.installer import morvane_grub_defaults

THEME = Path('/boot/grub/themes/morvane/theme.txt')

ARTIX_STYLE = """GRUB_DEFAULT=0
GRUB_TIMEOUT=5
GRUB_DISTRIBUTOR="Artix"
GRUB_CMDLINE_LINUX_DEFAULT="loglevel=3 quiet"
#GRUB_TERMINAL_OUTPUT=console
GRUB_GFXMODE=auto
#GRUB_THEME="/path/to/gfxtheme"
"""


def test_sets_name_and_theme() -> None:
	out = morvane_grub_defaults(ARTIX_STYLE, THEME)
	assert 'GRUB_DISTRIBUTOR="MorvaneOS"' in out
	assert 'GRUB_THEME="/boot/grub/themes/morvane/theme.txt"' in out
	assert '#GRUB_THEME' not in out
	assert out.count('GRUB_THEME=') == 1


def test_adds_theme_when_missing() -> None:
	out = morvane_grub_defaults('GRUB_DEFAULT=0\n', THEME)
	assert out.endswith('GRUB_THEME="/boot/grub/themes/morvane/theme.txt"\n')


def test_disables_console_only_output() -> None:
	out = morvane_grub_defaults('GRUB_TERMINAL_OUTPUT="console"\n', THEME)
	assert '#GRUB_TERMINAL_OUTPUT="console"' in out.splitlines()


def test_leaves_other_settings_alone() -> None:
	out = morvane_grub_defaults(ARTIX_STYLE, THEME)
	for line in ('GRUB_TIMEOUT=5', 'GRUB_CMDLINE_LINUX_DEFAULT="loglevel=3 quiet"', '#GRUB_TERMINAL_OUTPUT=console', 'GRUB_GFXMODE=auto'):
		assert line in out.splitlines()
