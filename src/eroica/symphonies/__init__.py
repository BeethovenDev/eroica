"""The movements of EROICA, in performance order.

Each module in this package contributes one :class:`~eroica.symphonies.base.Movement`.
Import the ``SYMPHONIES`` registry to enumerate them, or use the aggregation
helpers when building a hardening plan.
"""

from __future__ import annotations

from eroica.config import Tier
from eroica.symphonies.base import ChromiumFlag, FirefoxPref, Movement
from eroica.symphonies.choral import CHORAL
from eroica.symphonies.eroica import EROICA
from eroica.symphonies.fate import FATE
from eroica.symphonies.first import FIRST
from eroica.symphonies.pastoral import PASTORAL

__all__ = [
    "CHORAL",
    "EROICA",
    "FATE",
    "FIRST",
    "PASTORAL",
    "SYMPHONIES",
    "collect_flags",
    "collect_prefs",
    "get_movement",
]

#: Performance order: I, III, V, VI, IX.
SYMPHONIES: tuple[Movement, ...] = (FIRST, EROICA, FATE, PASTORAL, CHORAL)


def get_movement(key: str) -> Movement:
    """Return the movement with ``key`` (case-insensitive)."""
    for movement in SYMPHONIES:
        if movement.key == key.strip().lower():
            return movement
    known = ", ".join(m.key for m in SYMPHONIES)
    raise KeyError(f"unknown movement {key!r}; known movements: {known}")


def collect_prefs(tier: Tier) -> list[FirefoxPref]:
    """Gather all Firefox prefs that apply at ``tier``.

    Later movements win on duplicate keys, matching how ``user.js`` is applied.
    """
    merged: dict[str, FirefoxPref] = {}
    for movement in SYMPHONIES:
        for pref in movement.prefs_at(tier):
            merged[pref.key] = pref
    return list(merged.values())


def collect_flags(tier: Tier) -> list[ChromiumFlag]:
    """Gather all Chromium flags that apply at ``tier``, de-duplicated and ordered."""
    seen: set[str] = set()
    ordered: list[ChromiumFlag] = []
    for movement in SYMPHONIES:
        for flag in movement.flags_at(tier):
            if flag.flag in seen:
                continue
            seen.add(flag.flag)
            ordered.append(flag)
    return ordered
