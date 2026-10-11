"""Tests for isolated profile management."""

from __future__ import annotations

import pytest

from eroica.config import Tier
from eroica.errors import ProfileError, ProfileNotFound
from eroica.profiles import (
    META_FILENAME,
    create_profile,
    list_profiles,
    load_profile,
    remove_profile,
    validate_name,
)


def test_create_and_load_roundtrip() -> None:
    profile = create_profile("firefox", "osint-1", tier=Tier.STRICT, user_agent="Mozilla/5.0 x")
    assert profile.path.is_dir()
    assert (profile.path / META_FILENAME).is_file()

    loaded = load_profile("firefox", "osint-1")
    assert loaded.tier is Tier.STRICT
    assert loaded.user_agent == "Mozilla/5.0 x"


def test_duplicate_create_raises() -> None:
    create_profile("firefox", "dup", tier=Tier.STANDARD)
    with pytest.raises(ProfileError):
        create_profile("firefox", "dup", tier=Tier.STANDARD)


def test_duplicate_create_exist_ok_returns_existing() -> None:
    first = create_profile("firefox", "dup", tier=Tier.STANDARD)
    second = create_profile("firefox", "dup", tier=Tier.PARANOID, exist_ok=True)
    assert first.path == second.path


def test_list_and_filter_profiles() -> None:
    create_profile("firefox", "a", tier=Tier.STANDARD)
    create_profile("chrome", "b", tier=Tier.STRICT)
    assert {p.name for p in list_profiles()} == {"a", "b"}
    assert [p.name for p in list_profiles("firefox")] == ["a"]


def test_load_missing_raises() -> None:
    with pytest.raises(ProfileNotFound):
        load_profile("firefox", "ghost")


def test_remove_profile() -> None:
    profile = create_profile("firefox", "temp", tier=Tier.STANDARD)
    remove_profile(profile)
    assert not profile.path.exists()
    with pytest.raises(ProfileNotFound):
        remove_profile(profile)


@pytest.mark.parametrize("bad", ["", "..", "a/b", "a\\b", "a b", "-leading", "x" * 65])
def test_validate_name_rejects_unsafe(bad: str) -> None:
    with pytest.raises(ProfileError):
        validate_name(bad)


@pytest.mark.parametrize("good", ["osint", "osint-1", "research.v2", "a_b", "A1"])
def test_validate_name_accepts_safe(good: str) -> None:
    assert validate_name(good) == good
