"""Tests for configuration loading, saving and validation."""

from __future__ import annotations

import json

import pytest

from eroica.config import DOH_PROVIDERS, Config, Tier, config_path, load_config, save_config
from eroica.errors import ConfigError


def test_defaults_are_sane() -> None:
    config = load_config()
    assert config.default_tier is Tier.STRICT
    assert config.doh_provider == "mullvad"
    assert config.ua_mode == "consistent"
    assert config.backup_user_js is True


def test_save_load_roundtrip() -> None:
    config = Config(default_tier=Tier.PARANOID, doh_provider="quad9", ua_mode="off")
    save_config(config)
    assert config_path().is_file()

    reloaded = load_config()
    assert reloaded.default_tier is Tier.PARANOID
    assert reloaded.doh_provider == "quad9"
    assert reloaded.ua_mode == "off"


def test_tier_coerce_accepts_many_spellings() -> None:
    assert Tier.coerce("strict") is Tier.STRICT
    assert Tier.coerce("STRICT") is Tier.STRICT
    assert Tier.coerce(3) is Tier.PARANOID
    assert Tier.coerce(Tier.STANDARD) is Tier.STANDARD


def test_tier_coerce_rejects_garbage() -> None:
    with pytest.raises(ConfigError):
        Tier.coerce("nonsense")
    with pytest.raises(ConfigError):
        Tier.coerce(99)


def test_invalid_doh_provider_rejected() -> None:
    with pytest.raises(ConfigError):
        Config(doh_provider="notreal")


def test_invalid_ua_mode_rejected() -> None:
    with pytest.raises(ConfigError):
        Config(ua_mode="chaos")


def test_doh_uri_maps_and_system_is_none() -> None:
    assert Config(doh_provider="mullvad").doh_uri == DOH_PROVIDERS["mullvad"]
    assert Config(doh_provider="system").doh_uri is None


def test_corrupt_config_raises() -> None:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{ this is not json", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config()


def test_non_object_config_raises() -> None:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config()
