"""Tests for the throwaway stealth session."""

from __future__ import annotations

from pathlib import Path

import pytest

from eroica.config import Tier
from eroica.stealth import launch_stealth, plan_stealth


@pytest.fixture()
def fake_binary(monkeypatch: pytest.MonkeyPatch) -> Path:
    fake = Path("zen.exe")
    monkeypatch.setattr("eroica.stealth.find_binary", lambda browser: fake)
    return fake


def test_plan_defaults_to_paranoid_and_hardens(fake_binary: Path) -> None:
    session = plan_stealth("zen")
    assert session.tier is Tier.PARANOID
    assert session.profile.path.is_dir()
    user_js = session.profile.path / "user.js"
    assert user_js.is_file()
    assert "privacy.resistFingerprinting" in user_js.read_text(encoding="utf-8")
    assert "webgl.disabled" in user_js.read_text(encoding="utf-8")


def test_plan_creates_fresh_name_every_time(fake_binary: Path) -> None:
    first = plan_stealth("zen").profile.name
    second = plan_stealth("zen").profile.name
    assert first.startswith("stealth-")
    assert first != second


def test_plan_custom_tier_and_ua(fake_binary: Path) -> None:
    session = plan_stealth("zen", tier=Tier.STRICT, user_agent="Mozilla/5.0 (X11; Linux x86_64) Firefox/128.0")
    assert session.tier is Tier.STRICT
    assert session.user_agent.startswith("Mozilla/5.0")


def test_plan_create_false_writes_nothing(fake_binary: Path) -> None:
    session = plan_stealth("zen", create=False)
    assert not session.profile.path.exists()


def test_plan_makes_honest_warnings(fake_binary: Path) -> None:
    session = plan_stealth("zen", create=False)
    assert any("real IP" in warning for warning in session.warnings)


@pytest.mark.parametrize("family,marker", [("zen", "-private-window"), ("brave", "--incognito")])
def test_plan_command_shell_shape(fake_binary: Path, family: str, marker: str) -> None:
    session = plan_stealth(family, create=False, urls=["https://example.com"])
    command = " ".join(session.command)
    assert marker in command
    assert "example.com" in command
    assert "stealth-" in command


def test_launch_dry_run_does_nothing(fake_binary: Path) -> None:
    session = plan_stealth("zen")
    code = launch_stealth(session, dry_run=True)
    assert code == 0
    assert session.profile.path.is_dir()  # untouched by dry run


def test_launch_disposes_profile_afterwards(fake_binary: Path) -> None:
    session = plan_stealth("zen")
    assert session.profile.path.is_dir()
    code = launch_stealth(session, launcher=lambda command: 0)
    assert code == 0
    assert not session.profile.path.exists()
    assert not (session.profile.path / ".eroica.json").exists()


def test_launch_keep_preserves_profile(fake_binary: Path) -> None:
    session = plan_stealth("zen", keep=True)
    code = launch_stealth(session, launcher=lambda command: 7)
    assert code == 7
    assert session.profile.path.is_dir()


def test_launch_keeps_profile_when_launcher_itself_fails(fake_binary: Path) -> None:
    session = plan_stealth("zen")

    def failing_launcher(_command: object) -> int:
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        launch_stealth(session, launcher=failing_launcher)  # type: ignore[arg-type]
    # If the launcher itself raises, the process state is unknown, so we do
    # NOT delete the profile — destroying data while a browser may still be
    # open would be worse than leaving a throwaway dir behind.
    assert session.profile.path.is_dir()


def test_launch_reports_unremovable_profile(
    fake_binary: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If a lingering browser process still holds the profile, the session must
    not pretend to be clean: warn loudly, leave the dir, and exit non-zero."""
    from eroica.errors import ProfileError
    from eroica.profiles import remove_profile as real_remove

    session = plan_stealth("zen")

    def stuck_remove(profile: object, **kwargs: object) -> None:
        raise ProfileError("still in use")

    monkeypatch.setattr("eroica.stealth.remove_profile", stuck_remove)
    code = launch_stealth(session, launcher=lambda command: 0)
    assert code == 1

    monkeypatch.setattr("eroica.stealth.remove_profile", real_remove)
    real_remove(session.profile, missing_ok=True)  # clean the fixture up
    assert not session.profile.path.exists()