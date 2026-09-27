"""MorvaneOS colours for the installer.

The TUI draws with the terminal's 16 ANSI colours (the Linux console can't do
more), so the theme below only names ANSI slots. On the Linux console the
installer sets those slots to the MorvaneOS terminal palette (the one
morvane-wm-theme gives terminals) while it runs; anywhere else, such as over
SSH, the terminal's own palette is used.
"""

import os
import sys

from textual.theme import Theme

# ANSI slots 0-15. Slot 0 is also the console's background, so it's MorvaneOS
# night rather than the palette's usual #2A1C32 black.
CONSOLE_PALETTE = [
	'120C16',  # black: night
	'F0506E',  # red
	'3FB950',  # green
	'E8A23A',  # yellow
	'7AA2F7',  # blue
	'F4A6C6',  # magenta: MorvaneOS pastel pink
	'56C8C0',  # cyan
	'D8C8D4',  # white: default text
	'8F7F96',  # bright black
	'FF8AA0',  # bright red
	'6FD67D',  # bright green
	'F5C26B',  # bright yellow
	'A6C1FA',  # bright blue
	'F9CFE0',  # bright magenta
	'8FDDD6',  # bright cyan
	'F5EEF3',  # bright white: paper
]

MORVANE_THEME = Theme(
	name='morvane',
	ansi=True,
	dark=True,
	primary='ansi_magenta',
	secondary='ansi_blue',
	accent='ansi_bright_magenta',
	warning='ansi_yellow',
	error='ansi_red',
	success='ansi_green',
	foreground='ansi_default',
	background='ansi_default',
	surface='ansi_default',
	panel='ansi_default',
	boost='ansi_default',
	variables={
		'ansi-background': 'ansi_black',
		'ansi-foreground': 'ansi_white',
		'border': 'ansi_magenta',
		'border-blurred': 'ansi_bright_black',
		'block-cursor-foreground': 'ansi_black',
		'block-cursor-background': 'ansi_magenta',
		'block-cursor-text-style': 'none',
		'input-cursor-background': 'ansi_bright_white',
		'input-cursor-foreground': 'ansi_black',
		'input-cursor-text-style': 'none',
		'input-selection-background': 'ansi_bright_magenta',
		'input-selection-foreground': 'ansi_black',
		'screen-selection-background': 'ansi_bright_magenta',
		'screen-selection-foreground': 'ansi_black',
		'footer-key-foreground': 'ansi_magenta',
	},
)


def _on_linux_console() -> bool:
	return os.environ.get('TERM') == 'linux' and sys.stdout.isatty()


def apply_console_palette() -> None:
	"""Sets the Linux console's 16 colours to the MorvaneOS palette."""
	if _on_linux_console():
		sys.stdout.write(''.join(f'\033]P{i:X}{colour}' for i, colour in enumerate(CONSOLE_PALETTE)))
		sys.stdout.flush()


def restore_console_palette() -> None:
	"""Puts the Linux console's colours back to its defaults."""
	if _on_linux_console():
		# The framebuffer console doesn't repaint what's already drawn when the palette
		# changes, so clear the screen too or the night background stays behind
		sys.stdout.write('\033]R\033[2J\033[H')
		sys.stdout.flush()
