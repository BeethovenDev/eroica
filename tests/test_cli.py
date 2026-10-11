"""End-to-end tests for the command-line interface.

These drive ``main(argv)`` directly and assert on exit codes plus parsed JSON,
so they exercise the full create → harden → audit → remove lifecycle.
"""

from __future__ import annotations

import io
import json
from contextlib import redirect_stdout

import pytest

from eroica.cli import main


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


def test_unknown_browser_exits_nonzero() -> None:
    code, _ = run(["--json", "new", "-b", "netscape", "-p", "x"])
    assert code == 1


def test_unknown_profile_exits_nonzero() -> None:
    code, _ = run(["--json", "audit", "-b", "firefox", "-p", "missing"])
    assert code == 1


def test_config_set_rejects_unknown_doh() -> None:
    with pytest.raises(SystemExit):
        main(["config", "set", "--doh", "notreal"])
