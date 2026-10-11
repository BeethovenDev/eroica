"""Shared pytest fixtures.

Every test runs against an isolated configuration/data/cache home so the suite
never touches the developer's real browser profiles.
"""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("EROICA_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("EROICA_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("EROICA_CACHE_HOME", str(tmp_path / "cache"))
    return tmp_path
