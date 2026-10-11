"""Tests for the browser catalogue and detection."""

from __future__ import annotations

import pytest

from eroica.browsers import (
    CATALOG,
    BrowserFamily,
    detect_browsers,
    get_browser,
)
from eroica.errors import UnsupportedBrowser


def test_catalogue_families_are_known() -> None:
    for browser in CATALOG.values():
        assert browser.family in {BrowserFamily.MOZILLA, BrowserFamily.CHROMIUM}
        assert browser.key == browser.key.lower()


def test_get_browser_by_key() -> None:
    assert get_browser("firefox").family is BrowserFamily.MOZILLA
    assert get_browser("zen").family is BrowserFamily.MOZILLA
    assert get_browser("brave").family is BrowserFamily.CHROMIUM


def test_get_browser_by_alias() -> None:
    assert get_browser("google-chrome").key == "chrome"
    assert get_browser("mozilla").key == "firefox"
    assert get_browser("BRAVE").key == "brave"


def test_get_browser_unknown_raises() -> None:
    with pytest.raises(UnsupportedBrowser):
        get_browser("netscape")


def test_candidate_paths_expand_per_os() -> None:
    firefox = get_browser("firefox")
    assert firefox.candidate_paths("linux")
    assert firefox.candidate_paths("windows")
    assert firefox.candidate_paths("macos")
    assert firefox.candidate_paths("plan9") == []


def test_zen_known_paths() -> None:
    zen = get_browser("zen")
    assert "zen.exe" in zen.binaries
    assert any("Zen Browser" in str(p) for p in zen.candidate_paths("windows"))


def test_detect_all_returns_every_browser() -> None:
    detected = detect_browsers()
    assert len(detected) == len(CATALOG)


def test_detect_only_filters() -> None:
    detected = detect_browsers(only="firefox")
    assert len(detected) == 1
    assert detected[0].browser.key == "firefox"


def test_require_installed_raises_when_absent() -> None:
    from eroica.errors import BrowserNotFound

    detected = detect_browsers(only="vivaldi")[0]
    if detected.binary is None:
        with pytest.raises(BrowserNotFound):
            detected.require_installed()
    else:  # pragma: no cover - only when Vivaldi happens to be installed
        assert detected.installed
