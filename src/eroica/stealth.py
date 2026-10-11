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

import secrets
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass

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

__all__ = ["StealthSession", "launch_stealth", "plan_stealth"]

#: Every stealth run gets a fresh identity — nothing is ever reused or pinned.
_NAME_PREFIX = "stealth-"

_STANDARD_WARNINGS: tuple[str, ...] = (
    "Network anonymity is NOT included: the endpoint still sees your real IP.",
    "Add a VPN or Tor underneath if that matters.",
    "This is a throwaway identity: every session starts completely blank.",
)


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


def launch_stealth(
    session: StealthSession,
    *,
    dry_run: bool = False,
    launcher: Callable[[Sequence[str]], int] | None = None,
) -> int:
    """Run a stealth session and dispose of the profile afterwards.

    Args:
        session: A session returned by :func:`plan_stealth`.
        dry_run: Only report what would happen; never launches or deletes.
        launcher: Test seam; defaults to :func:`_default_launcher`.
    """
    if dry_run:
        return 0

    run = launcher or _default_launcher
    code = run(session.command)

    if not session.keep:
        try:
            remove_profile(session.profile, missing_ok=True)
        except ProfileError as exc:
            _log.warning("could not discard throwaway profile %s: %s", session.profile.name, exc)
            _log.warning(
                "the profile was left behind; once the browser is fully closed run "
                "'eroica remove -b %s -p %s' to finish the job",
                session.browser.key,
                session.profile.name,
            )
            return 1
        _log.info("discarded throwaway profile %s", session.profile.name)
    else:
        _log.info("kept profile %s at %s (--keep)", session.profile.name, session.profile.path)
    return code