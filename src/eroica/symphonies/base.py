"""Building blocks for EROICA's *movements*.

A movement is a single-theme bundle of hardening settings. Each setting
declares the **minimum** :class:`~eroica.config.Tier` at which it takes effect,
which is what makes tiers additive: ``PARANOID`` automatically includes
everything from ``STRICT`` and ``STANDARD``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from eroica.config import Tier

__all__ = ["ChromiumFlag", "FirefoxPref", "Movement"]


@dataclass(frozen=True)
class FirefoxPref:
    """A single Firefox preference for ``user.js``."""

    key: str
    value: Any
    tier: Tier = Tier.STANDARD
    note: str = ""


@dataclass(frozen=True)
class ChromiumFlag:
    """A single Chromium-family command-line flag.

    ``flag`` must be the complete token, e.g. ``"--no-pings"`` or
    ``"--disable-features=Translate"``.
    """

    flag: str
    tier: Tier = Tier.STANDARD
    note: str = ""


@dataclass(frozen=True)
class Movement:
    """One themed bundle of hardening settings."""

    key: str
    roman: str
    nickname: str
    title: str
    opus: str
    year: int
    signature: str
    summary: str
    prefs: tuple[FirefoxPref, ...] = field(default_factory=tuple)
    flags: tuple[ChromiumFlag, ...] = field(default_factory=tuple)

    @property
    def heading(self) -> str:
        """A human-readable one-line label, e.g. ``"III · Eroica — ..."``."""
        return f"{self.roman} · {self.nickname} — {self.title}"

    def prefs_at(self, tier: Tier) -> tuple[FirefoxPref, ...]:
        """Return the Firefox prefs that apply at or below ``tier``."""
        return tuple(p for p in self.prefs if p.tier <= tier)

    def flags_at(self, tier: Tier) -> tuple[ChromiumFlag, ...]:
        """Return the Chromium flags that apply at or below ``tier``."""
        return tuple(f for f in self.flags if f.tier <= tier)
