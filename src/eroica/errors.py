"""Exception hierarchy for EROICA.

Every error raised deliberately by the package derives from
:class:`EroicaError`, so callers (and the CLI) can distinguish expected,
user-actionable failures from genuine bugs.
"""

from __future__ import annotations


class EroicaError(Exception):
    """Base class for all EROICA errors."""


class BrowserError(EroicaError):
    """Raised for browser-related problems (unknown, missing or unusable)."""


class BrowserNotFound(BrowserError):
    """The requested browser is not installed or could not be located."""


class UnsupportedBrowser(BrowserError):
    """A browser was found but EROICA has no hardening strategy for it."""


class ProfileError(EroicaError):
    """Raised when a profile cannot be created, read or removed."""


class ProfileNotFound(ProfileError):
    """The requested EROICA profile does not exist."""


class ConfigError(EroicaError):
    """Raised when configuration is malformed or cannot be persisted."""


__all__ = [
    "BrowserError",
    "BrowserNotFound",
    "ConfigError",
    "EroicaError",
    "ProfileError",
    "ProfileNotFound",
    "UnsupportedBrowser",
]
