"""MorvaneOS: GNOME without systemd, so no GDM, Artix's gnome-session-sysvinit, and SDDM."""

import pytest

from morvane_installer.default_profiles.desktops import gnome
from morvane_installer.default_profiles.desktops.gnome import GnomeProfile
from morvane_installer.default_profiles.profile import GreeterType
from morvane_installer.lib.models.packages import PackageGroup
from morvane_installer.lib.profile import profile_menu


def _group(monkeypatch: pytest.MonkeyPatch, group: PackageGroup | None) -> None:
	monkeypatch.setattr(gnome, 'package_group_info', lambda name: group)


def test_installs_gnome_group_without_gdm(monkeypatch: pytest.MonkeyPatch) -> None:
	_group(monkeypatch, PackageGroup('gnome', ['gdm', 'gnome-session', 'gnome-shell', 'nautilus']))
	packages = GnomeProfile().packages
	assert 'gdm' not in packages
	assert {'gnome-session', 'gnome-shell', 'nautilus', 'gnome-session-sysvinit', 'gnome-tweaks'} <= set(packages)


def test_falls_back_to_a_minimal_gnome_without_the_group(monkeypatch: pytest.MonkeyPatch) -> None:
	_group(monkeypatch, None)
	packages = GnomeProfile().packages
	assert 'gdm' not in packages
	assert {'gnome-shell', 'gnome-session', 'gnome-session-sysvinit'} <= set(packages)


def test_defaults_to_sddm() -> None:
	assert GnomeProfile().default_greeter_type == GreeterType.Sddm


def test_gdm_is_not_offered() -> None:
	assert GreeterType.Gdm in profile_menu._UNAVAILABLE_GREETERS
