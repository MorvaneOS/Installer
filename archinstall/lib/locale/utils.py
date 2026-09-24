import zoneinfo
from functools import lru_cache
from pathlib import Path

from archinstall.lib.command import SysCommand
from archinstall.lib.exceptions import ServiceException, SysCallError
from archinstall.lib.log import error
from archinstall.lib.utils.util import running_from_iso

# MorvaneOS: localectl and timedatectl are systemd tools, so the lists below are
# read straight from the files those tools use.


def list_keyboard_languages() -> list[str]:
	keymaps = Path('/usr/share/kbd/keymaps')
	return sorted({path.name.removesuffix('.gz').removesuffix('.map') for path in keymaps.rglob('*.map*')})


def list_locales() -> list[str]:
	locales = []

	with open('/usr/share/i18n/SUPPORTED') as file:
		for line in file:
			if line != 'C.UTF-8 UTF-8\n':
				locales.append(line.rstrip())

	return locales


@lru_cache
def list_console_fonts() -> list[str]:
	directory = Path('/usr/share/kbd/consolefonts')
	fonts = {path.name.split('.')[0] for path in directory.glob('*.gz')}
	return sorted(fonts)


def list_x11_keyboard_languages() -> list[str]:
	# The "! layout" section of xkeyboard-config's rules list; empty when X11 isn't installed
	layouts: list[str] = []
	try:
		lines = Path('/usr/share/X11/xkb/rules/base.lst').read_text().splitlines()
	except OSError:
		return layouts

	in_layouts = False
	for line in lines:
		if line.startswith('!'):
			in_layouts = line.strip() == '! layout'
		elif in_layouts and line.strip():
			layouts.append(line.split()[0])
	return sorted(layouts)


def verify_keyboard_layout(layout: str) -> bool:
	for language in list_keyboard_languages():
		if layout.lower() == language.lower():
			return True
	return False


def verify_x11_keyboard_layout(layout: str) -> bool:
	for language in list_x11_keyboard_languages():
		if layout.lower() == language.lower():
			return True
	return False


def get_kb_layout() -> str:
	try:
		lines = Path('/etc/vconsole.conf').read_text().splitlines()
	except OSError:
		return ''

	layout = ''
	for line in lines:
		if line.startswith('KEYMAP='):
			layout = line.removeprefix('KEYMAP=').strip().strip('"')

	if not layout or not verify_keyboard_layout(layout):
		return ''

	return layout


def set_kb_layout(locale: str) -> bool:
	if not running_from_iso():
		# Skip when running from host - no need to change host keymap
		# The target installation keymap is set via installer.set_keyboard_language()
		return True

	if len(locale.strip()):
		if not verify_keyboard_layout(locale):
			error(f'Invalid keyboard locale specified: {locale}')
			return False

		try:
			SysCommand(f'loadkeys {locale}')
		except SysCallError as err:
			raise ServiceException(f"Unable to set locale '{locale}' for console: {err}")

		return True

	return False


def list_timezones() -> list[str]:
	return sorted(zone for zone in zoneinfo.available_timezones() if not zone.startswith(('posix/', 'right/')))
