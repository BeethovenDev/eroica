"""Throwaway, fully hardened, self-destructing browsing sessions.

``eroica stealth`` is a one-shot workflow for quick OSINT lookups:

1. generate a brand-new random profile (nothing reused → nothing correlated);
2. harden it at the requested tier (default ``PARANOID``, the maximum);
3. launch the browser in private mode on that isolated profile;
4. delete the profile as soon as the browser closes.

Anonymity note: an ephemeral profile protects your *identity inside the site*,
not your *network identity*. Your real IP stays visible to the endpoint unless
you add a VPN or Tor underneath. Every session banner says so.

The launch step is injectable (``launcher=...``) so the orchestration and the
cleanup behaviour can be tested without opening a real browser.
"""

from __future__ import annotations

import os
import secrets
import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from eroica import log, ua
from eroica.browsers import Browser, BrowserFamily, find_binary, get_browser
from eroica.config import Config, Tier
from eroica.errors import BrowserNotFound, ProfileError
from eroica.flags import build_args
from eroica.hardening import harden
from eroica.paths import data_home
from eroica.profiles import Profile, create_profile, remove_profile
from eroica.symphonies import collect_flags

_log = log.get_logger("stealth")

__all__ = ["StealthResult", "StealthSession", "launch_stealth", "plan_stealth"]

#: Every stealth run gets a fresh identity — nothing is ever reused or pinned.
_NAME_PREFIX = "stealth-"

_STANDARD_WARNINGS: tuple[str, ...] = (
    "Network anonymity is NOT included: the endpoint still sees your real IP.",
    "Add a VPN or Tor underneath if that matters.",
    "This is a throwaway identity: every session starts completely blank.",
)

#: A browser that just closed often keeps child processes holding profile files
#: for a while (Windows is famous for this). ``stealth`` waits for the locks to
#: clear immediately; if they don't, it schedules a detached ``purge`` worker
#: that hangs around for up to this many seconds and finishes the deletion as
#: soon as the files are released.
PURGE_TIMEOUT_SECONDS = 300


@dataclass
class StealthResult:
    """Outcome of a finished stealth session."""

    #: Return code of the browser process (or ``1`` if disposal failed and no
    #: background purge could be scheduled).
    exit_code: int
    #: ``True`` when the throwaway profile was deleted in-process.
    discarded: bool
    #: ``True`` when a detached ``purge`` worker was scheduled to finish the
    #: deletion once the profile's files are released.
    purge_scheduled: bool = False


@dataclass
class StealthSession:
    """A fully planned, not-yet-run stealth session."""

    browser: Browser
    profile: Profile
    tier: Tier
    user_agent: str
    keep: bool
    command: list[str]
    warnings: tuple[str, ...] = _STANDARD_WARNINGS


def _make_name() -> str:
    return f"{_NAME_PREFIX}{secrets.token_hex(4)}"


def plan_stealth(
    browser_key: str,
    *,
    tier: Tier = Tier.PARANOID,
    user_agent: str | None = None,
    keep: bool = False,
    urls: Sequence[str] = (),
    create: bool = True,
    config: Config | None = None,
) -> StealthSession:
    """Create (or plan) a stealth session for ``browser_key``.

    Args:
        tier: Hardening tier; defaults to :attr:`Tier.PARANOID`.
        user_agent: Explicit User-Agent; otherwise a fresh one is chosen for
            this session (a new random profile gets a new random identity).
        keep: Keep the profile after the browser closes instead of deleting it.
        urls: URLs to open in the session.
        create: Materialise the profile on disk. ``False`` only builds the
            launch command (used by ``--dry-run``).
        config: Configuration override (DoH provider, UA mode).
    """
    browser = get_browser(browser_key)
    binary = find_binary(browser)
    if binary is None:
        raise BrowserNotFound(f"{browser.name} executable not found; run 'eroica doctor'")

    active_config = config or Config()
    name = _make_name()
    pinned_ua = ua.validate(user_agent) if user_agent else ua.pick(f"stealth::{name}")

    if create:
        profile = create_profile(browser.key, name, tier=tier, user_agent=pinned_ua)
        try:
            harden(browser, profile, tier, active_config, user_agent=pinned_ua, backup=False)
        except Exception:
            remove_profile(profile, missing_ok=True)
            raise
    else:
        path = data_home() / "profiles" / browser.key / name
        profile = Profile(name=name, browser_key=browser.key, path=path,
                          meta={"tier": tier.name.lower(), "user_agent": pinned_ua})

    if browser.family is BrowserFamily.MOZILLA:
        command = [
            str(binary), "-profile", str(profile.path), "-no-remote", "-private-window",
            *list(urls),
        ]
    else:
        command = [
            str(binary),
            *build_args(
                profile.path,
                collect_flags(tier),
                user_agent=pinned_ua,
                doh_uri=active_config.doh_uri,
                private=True,
                extra=list(urls),
            ),
        ]

    return StealthSession(
        browser=browser,
        profile=profile,
        tier=tier,
        user_agent=pinned_ua,
        keep=keep,
        command=command,
    )


def _default_launcher(command: Sequence[str]) -> int:
    """Launch a browser detached and wait for it to exit, returning its code."""
    process = subprocess.Popen(list(command))
    try:
        process.wait()
    except KeyboardInterrupt:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:  # pragma: no cover - rare
            process.kill()
        return 130
    return int(process.returncode or 0)


def _spawn_purge(session: StealthSession) -> bool:
    """Detach a ``purge`` worker that will finish deleting the profile.

    The worker keeps retrying removal for up to :data:`PURGE_TIMEOUT_SECONDS`,
    independent of this process's lifetime, so a slow browser teardown can no
    longer defeat the self-destruct. Returns ``False`` if the worker could not
    be started (then the caller falls back to telling the user).
    """
    command = [
        sys.executable,
        "-m",
        "eroica",
        "purge",
        "-b",
        session.browser.key,
        "-p",
        session.profile.name,
        "--timeout",
        str(PURGE_TIMEOUT_SECONDS),
    ]
    if os.name == "nt":
        kwargs: dict[str, Any] = {
            "creationflags": getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            | getattr(subprocess, "DETACHED_PROCESS", 0),
        }
    else:  # pragma: no cover - POSIX
        kwargs = {"start_new_session": True}
    try:
        subprocess.Popen(  # noqa: S603 - trusted argv, fully ours
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            **kwargs,
        )
    except OSError as exc:
        _log.warning("could not start background cleanup worker: %s", exc)
        return False
    _log.info("background purge worker started for profile %s", session.profile.name)
    return True


def launch_stealth(
    session: StealthSession,
    *,
    dry_run: bool = False,
    launcher: Callable[[Sequence[str]], int] | None = None,
) -> StealthResult:
    """Run a stealth session and dispose of the profile afterwards.

    Args:
        session: A session returned by :func:`plan_stealth`.
        dry_run: Only report what would happen; never launches or deletes.
        launcher: Test seam; defaults to :func:`_default_launcher`.
    """
    if dry_run:
        return StealthResult(exit_code=0, discarded=False)

    run = launcher or _default_launcher
    code = run(session.command)

    if session.keep:
        _log.info("kept profile %s at %s (--keep)", session.profile.name, session.profile.path)
        return StealthResult(exit_code=code, discarded=False)

    try:
        remove_profile(session.profile, missing_ok=True)
    except ProfileError as exc:
        _log.warning(
            "could not discard throwaway profile %s immediately: %s",
            session.profile.name,
            exc,
        )
        if _spawn_purge(session):
            _log.warning(
                "background cleanup scheduled: the profile will be removed as soon "
                "as the browser releases its files"
            )
            return StealthResult(exit_code=code, discarded=False, purge_scheduled=True)
        _log.warning(
            "the profile was left behind; once the browser is fully closed run "
            "'eroica remove -b %s -p %s' to finish the job",
            session.browser.key,
            session.profile.name,
        )
        return StealthResult(exit_code=1, discarded=False)

    _log.info("discarded throwaway profile %s", session.profile.name)
    return StealthResult(exit_code=code, discarded=True)