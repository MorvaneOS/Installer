from functools import lru_cache

from archinstall.lib.log import debug
from archinstall.lib.packages.packages import check_package_upgrade


@lru_cache(maxsize=128)
def check_version_upgrade() -> str | None:
	debug('Checking version')
	upgrade = None

	upgrade = check_package_upgrade('morvane-installer')

	if upgrade is None:
		debug('No morvane-installer upgrades found')
		return None

	debug(f'morvane-installer latest: {upgrade}')

	return upgrade
