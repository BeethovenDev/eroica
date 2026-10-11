"""Cross-platform path resolution.

Chromium-family browsers keep profiles under a per-OS "user data" directory
that differs by vendor *and* platform, and Firefox has its own (older, less
consistent) layout. This module centralises all of that guesswork so the rest
of EROICA only ever deals with :class:`pathlib.Path` objects.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

__all__ = [
    "cache_home",
    "chromium_user_data_dirs",
    "config_home",
    "data_home",
    "firefox_profile_root",
    "home",
    "os_name",
]


def os_name() -> str:
    """Return one of ``"windows"``, ``"macos"`` or ``"linux"``."""
    if sys.platform.startswith("win"):
        return "windows"
    if sys.platform == "darwin":
        return "macos"
    return "linux"


def home() -> Path:
    """Return the current user's home directory."""
    return Path.home()


def _env_path(variable: str) -> Path | None:
    value = os.environ.get(variable)
    return Path(value) if value else None


def config_home() -> Path:
    """Return EROICA's per-user configuration directory (created on demand)."""
    override = _env_path("EROICA_CONFIG_HOME")
    if override is not None:
        return override

    osname = os_name()
    if osname == "windows":
        base = _env_path("APPDATA") or home() / "AppData" / "Roaming"
        return base / "eroica"
    if osname == "macos":
        return home() / "Library" / "Application Support" / "eroica"
    base = _env_path("XDG_CONFIG_HOME") or home() / ".config"
    return base / "eroica"


def data_home() -> Path:
    """Return EROICA's per-user data directory (isolated browser profiles)."""
    override = _env_path("EROICA_DATA_HOME")
    if override is not None:
        return override

    osname = os_name()
    if osname == "windows":
        base = _env_path("LOCALAPPDATA") or home() / "AppData" / "Local"
        return base / "eroica"
    if osname == "macos":
        return home() / "Library" / "Application Support" / "eroica" / "data"
    base = _env_path("XDG_DATA_HOME") or home() / ".local" / "share"
    return base / "eroica"


def cache_home() -> Path:
    """Return EROICA's per-user cache directory."""
    override = _env_path("EROICA_CACHE_HOME")
    if override is not None:
        return override

    osname = os_name()
    if osname == "windows":
        base = _env_path("LOCALAPPDATA") or home() / "AppData" / "Local"
        return base / "eroica" / "cache"
    if osname == "macos":
        return home() / "Library" / "Caches" / "eroica"
    base = _env_path("XDG_CACHE_HOME") or home() / ".cache"
    return base / "eroica"


def firefox_profile_root() -> Path:
    """Return the directory containing Mozilla Firefox profiles."""
    osname = os_name()
    if osname == "windows":
        base = _env_path("APPDATA") or home() / "AppData" / "Roaming"
        return base / "Mozilla" / "Firefox"
    if osname == "macos":
        return home() / "Library" / "Application Support" / "Firefox"
    return home() / ".mozilla" / "firefox"


#: Vendor-relative "User Data" directories, keyed by EROICA browser id.
_CHROMIUM_USER_DATA: dict[str, dict[str, tuple[str, ...]]] = {
    "chrome": {
        "windows": ("Google", "Chrome", "User Data"),
        "macos": ("Google", "Chrome"),
        "linux": (".config", "google-chrome"),
    },
    "chromium": {
        "windows": ("Chromium", "User Data"),
        "macos": ("Chromium",),
        "linux": (".config", "chromium"),
    },
    "brave": {
        "windows": ("BraveSoftware", "Brave-Browser", "User Data"),
        "macos": ("BraveSoftware", "Brave-Browser"),
        "linux": (".config", "BraveSoftware", "Brave-Browser"),
    },
    "edge": {
        "windows": ("Microsoft", "Edge", "User Data"),
        "macos": ("Microsoft Edge",),
        "linux": (".config", "microsoft-edge"),
    },
    "vivaldi": {
        "windows": ("Vivaldi", "User Data"),
        "macos": ("Vivaldi",),
        "linux": (".config", "vivaldi"),
    },
}


def _windows_base() -> Path:
    return _env_path("LOCALAPPDATA") or home() / "AppData" / "Local"


def chromium_user_data_dirs(browser_id: str) -> list[Path]:
    """Return candidate user-data directories for a Chromium-family browser.

    Returns an empty list for browsers EROICA does not know about. The list is
    ordered from most- to least-likely and callers should use the first entry
    that exists.
    """
    spec = _CHROMIUM_USER_DATA.get(browser_id)
    if spec is None:
        return []

    osname = os_name()
    parts = spec.get(osname)
    if parts is None:
        return []

    if osname == "windows":
        base = _windows_base()
        mac_base = None
        linux_base = None
    elif osname == "macos":
        base = home() / "Library" / "Application Support"
        mac_base = base
        linux_base = None
    else:
        base = home()
        mac_base = None
        linux_base = home()

    candidates: list[Path] = []
    if osname == "windows":
        candidates.append(_windows_base().joinpath(*parts))
        roaming = _env_path("APPDATA")
        if roaming is not None:
            candidates.append(roaming.joinpath(*parts))
    elif osname == "macos":
        candidates.append((mac_base or base).joinpath(*parts))
    else:
        candidates.append((linux_base or base).joinpath(*parts))

    # De-duplicate while preserving order.
    seen: set[Path] = set()
    unique: list[Path] = []
    for candidate in candidates:
        if candidate not in seen:
            seen.add(candidate)
            unique.append(candidate)
    return unique
