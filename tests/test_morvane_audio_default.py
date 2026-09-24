"""MorvaneOS: desktops get PipeWire unless the user made an audio choice."""

from types import SimpleNamespace

import pytest

from morvane_installer.lib.models.application import ApplicationConfiguration, Audio, AudioConfiguration
from morvane_installer.scripts.guided import needs_default_audio


def _config(app_config: object, desktop: bool | None) -> SimpleNamespace:
	if desktop is None:
		profile_config = None
	else:
		profile = SimpleNamespace(is_desktop_profile=lambda: desktop)
		profile_config = SimpleNamespace(profile=profile)
	return SimpleNamespace(app_config=app_config, profile_config=profile_config)


@pytest.mark.parametrize(
	('app_config', 'desktop', 'expected'),
	[
		([], True, True),  # Applications menu never opened: its default is []
		(None, True, True),
		(ApplicationConfiguration(), True, True),  # opened, but no audio choice
		(ApplicationConfiguration(audio_config=AudioConfiguration(Audio.PIPEWIRE)), True, False),
		(ApplicationConfiguration(audio_config=AudioConfiguration(Audio.NO_AUDIO)), True, False),
		([], False, False),  # server / minimal profile
		([], None, False),  # no profile at all
	],
)
def test_needs_default_audio(app_config: object, desktop: bool | None, expected: bool) -> None:
	assert needs_default_audio(_config(app_config, desktop)) is expected  # type: ignore[arg-type]
