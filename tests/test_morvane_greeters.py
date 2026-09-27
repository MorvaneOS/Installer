"""MorvaneOS: display managers give sessions a D-Bus session bus, and elogind's runit check works."""

import subprocess
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from morvane_installer.default_profiles.profile import GreeterType
from morvane_installer.lib.installer import ELOGIND_CHECK, Installer
from morvane_installer.lib.profile import profiles_handler
from morvane_installer.lib.profile.profiles_handler import ProfileHandler

# As shipped in Artix's lightdm package
LIGHTDM_CONF = '[Seat:*]\n#greeter-session=example-gtk-gnome\nsession-wrapper=/etc/lightdm/Xsession\n#greeter-wrapper=\n'

# As shipped in elogind-runit 20231119
ARTIX_ELOGIND_CHECK = '#!/bin/sh -e\n\ntest -f /run/elogind.pid\n\nreadonly PID="$(cat /run/elogind.pid)"\ntest -n "$PID"\n'


def _session(target: Path) -> tuple[Any, dict[str, Any]]:
	calls: dict[str, Any] = {}
	session = SimpleNamespace(
		target=target,
		add_additional_packages=lambda p: calls.setdefault('packages', p),
		enable_service=lambda s: calls.setdefault('services', s),
	)
	return session, calls


def _check_wrapper(wrapper: Path, wrapped: str) -> None:
	assert wrapper.stat().st_mode & 0o111
	text = wrapper.read_text()
	assert 'exec dbus-run-session "$0" "$@"' in text
	assert text.rstrip().endswith(f'exec {wrapped} "$@"')
	subprocess.run(['sh', '-n', str(wrapper)], check=True)


def _script(path: Path, body: str) -> None:
	path.write_text(f'#!/bin/sh\n{body}\n')
	path.chmod(0o755)


def _wrapper_with_fakes(tmp_path: Path) -> tuple[Path, Path]:
	"""The wrapper around a script that prints its arguments, and a bin dir for fake commands."""
	show = tmp_path / 'show'
	_script(show, 'for a in "$@"; do echo "$a"; done')
	session, _ = _session(tmp_path)
	profiles_handler._write_session_bus_wrapper(session, 'wrapper', str(show))

	bin_dir = tmp_path / 'bin'
	bin_dir.mkdir()
	return tmp_path / 'usr/local/bin/wrapper', bin_dir


def _run(wrapper: Path, bin_dir: Path, args: list[str], bus: str | None) -> list[str]:
	env = {'PATH': f'{bin_dir}:/usr/bin:/bin', 'XDG_RUNTIME_DIR': str(bin_dir)}
	if bus:
		env['DBUS_SESSION_BUS_ADDRESS'] = bus
	out = subprocess.run([str(wrapper), *args], env=env, capture_output=True, text=True, check=True)
	return out.stdout.splitlines()


def test_sddm_runs_sessions_with_a_session_bus(tmp_path: Path) -> None:
	session, _ = _session(tmp_path)
	ProfileHandler().install_greeter(session, GreeterType.Sddm)

	_check_wrapper(tmp_path / 'usr/local/bin/morvane-wayland-session', '/usr/share/sddm/scripts/wayland-session')
	conf = (tmp_path / 'etc/sddm.conf.d/10-morvane-session-bus.conf').read_text()
	assert conf == '[Wayland]\nSessionCommand=/usr/local/bin/morvane-wayland-session\n'


@pytest.mark.parametrize('greeter', [GreeterType.Lightdm, GreeterType.LightdmSlick])
def test_lightdm_runs_sessions_with_a_session_bus(tmp_path: Path, greeter: GreeterType) -> None:
	conf = tmp_path / 'etc/lightdm/lightdm.conf'
	conf.parent.mkdir(parents=True)
	conf.write_text(LIGHTDM_CONF)

	session, _ = _session(tmp_path)
	ProfileHandler().install_greeter(session, greeter)

	_check_wrapper(tmp_path / 'usr/local/bin/morvane-lightdm-session', '/etc/lightdm/Xsession')
	lines = conf.read_text().splitlines()
	assert 'session-wrapper=/usr/local/bin/morvane-lightdm-session' in lines
	assert 'session-wrapper=/etc/lightdm/Xsession' not in lines


@pytest.mark.parametrize(
	('args', 'expected'),
	[
		# LightDM passes the session's Exec split into words
		(['dbus-launch', '--exit-with-session', 'niri', '--session'], ['niri', '--session']),
		# SDDM passes it as one string, which its wayland-session script splits later
		(['dbus-launch --exit-with-session niri --session'], ['niri --session']),
		(['sway'], ['sway']),
		(['dbus-launch', 'something'], ['dbus-launch', 'something']),
	],
)
def test_session_bus_wrapper_drops_dbus_launch(tmp_path: Path, args: list[str], expected: list[str]) -> None:
	wrapper, bin_dir = _wrapper_with_fakes(tmp_path)
	# With a bus already there, the wrapper runs the script directly
	assert _run(wrapper, bin_dir, args, bus='unix:path=/existing') == expected


def test_session_bus_wrapper_starts_a_bus_when_there_is_none(tmp_path: Path) -> None:
	wrapper, bin_dir = _wrapper_with_fakes(tmp_path)
	# Stands in for dbus-run-session: runs the command with a bus address set
	_script(bin_dir / 'dbus-run-session', 'echo started-bus; DBUS_SESSION_BUS_ADDRESS=unix:path=/new exec "$@"')

	out = _run(wrapper, bin_dir, ['dbus-launch', '--exit-with-session', 'niri', '--session'], bus=None)
	# The wrapper re-ran itself under the bus exactly once, then the session
	assert out == ['started-bus', 'niri', '--session']


def test_session_bus_wrapper_starts_pipewire(tmp_path: Path) -> None:
	wrapper, bin_dir = _wrapper_with_fakes(tmp_path)
	marker = tmp_path / 'pipewire-started'
	_script(bin_dir / 'artix-pipewire-launcher', f'echo "$DBUS_SESSION_BUS_ADDRESS" > {marker}')

	assert _run(wrapper, bin_dir, ['sway'], bus='unix:path=/existing') == ['sway']
	# Started in the background, inside the session's bus
	for _ in range(50):
		if marker.exists() and marker.read_text():
			break
		time.sleep(0.05)
	assert marker.read_text().strip() == 'unix:path=/existing'


def test_session_bus_wrapper_without_pipewire_installed(tmp_path: Path) -> None:
	wrapper, bin_dir = _wrapper_with_fakes(tmp_path)
	assert _run(wrapper, bin_dir, ['sway'], bus='unix:path=/existing') == ['sway']


def test_gdm_greeter_from_old_configs_becomes_sddm(tmp_path: Path) -> None:
	session, calls = _session(tmp_path)
	ProfileHandler().install_greeter(session, GreeterType.Gdm)
	assert calls == {'packages': ['sddm'], 'services': ['sddm']}


def _installer_for(target: Path) -> Installer:
	installer = Installer.__new__(Installer)
	installer.target = target
	return installer


def test_elogind_check_replaced_when_it_waits_for_the_pid_file(tmp_path: Path) -> None:
	check = tmp_path / 'etc/runit/sv/elogind/check'
	check.parent.mkdir(parents=True)
	check.write_text(ARTIX_ELOGIND_CHECK)
	check.chmod(0o755)

	_installer_for(tmp_path)._fix_elogind_check()

	assert check.read_text() == ELOGIND_CHECK
	assert '/run/elogind.pid' not in check.read_text()
	assert check.stat().st_mode & 0o111
	subprocess.run(['sh', '-n', str(check)], check=True)


def test_elogind_check_left_alone_once_fixed_upstream(tmp_path: Path) -> None:
	check = tmp_path / 'etc/runit/sv/elogind/check'
	check.parent.mkdir(parents=True)
	check.write_text('#!/bin/sh\nexec pgrep -x elogind\n')

	_installer_for(tmp_path)._fix_elogind_check()

	assert check.read_text() == '#!/bin/sh\nexec pgrep -x elogind\n'


def test_elogind_check_missing_is_fine(tmp_path: Path) -> None:
	_installer_for(tmp_path)._fix_elogind_check()
	assert not (tmp_path / 'etc/runit/sv/elogind/check').exists()
