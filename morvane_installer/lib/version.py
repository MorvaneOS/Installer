from importlib.metadata import version


def get_version() -> str:
	try:
		return version('morvane-installer')
	except Exception:
		return 'MorvaneOS installer version not found'
