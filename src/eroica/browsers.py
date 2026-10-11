"""Browser catalogue and detection.

EROICA understands two hardening strategies:

* **Mozilla family** — prefs are written to a ``user.js`` inside the profile.
* **Chromium family** — prefs are mostly compile-time, so EROICA curates
  command-line flags and launches the browser with an isolated user-data dir.

Detection is deliberately conservative: a browser counts as "installed" only
when an executable can be located via ``PATH`` or a known install location.
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from eroica.errors import BrowserNotFound, UnsupportedBrowser
from eroica.paths import (
    chromium_user_data_dirs,
    mozilla_profile_root,
    os_name,
)

__all__ = [
    "Browser",
    "BrowserFamily",
    "CATALOG",
    "DetectedBrowser",
    "detect_browsers",
    "find_binary",
    "get_browser",
]


class BrowserFamily(str, Enum):
    """The two hardening strategies EROICA implements."""

    MOZILLA = "mozilla"
    CHROMIUM = "chromium"


@dataclass(frozen=True)
class Browser:
    """Static description of a supported browser."""

    key: str
    name: str
    family: BrowserFamily
    binaries: tuple[str, ...]
    extra_paths: dict[str, tuple[str, ...]] = field(default_factory=dict)
    notes: str = ""

    def candidate_paths(self, osname: str | None = None) -> list[Path]:
        """Return expanded absolute install paths for the current OS."""
        current = osname or os_name()
        raw = self.extra_paths.get(current, ())
        return [Path(os.path.expandvars(p)).expanduser() for p in raw]


def _p(*parts: str) -> tuple[str, ...]:
    return tuple(parts)


#: The full catalogue of browsers EROICA knows about.
CATALOG: dict[str, Browser] = {
    "firefox": Browser(
        key="firefox",
        name="Mozilla Firefox",
        family=BrowserFamily.MOZILLA,
        binaries=("firefox", "firefox.exe", "firefox-bin"),
        extra_paths={
            "windows": (
                r"%ProgramFiles%\Mozilla Firefox\firefox.exe",
                r"%ProgramFiles(x86)%\Mozilla Firefox\firefox.exe",
            ),
            "macos": ("/Applications/Firefox.app/Contents/MacOS/firefox",),
            "linux": ("/usr/bin/firefox", "/usr/lib/firefox/firefox", "/snap/bin/firefox"),
        },
    ),
    "librewolf": Browser(
        key="librewolf",
        name="LibreWolf",
        family=BrowserFamily.MOZILLA,
        binaries=("librewolf", "librewolf.exe"),
        extra_paths={
            "windows": (r"%ProgramFiles%\LibreWolf\librewolf.exe",),
            "macos": ("/Applications/LibreWolf.app/Contents/MacOS/librewolf",),
            "linux": ("/usr/bin/librewolf", "/usr/lib/librewolf/librewolf"),
        },
        notes="Already hardened upstream; EROICA adds isolation and your DoH choice.",
    ),
    "waterfox": Browser(
        key="waterfox",
        name="Waterfox",
        family=BrowserFamily.MOZILLA,
        binaries=("waterfox", "waterfox.exe"),
        extra_paths={
            "windows": (r"%ProgramFiles%\Waterfox\waterfox.exe",),
            "macos": ("/Applications/Waterfox.app/Contents/MacOS/waterfox",),
            "linux": ("/usr/bin/waterfox",),
        },
    ),
    "zen": Browser(
        key="zen",
        name="Zen Browser",
        family=BrowserFamily.MOZILLA,
        binaries=("zen", "zen.exe", "zen-browser"),
        extra_paths={
            "windows": (
                r"%ProgramFiles%\Zen Browser\zen.exe",
                r"%LOCALAPPDATA%\zen\zen.exe",
            ),
            "macos": ("/Applications/Zen.app/Contents/MacOS/zen",),
            "linux": ("/usr/bin/zen-browser", "/opt/zen-browser/zen", "/opt/zen/zen"),
        },
        notes=(
            "Firefox-based and privacy-minded; EROICA still adds isolated "
            "profiles, strict DoH and its own anti-fingerprinting."
        ),
    ),
    "chrome": Browser(
        key="chrome",
        name="Google Chrome",
        family=BrowserFamily.CHROMIUM,
        binaries=("chrome", "chrome.exe", "google-chrome", "google-chrome-stable"),
        extra_paths={
            "windows": (
                r"%ProgramFiles%\Google\Chrome\Application\chrome.exe",
                r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe",
                r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe",
            ),
            "macos": ("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",),
            "linux": (
                "/usr/bin/google-chrome",
                "/usr/bin/google-chrome-stable",
                "/opt/google/chrome/chrome",
            ),
        },
    ),
    "chromium": Browser(
        key="chromium",
        name="Chromium",
        family=BrowserFamily.CHROMIUM,
        binaries=("chromium", "chromium.exe", "chromium-browser"),
        extra_paths={
            "windows": (r"%ProgramFiles%\Chromium\Application\chrome.exe",),
            "macos": ("/Applications/Chromium.app/Contents/MacOS/Chromium",),
            "linux": ("/usr/bin/chromium", "/usr/bin/chromium-browser", "/snap/bin/chromium"),
        },
    ),
    "brave": Browser(
        key="brave",
        name="Brave",
        family=BrowserFamily.CHROMIUM,
        binaries=("brave", "brave.exe", "brave-browser"),
        extra_paths={
            "windows": (
                r"%ProgramFiles%\BraveSoftware\Brave-Browser\Application\brave.exe",
                r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe",
            ),
            "macos": ("/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",),
            "linux": ("/usr/bin/brave-browser", "/opt/brave.com/brave/brave"),
        },
        notes="Brave ships strong defaults; EROICA still adds isolation + DoH + flags.",
    ),
    "edge": Browser(
        key="edge",
        name="Microsoft Edge",
        family=BrowserFamily.CHROMIUM,
        binaries=("msedge", "msedge.exe", "microsoft-edge"),
        extra_paths={
            "windows": (
                r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe",
                r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe",
            ),
            "macos": ("/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",),
            "linux": ("/usr/bin/microsoft-edge", "/usr/bin/microsoft-edge-stable"),
        },
    ),
    "vivaldi": Browser(
        key="vivaldi",
        name="Vivaldi",
        family=BrowserFamily.CHROMIUM,
        binaries=("vivaldi", "vivaldi.exe", "vivaldi-stable"),
        extra_paths={
            "windows": (
                r"%LOCALAPPDATA%\Vivaldi\Application\vivaldi.exe",
                r"%ProgramFiles%\Vivaldi\Application\vivaldi.exe",
            ),
            "macos": ("/Applications/Vivaldi.app/Contents/MacOS/Vivaldi",),
            "linux": ("/usr/bin/vivaldi", "/usr/bin/vivaldi-stable"),
        },
    ),
}

#: Aliases so users can type the name they know.
_ALIASES: dict[str, str] = {
    "mozilla": "firefox",
    "google-chrome": "chrome",
    "msedge": "edge",
    "brave-browser": "brave",
}


def get_browser(key: str) -> Browser:
    """Look up a browser by key or alias.

    Raises:
        UnsupportedBrowser: if the key is not in the catalogue.
    """
    normalised = _ALIASES.get(key.strip().lower(), key.strip().lower())
    try:
        return CATALOG[normalised]
    except KeyError as exc:
        known = ", ".join(sorted(CATALOG))
        raise UnsupportedBrowser(f"unsupported browser {key!r}; known browsers: {known}") from exc


def find_binary(browser: Browser) -> Path | None:
    """Locate the browser executable, or return ``None`` if not installed."""
    for name in browser.binaries:
        found = shutil.which(name)
        if found:
            return Path(found)
    for candidate in browser.candidate_paths():
        if candidate.is_file():
            return candidate
    return None


@dataclass(frozen=True)
class DetectedBrowser:
    """A catalogue entry paired with what was actually found on this machine."""

    browser: Browser
    binary: Path | None
    profile_roots: tuple[Path, ...]

    @property
    def installed(self) -> bool:
        return self.binary is not None

    def require_installed(self) -> Path:
        if self.binary is None:
            raise BrowserNotFound(
                f"{self.browser.name} is not installed or could not be found on this system"
            )
        return self.binary


def _profile_roots(browser: Browser) -> tuple[Path, ...]:
    if browser.family is BrowserFamily.MOZILLA:
        return (mozilla_profile_root(browser.key),)
    return tuple(chromium_user_data_dirs(browser.key))


def detect_browsers(*, only: str | None = None) -> list[DetectedBrowser]:
    """Detect installed browsers.

    Args:
        only: If given, restrict detection to a single browser key/alias.
    """
    candidates = [get_browser(only)] if only is not None else list(CATALOG.values())

    detected: list[DetectedBrowser] = []
    for browser in candidates:
        detected.append(
            DetectedBrowser(
                browser=browser,
                binary=find_binary(browser),
                profile_roots=_profile_roots(browser),
            )
        )
    return detected
