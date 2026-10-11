"""Tests for the User-Agent pool and validation."""

from __future__ import annotations

import pytest

from eroica.errors import ConfigError
from eroica.ua import UA_POOL, describe_pool, pick, validate


def test_pick_is_deterministic() -> None:
    assert pick("profile-a") == pick("profile-a")


def test_pick_varies_with_seed() -> None:
    picks = {pick(f"seed-{i}") for i in range(32)}
    assert len(picks) > 1


def test_pick_returns_pool_member() -> None:
    for platform, pool in UA_POOL.items():
        assert pick("x", platform) in pool


def test_unknown_platform_raises() -> None:
    with pytest.raises(ConfigError):
        pick("x", "amiga")


def test_validate_accepts_reasonable_ua() -> None:
    ua = "Mozilla/5.0 (X11; Linux x86_64) Gecko/20100101 Firefox/128.0"
    assert validate(ua) == ua


@pytest.mark.parametrize(
    "bad",
    ["", "curl/8.0", "Mozilla/5.0\nInjected: yes", "Mozilla/" + "x" * 600],
)
def test_validate_rejects_bad(bad: str) -> None:
    with pytest.raises(ConfigError):
        validate(bad)


def test_describe_pool_is_flat() -> None:
    assert len(describe_pool()) == sum(len(p) for p in UA_POOL.values())
