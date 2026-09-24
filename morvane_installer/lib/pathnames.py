from pathlib import Path
from typing import Final

from morvane_installer.lib.linux_path import LPath

# MorvaneOS: where the Artix live system mounts its boot medium (Arch: /run/archiso/airootfs).
# Used to detect live mode and to keep the boot USB out of the installable disks.
ARCHISO_MOUNTPOINT: Final = Path('/run/artix/bootmnt')
MIRRORLIST: Final = LPath('/etc/pacman.d/mirrorlist')
PACMAN_CONF: Final = LPath('/etc/pacman.conf')
