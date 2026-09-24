from pathlib import Path

from morvane_installer.lib.disk.device_handler import device_handler
from morvane_installer.lib.models.device import DiskLayoutConfiguration, DiskLayoutType

root_mount_dir = Path('/mnt/archinstall')

mods = device_handler.detect_pre_mounted_mods(root_mount_dir)

disk_config = DiskLayoutConfiguration(
	DiskLayoutType.Pre_mount,
	device_modifications=mods,
)
