"""Tests for cross-platform path resolution."""

from __future__ import annotations

from pathlib import Path

from eroica.paths import (
    config_home,
    data_home,
    mozilla_profile_root,
    zen_profile_root,
)


def test_config_and_data_home_respect_env(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("EROICA_CONFIG_HOME", str(tmp_path / "cfg"))
    monkeypatch.setenv("EROICA_DATA_HOME", str(tmp_path / "data"))
    assert config_home() == tmp_path / "cfg"
    assert data_home() == tmp_path / "data"


def test_windows_zen_profile_root_under_appdata(monkeypatch, tmp_path) -> None:
    import eroica.paths as paths

    monkeypatch.setattr(paths, "os_name", lambda: "windows")
    monkeypatch.setenv("APPDATA", str(tmp_path / "roaming"))
    assert zen_profile_root() == tmp_path / "roaming" / "zen" / "Profiles"


def test_linux_zen_profile_root_hidden_dir(monkeypatch) -> None:
    import eroica.paths as paths

    monkeypatch.setattr(paths, "os_name", lambda: "linux")
    assert zen_profile_root() == Path.home() / ".zen"


def test_mozilla_profile_root_override_and_fallback(monkeypatch) -> None:
    import eroica.paths as paths

    monkeypatch.setattr(paths, "os_name", lambda: "linux")
    assert mozilla_profile_root("zen") == Path.home() / ".zen"
    assert mozilla_profile_root("unknown") == Path.home() / ".mozilla" / "firefox"