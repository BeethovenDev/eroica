"""Tests for the network layer (SOCKS proxy + exit-IP verification)."""

from __future__ import annotations

import pytest

from eroica.browsers import get_browser
from eroica.config import Config
from eroica.errors import ConfigError
from eroica.hardening import build_plan
from eroica.net import (
    ProxySetting,
    parse_proxy,
    probe_network,
    proxy_chromium_flags,
    proxy_firefox_prefs,
)
from eroica.profiles import create_profile, remove_profile


def test_parse_proxy_valid() -> None:
    proxy = parse_proxy("socks5://127.0.0.1:9050")
    assert proxy is not None
    assert proxy.host == "127.0.0.1"
    assert proxy.port == 9050
    assert proxy.as_url() == "socks5://127.0.0.1:9050"


def test_parse_proxy_normalises_socks5h() -> None:
    proxy = parse_proxy("socks5h://10.0.0.8:1080")
    assert proxy is not None and proxy.scheme == "socks5"


@pytest.mark.parametrize(
    "bad",
    [
        "http://proxy:8080",
        "socks5://",
        "socks5://host:nope",
        "socks5://host:70000",
        "socks5://host",
        "ftp://x",
    ],
)
def test_parse_proxy_rejects_invalid(bad: str) -> None:
    with pytest.raises(ConfigError):
        parse_proxy(bad)


def test_parse_proxy_clears_markers() -> None:
    assert parse_proxy(None) is None
    assert parse_proxy("") is None
    assert parse_proxy("off") is None
    assert parse_proxy("none") is None


def test_proxy_firefox_prefs_route_dns_inside_tunnel() -> None:
    setting = ProxySetting(scheme="socks5", host="127.0.0.1", port=9050)
    prefs = {p.key: p.value for p in proxy_firefox_prefs(setting)}
    assert prefs["network.proxy.type"] == 1
    assert prefs["network.proxy.socks"] == "127.0.0.1"
    assert prefs["network.proxy.socks_port"] == 9050
    assert prefs["network.proxy.socks_remote_dns"] is True
    assert prefs["network.proxy.share_proxy_settings"] is True
    assert prefs["network.trr.mode"] == 5


def test_proxy_chromium_flags_force_remote_dns() -> None:
    setting = ProxySetting(scheme="socks5", host="127.0.0.1", port=9050)
    flags = [f.flag for f in proxy_chromium_flags(setting)]
    assert "--proxy-server=socks5://127.0.0.1:9050" in flags
    assert any("host-resolver-rules" in f for f in flags)
    assert any("DnsOverHttps" in f for f in flags)


def test_build_plan_folds_proxy_into_mozilla_plan() -> None:
    config = Config(proxy="socks5://127.0.0.1:9050")
    browser = get_browser("firefox")
    profile = create_profile("firefox", "net-test", tier=config.default_tier)
    plan = build_plan(browser, profile, config.default_tier, config)
    keys = {p.key for p in plan.prefs}
    assert "network.proxy.socks" in keys
    assert "network.trr.mode" in keys
    assert not any(k.startswith("network.trr.uri") for k in keys)
    assert plan.doh_uri is None
    assert plan.proxy == "socks5://127.0.0.1:9050"
    remove_profile(profile, missing_ok=True)


def test_build_plan_folds_proxy_into_chromium_plan_and_kills_doh() -> None:
    config = Config(proxy="socks5://127.0.0.1:9050")
    browser = get_browser("brave")
    profile = create_profile("brave", "net-test", tier=config.default_tier)
    plan = build_plan(browser, profile, config.default_tier, config)
    flagset = {f.flag for f in plan.flags}
    assert any(f.startswith("--proxy-server=") for f in flagset)
    assert not any(f.startswith("--dns-over-https-mode") for f in flagset)
    assert plan.doh_uri is None
    remove_profile(profile, missing_ok=True)


def test_build_plan_leaves_dns_alone_without_proxy() -> None:
    config = Config()
    browser = get_browser("firefox")
    profile = create_profile("firefox", "net-test", tier=config.default_tier)
    plan = build_plan(browser, profile, config.default_tier, config)
    keys = {p.key for p in plan.prefs}
    assert plan.proxy is None
    assert "network.proxy.socks" not in keys
    assert "network.trr.uri" in keys  # DoH stays on without a proxy
    assert plan.doh_uri is not None
    remove_profile(profile, missing_ok=True)


def test_probe_network_reports_direct_when_no_proxy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("eroica.net._fetch_direct", lambda *, timeout: "198.51.100.9")
    result = probe_network(Config())
    assert result.proxy is None
    assert result.direct_ip == "198.51.100.9"
    assert result.exit_ip is None
    assert result.reachable is True


def test_probe_network_tunnels_when_proxy_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("eroica.net._fetch_direct", lambda *, timeout: "198.51.100.9")
    monkeypatch.setattr(
        "eroica.net._fetch_via_proxy",
        lambda proxy, *, timeout: ("185.220.101.4", None),
    )
    result = probe_network(Config(proxy="socks5://127.0.0.1:9050"))
    assert result.exit_ip == "185.220.101.4"
    assert result.reachable is True


def test_probe_network_surfaces_proxy_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("eroica.net._fetch_direct", lambda *, timeout: "198.51.100.9")
    monkeypatch.setattr(
        "eroica.net._fetch_via_proxy",
        lambda proxy, *, timeout: (None, "connection refused"),
    )
    result = probe_network(Config(proxy="socks5://127.0.0.1:9050"))
    assert result.exit_ip is None
    assert result.reachable is False
    assert result.error == "connection refused"