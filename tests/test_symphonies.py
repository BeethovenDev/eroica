"""Tests for the symphonies registry and tier additivity."""

from __future__ import annotations

import pytest

from eroica.config import Tier
from eroica.symphonies import (
    SYMPHONIES,
    collect_flags,
    collect_prefs,
    get_movement,
)


def test_five_movements_in_order() -> None:
    assert [m.key for m in SYMPHONIES] == ["first", "eroica", "fate", "pastoral", "choral"]
    assert [m.roman for m in SYMPHONIES] == ["I", "III", "V", "VI", "IX"]


def test_every_movement_is_beethoven_attributed() -> None:
    for movement in SYMPHONIES:
        assert movement.opus.startswith("Op. ")
        assert 1800 <= movement.year <= 1824
        assert movement.summary
        assert movement.title


def test_tiers_are_additive_for_prefs() -> None:
    standard = {p.key for p in collect_prefs(Tier.STANDARD)}
    strict = {p.key for p in collect_prefs(Tier.STRICT)}
    paranoid = {p.key for p in collect_prefs(Tier.PARANOID)}
    assert standard <= strict <= paranoid


def test_tiers_are_additive_for_flags() -> None:
    standard = set(collect_flags(Tier.STANDARD))
    strict = set(collect_flags(Tier.STRICT))
    paranoid = set(collect_flags(Tier.PARANOID))
    assert standard <= strict <= paranoid


def test_prefs_are_deduplicated() -> None:
    keys = [p.key for p in collect_prefs(Tier.PARANOID)]
    assert len(keys) == len(set(keys))


def test_flags_are_deduplicated() -> None:
    flags = [f.flag for f in collect_flags(Tier.PARANOID)]
    assert len(flags) == len(set(flags))


def test_paranoid_is_strictly_larger_than_standard() -> None:
    assert len(collect_prefs(Tier.PARANOID)) > len(collect_prefs(Tier.STANDARD))


def test_get_movement_is_case_insensitive() -> None:
    assert get_movement("EROICA").key == "eroica"


def test_get_movement_rejects_unknown() -> None:
    with pytest.raises(KeyError):
        get_movement("nope")
