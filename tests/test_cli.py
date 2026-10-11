"""End-to-end tests for the command-line interface.

These drive ``main(argv)`` directly and assert on exit codes plus parsed JSON,
so they exercise the full create → harden → audit → remove lifecycle.
"""

from __future__ import annotations

import io
import json
from contextlib import redirect_stdout
from pathlib import Path

import pytest

from eroica.cli import main
from eroica.config import Config, Tier, load_config, save_config
from eroica.net import TOR_DEFAULT, ProbeResult
from eroica.profiles import create_profile, load_profile, remove_profile


def run(argv: list[str]) -> tuple[int, dict]:
    """Run the CLI, returning ``(exit_code, parsed_stdout_json)``."""
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        code = main(argv)
    text = buffer.getvalue().strip()
    payload = json.loads(text) if text.startswith(("{", "[")) else {}
    return code, payload


def test_version() -> None:
    code, payload = run(["--json", "version"])
    assert code == 0
    assert payload["name"] == "eroica"


def test_doctor_json() -> None:
    code, payload = run(["--json", "doctor"])
    assert code == 0
    assert "browsers" in payload
    assert payload["platform"] in {"windows", "macos", "linux"}


def test_symphonies_json_lists_five() -> None:
    code, payload = run(["--json", "symphonies", "--tier", "strict"])
    assert code == 0
    assert [m["nickname"] for m in payload["movements"]] == [
        "First",
        "Eroica",
        "Fate",
        "Pastoral",
        "Choral",
    ]


def test_config_show_and_set_roundtrip() -> None:
    code, _ = run(["--json", "config", "set", "--tier", "paranoid", "--doh", "quad9"])
    assert code == 0
    code, payload = run(["--json", "config", "show"])
    assert code == 0
    assert payload["default_tier"] == "paranoid"
    assert payload["doh_provider"] == "quad9"


def test_full_lifecycle_firefox() -> None:
    code, payload = run(
        ["--json", "new", "-b", "firefox", "-p", "osint", "--tier", "strict"]
    )
    assert code == 0
    assert payload["hardened"] is True

    code, payload = run(["--json", "profiles", "-b", "firefox"])
    assert code == 0
    assert [p["profile"] for p in payload["profiles"]] == ["osint"]

    code, payload = run(["--json", "audit", "-b", "firefox", "-p", "osint", "--tier", "strict"])
    assert code == 0
    assert payload["healthy"] is True

    code, _ = run(["--json", "remove", "-b", "firefox", "-p", "osint", "--yes"])
    assert code == 0

    code, payload = run(["--json", "profiles", "-b", "firefox"])
    assert payload["profiles"] == []


def test_harden_dry_run_does_not_touch_disk() -> None:
    run(["--json", "new", "-b", "firefox", "-p", "dry", "--no-harden"])
    code, payload = run(["--json", "harden", "-b", "firefox", "-p", "dry", "--dry-run"])
    assert code == 0
    assert payload["dry_run"] is True
    assert "user_js" in payload

    # Nothing written, so the audit should complain.
    code, _ = run(["--json", "audit", "-b", "firefox", "-p", "dry"])
    assert code == 1


def test_launch_dry_run_chromium() -> None:
    run(["--json", "new", "-b", "brave", "-p", "b1"])
    code, payload = run(["--json", "launch", "-b", "brave", "-p", "b1", "--dry-run",
                         "https://example.com"])
    assert code == 0
    assert any("--user-data-dir=" in arg for arg in payload["command"])
    assert payload["command"][-1] == "https://example.com"


def test_stealth_cli_dry_run(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("eroica.stealth.find_binary", lambda browser: Path("zen.exe"))
    code, payload = run(["--json", "stealth", "-b", "zen", "--dry-run", "https://x.test"])
    assert code == 0
    assert payload["tier"] == "paranoid"
    assert payload["ephemeral"] is True
    assert payload["private"] is True
    assert any("-private-window" in a or "--incognito" in a for a in payload["command"])
    assert payload["command"][-1] == "https://x.test"


def test_purge_cli_removes_profile() -> None:
    profile = create_profile("firefox", "purge-me", tier=Tier.STRICT)
    code, payload = run(["--json", "purge", "-b", "firefox", "-p", "purge-me", "--timeout", "5"])
    assert code == 0
    assert payload["purged"] == "purge-me"
    assert not profile.path.exists()


def test_purge_cli_waits_for_release(monkeypatch: pytest.MonkeyPatch) -> None:
    from eroica.errors import ProfileError

    profile = create_profile("firefox", "purge-wait", tier=Tier.STRICT)

    real_remove = remove_profile
    attempts = {"left": 1}

    def flaky_remove(profile: object, **kwargs: object) -> None:
        if attempts["left"] > 0:
            attempts["left"] -= 1
            raise ProfileError("busy")
        real_remove(profile, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr("eroica.cli.remove_profile", flaky_remove)
    code, payload = run(["--json", "purge", "-b", "firefox", "-p", "purge-wait", "--timeout", "5", "--poll", "0.05"])
    assert code == 0
    assert not profile.path.exists()


def test_purge_cli_gives_up_after_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    from eroica.errors import ProfileError

    profile = create_profile("firefox", "purge-stuck", tier=Tier.STRICT)

    def stuck_remove(profile: object, **kwargs: object) -> None:
        raise ProfileError("still held")

    monkeypatch.setattr("eroica.cli.remove_profile", stuck_remove)
    code, _ = run(["--json", "purge", "-b", "firefox", "-p", "purge-stuck", "--timeout", "1", "--poll", "0.05"])
    assert code == 1
    assert profile.path.exists()

    remove_profile(profile)  # clean the fixture up
    assert not profile.path.exists()


def test_tor_on_off_toggle() -> None:
    save_config(Config())
    code, payload = run(["--json", "tor", "on"])
    assert code == 0
    assert payload["proxy"] == TOR_DEFAULT
    assert payload["tor"] is True
    assert load_config().proxy == TOR_DEFAULT

    code, payload = run(["--json", "tor", "off"])
    assert code == 0
    assert payload["tor"] is False
    assert load_config().proxy is None


def test_tor_status_and_apply_rehardens() -> None:
    profile = create_profile("firefox", "net-applied", tier=Tier.STRICT)
    run(["--json", "tor", "on", "--apply"])
    assert load_profile("firefox", "net-applied").meta.get("proxy") == TOR_DEFAULT

    code, payload = run(["--json", "tor"])
    assert code == 0
    assert payload["tor"] is True
    assert payload["proxy"] == TOR_DEFAULT

    run(["--json", "tor", "off", "--apply"])
    assert load_profile("firefox", "net-applied").meta.get("proxy") is None
    assert profile.path.is_dir()  # unharmed
    remove_profile(profile)


def test_proxy_set_and_clear() -> None:
    code, _ = run(["--json", "proxy", "socks5://10.0.0.5:1080"])
    assert code == 0
    assert load_config().proxy == "socks5://10.0.0.5:1080"

    code, payload = run(["--json", "proxy", "off"])
    assert code == 0
    assert payload["proxy"] is None
    assert load_config().proxy is None


def test_proxy_rejects_unsupported_scheme() -> None:
    code, _ = run(["--json", "proxy", "http://x:80"])
    assert code == 1
    assert load_config().proxy is None


def test_check_ip_json_report(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = ProbeResult(proxy=None, direct_ip="203.0.113.9", exit_ip=None, reachable=True)
    monkeypatch.setattr("eroica.net.probe_network", lambda config, *, timeout: fake)
    code, payload = run(["--json", "check-ip"])
    assert code == 0
    assert payload["direct_ip"] == "203.0.113.9"
    assert payload["exit_ip"] is None
    assert payload["match"] is None


def test_check_ip_expect_match(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = ProbeResult(
        proxy="socks5://127.0.0.1:9050",
        direct_ip="198.51.100.1",
        exit_ip="185.220.101.4",
        reachable=True,
    )
    monkeypatch.setattr("eroica.net.probe_network", lambda config, *, timeout: fake)
    code, payload = run(["--json", "check-ip", "--expect", "185.220.101.4"])
    assert code == 0
    assert payload["match"] is True


def test_check_ip_expect_mismatch_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = ProbeResult(
        proxy="socks5://127.0.0.1:9050",
        direct_ip="198.51.100.1",
        exit_ip="185.220.101.4",
        reachable=True,
    )
    monkeypatch.setattr("eroica.net.probe_network", lambda config, *, timeout: fake)
    code, payload = run(["--json", "check-ip", "--expect", "9.9.9.9"])
    assert code == 1
    assert payload["match"] is False


def test_check_ip_expect_unverifiable_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = ProbeResult(
        proxy="socks5://127.0.0.1:9050",
        direct_ip="198.51.100.1",
        exit_ip=None,
        reachable=False,
        error="connection refused",
    )
    monkeypatch.setattr("eroica.net.probe_network", lambda config, *, timeout: fake)
    code, _ = run(["--json", "check-ip", "--expect", "185.220.101.4"])
    assert code == 1


def test_launch_uses_materialized_proxy_flags() -> None:
    save_config(Config(proxy="socks5://127.0.0.1:9050"))
    create_profile("chrome", "net-launch", tier=Tier.STRICT)
    code, _ = run(["--json", "harden", "-b", "chrome", "-p", "net-launch", "-t", "strict"])
    assert code == 0

    code, payload = run(["--json", "launch", "-b", "chrome", "-p", "net-launch", "--dry-run"])
    assert code == 0
    assert any("--proxy-server=socks5://127.0.0.1:9050" in a for a in payload["command"])
    assert not any("--dns-over-https-mode" in a for a in payload["command"])
    assert any("--disable-features=DnsOverHttps" in a for a in payload["command"])

    remove_profile(load_profile("chrome", "net-launch"))


def test_unknown_browser_exits_nonzero() -> None:
    code, _ = run(["--json", "new", "-b", "netscape", "-p", "x"])
    assert code == 1


def test_unknown_profile_exits_nonzero() -> None:
    code, _ = run(["--json", "audit", "-b", "firefox", "-p", "missing"])
    assert code == 1


def test_config_set_rejects_unknown_doh() -> None:
    with pytest.raises(SystemExit):
        main(["config", "set", "--doh", "notreal"])
