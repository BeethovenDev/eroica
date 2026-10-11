"""Tests for plan resolution and the two write strategies."""

from __future__ import annotations

import json

from eroica.browsers import get_browser
from eroica.config import Config, Tier
from eroica.hardening import build_plan, harden, preview_firefox
from eroica.profiles import create_profile


def _profile(browser_key: str = "firefox", name: str = "p"):
    return create_profile(browser_key, name, tier=Tier.STRICT, exist_ok=True)


def test_plan_injects_doh_endpoint() -> None:
    config = Config(doh_provider="quad9")
    plan = build_plan(get_browser("firefox"), _profile(), Tier.STRICT, config)
    uris = {p.key: p.value for p in plan.prefs}
    assert uris["network.trr.uri"] == config.doh_uri
    assert uris["network.trr.custom_uri"] == config.doh_uri


def test_system_resolver_strips_doh_directives() -> None:
    config = Config(doh_provider="system")
    plan = build_plan(get_browser("firefox"), _profile(), Tier.STRICT, config)
    assert plan.doh_uri is None
    assert not any(p.key.startswith("network.trr.") for p in plan.prefs)
    assert not any(f.flag.startswith("--dns-over-https-mode") for f in plan.flags)


def test_ua_is_pinned_deterministically() -> None:
    config = Config()
    plan_a = build_plan(get_browser("firefox"), _profile(name="seed"), Tier.STRICT, config)
    plan_b = build_plan(get_browser("firefox"), _profile(name="seed"), Tier.STRICT, config)
    assert plan_a.user_agent == plan_b.user_agent
    assert plan_a.user_agent is not None


def test_ua_mode_off_disables_pinning() -> None:
    config = Config(ua_mode="off")
    plan = build_plan(get_browser("firefox"), _profile(), Tier.STRICT, config)
    assert plan.user_agent is None


def test_explicit_ua_overrides() -> None:
    config = Config()
    ua = "Mozilla/5.0 (X11; Linux x86_64) Gecko/20100101 Firefox/128.0"
    plan = build_plan(get_browser("firefox"), _profile(), Tier.STRICT, config, user_agent=ua)
    assert plan.user_agent == ua


def test_harden_firefox_writes_user_js() -> None:
    profile = _profile()
    result = harden(get_browser("firefox"), profile, Tier.STRICT, Config())
    assert result.user_js is not None and result.user_js.is_file()
    text = result.user_js.read_text(encoding="utf-8")
    assert "privacy.resistFingerprinting" in text
    assert "general.useragent.override" in text
    assert profile.tier is Tier.STRICT


def test_harden_chromium_writes_flags_file() -> None:
    profile = _profile("brave", "b1")
    result = harden(get_browser("brave"), profile, Tier.STRICT, Config())
    assert result.flags_file is not None and result.flags_file.is_file()
    payload = json.loads(result.flags_file.read_text(encoding="utf-8"))
    assert payload["args"][0].startswith("--user-data-dir=")
    assert any("--no-pings" in a for a in payload["args"])
    assert payload["doh_uri"] == Config().doh_uri


def test_dry_run_writes_nothing() -> None:
    profile = _profile()
    result = harden(get_browser("firefox"), profile, Tier.STRICT, Config(), dry_run=True)
    assert result.dry_run is True
    assert result.preview is not None
    assert not (profile.path / "user.js").exists()


def test_preview_matches_written_prefs() -> None:
    profile = _profile()
    config = Config()
    preview = preview_firefox(get_browser("firefox"), profile, Tier.STRICT, config)
    harden(get_browser("firefox"), profile, Tier.STRICT, config)
    written = (profile.path / "user.js").read_text(encoding="utf-8")
    for line in preview.splitlines():
        if line.startswith("user_pref("):
            assert line in written
