"""MorvaneOS: optional Secure Boot with machine-owned keys, for UKIs on Efistub and Limine."""

from pathlib import Path

import pytest

from morvane_installer.lib.hardware import SysInfo
from morvane_installer.lib.models.bootloader import Bootloader, BootloaderConfiguration

SETUP_MODE = 'SetupMode-8be4df61-93ca-11d2-aa0d-00e098032b8c'
# efivarfs: 4 bytes of attributes (NV+BS+RT), then the variable's value
ATTRS = b'\x06\x00\x00\x00'


def _efivars(tmp_path: Path, value: bytes) -> Path:
	(tmp_path / SETUP_MODE).write_bytes(ATTRS + value)
	return tmp_path


def test_setup_mode_detected(tmp_path: Path) -> None:
	assert SysInfo.secure_boot_setup_mode(_efivars(tmp_path, b'\x01'))


def test_user_mode_is_not_setup_mode(tmp_path: Path) -> None:
	assert not SysInfo.secure_boot_setup_mode(_efivars(tmp_path, b'\x00'))


def test_missing_variable_is_not_setup_mode(tmp_path: Path) -> None:
	# BIOS systems and firmware without Secure Boot have no SetupMode variable
	assert not SysInfo.secure_boot_setup_mode(tmp_path)


@pytest.mark.parametrize('bootloader', [Bootloader.Efistub, Bootloader.Limine])
def test_uki_bootloaders_support_secure_boot(bootloader: Bootloader) -> None:
	assert bootloader.has_uki_support()
	assert bootloader.has_secure_boot_support()


@pytest.mark.parametrize('bootloader', [Bootloader.Grub, Bootloader.Refind, Bootloader.Systemd, Bootloader.NO_BOOTLOADER])
def test_other_bootloaders_do_not(bootloader: Bootloader) -> None:
	assert not bootloader.has_uki_support()
	assert not bootloader.has_secure_boot_support()


def test_secure_boot_kept_with_uki_on_limine() -> None:
	config = BootloaderConfiguration.parse_arg({'bootloader': 'Limine', 'uki': True, 'secure_boot': True}, skip_boot=False)
	assert config.secure_boot


@pytest.mark.parametrize(
	'arg',
	[
		{'bootloader': 'Grub', 'uki': True, 'secure_boot': True},
		{'bootloader': 'Limine', 'uki': False, 'secure_boot': True},
	],
)
def test_secure_boot_dropped_when_unsupported(arg: dict[str, object]) -> None:
	assert not BootloaderConfiguration.parse_arg(arg, skip_boot=False).secure_boot


def test_secure_boot_defaults_off_for_old_configs() -> None:
	config = BootloaderConfiguration.parse_arg({'bootloader': 'Limine', 'uki': True}, skip_boot=False)
	assert not config.secure_boot


def test_secure_boot_round_trips_through_json() -> None:
	config = BootloaderConfiguration(bootloader=Bootloader.Efistub, uki=True, removable=False, secure_boot=True)
	assert config.json()['secure_boot'] is True
	assert BootloaderConfiguration.parse_arg(config.json(), skip_boot=False) == config
