"""EROICA command-line interface.

Exit codes
----------
``0`` success · ``1`` expected error · ``2`` argument error (from argparse).
"""

from __future__ import annotations

import argparse
import contextlib
import json
import subprocess
import sys
import time
from collections.abc import Sequence
from typing import Any

from eroica import BANNER, __version__, log, ua
from eroica.audit import audit_profile
from eroica.browsers import (
    BrowserFamily,
    detect_browsers,
    find_binary,
    get_browser,
)
from eroica.config import DOH_PROVIDERS, Config, Tier, config_path, load_config, save_config
from eroica.errors import EroicaError, ProfileError
from eroica.flags import build_args
from eroica.hardening import harden, preview_firefox
from eroica.paths import data_home, os_name
from eroica.profiles import (
    Profile,
    create_profile,
    list_profiles,
    profiles_root,
    remove_profile,
    resolve_profile,
    validate_name,
)
from eroica.stealth import launch_stealth, plan_stealth
from eroica.symphonies import SYMPHONIES, collect_flags, collect_prefs

_log = log.get_logger("cli")


# --------------------------------------------------------------------------- #
# Output helpers
# --------------------------------------------------------------------------- #
def _configure_console_encoding() -> None:
    """Best-effort switch of stdout/stderr to UTF-8.

    Windows consoles often default to a legacy codepage (e.g. cp1251) that
    cannot encode characters such as ``♭`` or ``→``. Reconfiguring avoids a
    crash; ``errors="replace"`` keeps output flowing even on exotic terminals.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        with contextlib.suppress(ValueError, OSError):  # pragma: no cover - platform dependent
            reconfigure(encoding="utf-8", errors="replace")


def _emit(args: argparse.Namespace, payload: Any, text: str) -> None:
    """Print either machine-readable JSON or human text."""
    if getattr(args, "json", False):
        json.dump(payload, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
    else:
        print(text)


def _tick(ok: bool) -> str:
    return "ok  " if ok else "FAIL"


# --------------------------------------------------------------------------- #
# Browser / profile resolution
# --------------------------------------------------------------------------- #
def _resolve_browser_key(key: str | None) -> str:
    if key:
        return get_browser(key).key
    installed = [d for d in detect_browsers() if d.installed]
    if len(installed) == 1:
        return installed[0].browser.key
    if not installed:
        raise EroicaError("no supported browser detected; pass --browser explicitly")
    names = ", ".join(d.browser.key for d in installed)
    raise EroicaError(f"multiple browsers detected ({names}); pass --browser")


def _tier(args: argparse.Namespace, config: Config) -> Tier:
    return Tier.coerce(args.tier) if getattr(args, "tier", None) else config.default_tier


# --------------------------------------------------------------------------- #
# Commands
# --------------------------------------------------------------------------- #
def cmd_version(args: argparse.Namespace) -> int:
    payload = {"name": "eroica", "version": __version__}
    _emit(args, payload, f"eroica {__version__}")
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    detected = detect_browsers(only=args.browser)
    rows = []
    for item in detected:
        rows.append(
            {
                "key": item.browser.key,
                "name": item.browser.name,
                "family": item.browser.family.value,
                "installed": item.installed,
                "binary": str(item.binary) if item.binary else None,
                "profile_roots": [str(p) for p in item.profile_roots],
            }
        )
    payload = {
        "platform": os_name(),
        "python": sys.version.split()[0],
        "config_path": str(config_path()),
        "config_home": str(config_path().parent),
        "data_home": str(data_home()),
        "browsers": rows,
    }
    if args.json:
        _emit(args, payload, "")
        return 0

    print(BANNER)
    print()
    print(f"platform    : {payload['platform']}")
    print(f"python      : {payload['python']}")
    print(f"config      : {payload['config_path']}")
    print(f"profiles    : {payload['data_home']}")
    print()
    print(f"{'browser':<12} {'family':<9} {'status':<9} path")
    print("-" * 72)
    for row in rows:
        status = "installed" if row["installed"] else "-"
        location = row["binary"] or "(not found)"
        print(f"{row['key']:<12} {row['family']:<9} {status:<9} {location}")
    return 0


def cmd_symphonies(args: argparse.Namespace) -> int:
    config = load_config()
    tier = _tier(args, config)
    entries = []
    for movement in SYMPHONIES:
        entries.append(
            {
                "key": movement.key,
                "roman": movement.roman,
                "nickname": movement.nickname,
                "title": movement.title,
                "opus": movement.opus,
                "year": movement.year,
                "signature": movement.signature,
                "summary": movement.summary,
                "prefs": len(movement.prefs_at(tier)),
                "flags": len(movement.flags_at(tier)),
            }
        )
    payload = {"tier": tier.name.lower(), "movements": entries}
    if args.json:
        _emit(args, payload, "")
        return 0

    print(f"EROICA · five movements at tier '{tier.name.lower()}'")
    print()
    for entry in entries:
        setting = f"{entry['prefs']} prefs / {entry['flags']} flags"
        print(f"{entry['roman']:<3} {entry['nickname']:<9} {entry['title']}")
        print(f"    {entry['opus']} ({entry['year']}) · {entry['signature']} · {setting}")
        print(f"    {entry['summary']}")
        print()
    print(f"Totals at this tier: {len(collect_prefs(tier))} unique prefs, "
          f"{len(collect_flags(tier))} unique flags.")
    return 0


def cmd_config(args: argparse.Namespace) -> int:
    config = load_config()
    if args.config_command == "set":
        changed = False
        if args.tier:
            config.default_tier = Tier.coerce(args.tier)
            changed = True
        if args.doh:
            config.doh_provider = args.doh
            changed = True
        if args.ua_mode:
            config.ua_mode = args.ua_mode
            changed = True
        if args.backup is not None:
            config.backup_user_js = args.backup
            changed = True
        if changed:
            save_config(config)
            _log.info("updated %s", config_path())

    payload = config.to_dict()
    payload["config_path"] = str(config_path())
    payload["doh_uri"] = config.doh_uri
    payload["doh_providers"] = sorted(DOH_PROVIDERS)
    if args.json:
        _emit(args, payload, "")
        return 0

    print(f"config file : {payload['config_path']}")
    print(f"default tier: {payload['default_tier']}")
    print(f"doh provider: {payload['doh_provider']} ({config.doh_uri or 'system resolver'})")
    print(f"ua mode     : {payload['ua_mode']}")
    print(f"backup      : {'on' if config.backup_user_js else 'off'}")
    return 0


def cmd_new(args: argparse.Namespace) -> int:
    config = load_config()
    tier = _tier(args, config)
    browser = get_browser(_resolve_browser_key(args.browser))
    pinned_ua = ua.validate(args.ua) if args.ua else ua.pick(f"{browser.key}:{args.profile}")
    profile = create_profile(browser.key, args.profile, tier=tier, user_agent=pinned_ua)

    result = None
    if not args.no_harden:
        result = harden(browser, profile, tier, config, user_agent=pinned_ua, dry_run=args.dry_run)

    payload = {
        "browser": browser.key,
        "profile": profile.name,
        "path": str(profile.path),
        "tier": tier.name.lower(),
        "user_agent": pinned_ua,
        "hardened": result is not None,
    }
    if args.json:
        _emit(args, payload, "")
        return 0

    _log.info("created profile %s for %s", profile.name, browser.name)
    print(f"profile  : {profile.name}")
    print(f"location : {profile.path}")
    print(f"tier     : {tier.name.lower()}")
    print(f"ua       : {pinned_ua}")
    if result is not None:
        print(f"hardened : {result.summary()}")
        print()
        print(f"launch it: eroica launch -b {browser.key} -p {profile.name}")
    return 0


def cmd_profiles(args: argparse.Namespace) -> int:
    profiles = list_profiles(get_browser(args.browser).key if args.browser else None)
    rows = [
        {
            "browser": p.browser_key,
            "profile": p.name,
            "tier": p.meta.get("tier", "-"),
            "user_agent": p.meta.get("user_agent"),
            "path": str(p.path),
        }
        for p in profiles
    ]
    if args.json:
        _emit(args, {"profiles": rows}, "")
        return 0

    if not rows:
        print("no EROICA profiles yet — create one with 'eroica new'")
        return 0
    print(f"{'browser':<10} {'profile':<20} {'tier':<9} path")
    print("-" * 72)
    for row in rows:
        print(f"{row['browser']:<10} {row['profile']:<20} {str(row['tier']):<9} {row['path']}")
    return 0


def cmd_remove(args: argparse.Namespace) -> int:
    browser = get_browser(_resolve_browser_key(args.browser))
    profile = resolve_profile(browser.key, args.profile)
    if not args.yes and not getattr(args, "json", False):
        answer = input(f"remove profile '{profile.name}' at {profile.path}? [y/N] ").strip().lower()
        if answer not in {"y", "yes"}:
            print("aborted")
            return 1
    remove_profile(profile)
    _emit(args, {"removed": profile.name, "path": str(profile.path)}, f"removed {profile.name}")
    return 0


def cmd_harden(args: argparse.Namespace) -> int:
    config = load_config()
    tier = _tier(args, config)
    browser = get_browser(_resolve_browser_key(args.browser))
    profile = resolve_profile(browser.key, args.profile)

    if args.dry_run and browser.family is BrowserFamily.MOZILLA:
        content = preview_firefox(browser, profile, tier, config, user_agent=args.ua)
        _emit(args, {"dry_run": True, "user_js": content}, content)
        return 0

    result = harden(
        browser,
        profile,
        tier,
        config,
        user_agent=args.ua,
        dry_run=args.dry_run,
        backup=not args.no_backup,
    )
    payload = {
        "browser": browser.key,
        "profile": profile.name,
        "tier": tier.name.lower(),
        "prefs": result.prefs_count,
        "flags": result.flags_count,
        "user_js": str(result.user_js) if result.user_js else None,
        "backup": str(result.backup) if result.backup else None,
        "flags_file": str(result.flags_file) if result.flags_file else None,
        "dry_run": result.dry_run,
    }
    _emit(args, payload, result.summary())
    return 0


def cmd_audit(args: argparse.Namespace) -> int:
    config = load_config()
    tier = _tier(args, config)
    browser = get_browser(_resolve_browser_key(args.browser))
    profile = resolve_profile(browser.key, args.profile)
    report = audit_profile(browser, profile, tier, config)

    if args.json:
        _emit(args, report.to_dict(), "")
        return 0 if report.healthy else 1

    print(f"audit · {browser.name} · profile '{profile.name}' · tier {tier.name.lower()}")
    print(f"path  · {profile.path}")
    print()
    for check in report.checks:
        detail = f"  {check.detail}" if check.detail else ""
        print(f"[{_tick(check.ok)}] {check.label}{detail}")
    print()
    print("verdict:", "healthy" if report.healthy else "drift detected — re-run 'eroica harden'")
    return 0 if report.healthy else 1


def cmd_launch(args: argparse.Namespace) -> int:
    config = load_config()
    tier = _tier(args, config)
    browser = get_browser(_resolve_browser_key(args.browser))
    binary = find_binary(browser)
    if binary is None and not args.dry_run:
        raise EroicaError(f"{browser.name} executable not found; run 'eroica doctor'")
    executable = str(binary) if binary else f"<{browser.key}>"

    profile = resolve_profile(browser.key, args.profile)
    urls = [u for u in (args.urls or []) if u != "--"]

    if browser.family is BrowserFamily.MOZILLA:
        command = [executable, "-profile", str(profile.path), "-no-remote"]
        if args.private:
            command.append("-private-window")
        command.extend(urls)
    else:
        args_vec = build_args(
            profile.path,
            collect_flags(tier),
            user_agent=profile.user_agent,
            doh_uri=config.doh_uri,
            private=args.private,
            extra=urls,
        )
        command = [executable, *args_vec]

    if args.dry_run:
        payload = {"command": command, "tier": tier.name.lower()}
        _emit(args, payload, " ".join(command))
        return 0

    _log.info("launching %s", browser.name)
    try:
        subprocess.Popen(command)  # noqa: S603 - user-controlled, intentional
    except OSError as exc:
        raise EroicaError(f"failed to launch {browser.name}: {exc}") from exc
    _emit(args, {"launched": command[0], "args": command[1:]}, f"launched {browser.name}")
    return 0


def cmd_stealth(args: argparse.Namespace) -> int:
    """Launch a throwaway, fully hardened, self-destructing session."""
    config = load_config()
    tier = Tier.coerce(args.tier) if args.tier else Tier.PARANOID
    urls = [u for u in (args.urls or []) if u != "--"]
    browser_key = _resolve_browser_key(args.browser)
    session = plan_stealth(
        browser_key,
        tier=tier,
        user_agent=args.ua,
        keep=args.keep,
        urls=urls,
        create=not args.dry_run,
        config=config,
    )

    base_payload = {
        "browser": browser_key,
        "tier": tier.name.lower(),
        "ephemeral": True,
        "private": True,
        "keep": bool(args.keep),
        "user_agent": session.user_agent,
        "command": session.command,
    }
    if args.dry_run:
        _emit(args, base_payload, " ".join(session.command))
        return 0

    for warning in session.warnings:
        _log.warning("%s", warning)
    print(f"STEALTH · {session.browser.name} · tier {tier.name.lower()} · profile {session.profile.name}")
    print(f"        profile will be discarded when the browser closes "
          f"{'unless --keep' if args.keep else ''}".rstrip())

    result = launch_stealth(session)

    if result.purge_scheduled:
        summary = (
            f"stealth session ended (exit {result.exit_code}); the profile is still "
            f"locked by the browser, background cleanup scheduled"
        )
    elif result.discarded:
        summary = f"stealth session ended (exit {result.exit_code}); profile discarded"
    else:
        summary = (
            f"stealth session ended (exit {result.exit_code}); the profile was left "
            f"behind — run 'eroica remove -b {browser_key} -p {session.profile.name}'"
        )

    payload = {
        **base_payload,
        "profile": session.profile.name,
        "discarded": result.discarded,
        "purge_scheduled": result.purge_scheduled,
        "exit_code": result.exit_code,
    }
    _emit(args, payload, summary)
    return result.exit_code


def cmd_purge(args: argparse.Namespace) -> int:
    """Wait until a profile's files are released, then delete it.

    ``stealth`` hands over to this worker when a freshly-closed browser still
    holds profile files. It retries deletion until the directory is gone or
    ``--timeout`` seconds elapse. Also usable standalone — same semantics as
    ``remove``, only with patience.
    """
    browser = get_browser(_resolve_browser_key(args.browser))
    name = validate_name(args.profile)
    path = profiles_root(browser.key) / name
    deadline = time.monotonic() + args.timeout

    _log.info("purge %s profile %s (budget %ds)", browser.key, name, args.timeout)
    while True:
        if not path.exists():
            _emit(args, {"purged": name, "path": str(path)}, f"purged {name}")
            return 0
        try:
            remove_profile(
                Profile(name=name, browser_key=browser.key, path=path, meta={}),
                missing_ok=True,
                retries=1,
            )
            _emit(args, {"purged": name, "path": str(path)}, f"purged {name}")
            return 0
        except ProfileError as exc:
            if time.monotonic() >= deadline:
                _log.error(
                    "could not purge %s within %ds: %s",
                    name,
                    args.timeout,
                    exc,
                )
                hint = f"try again once the browser is fully closed: eroica remove -b {browser.key} -p {name}"
                if not getattr(args, "json", False):
                    print(hint)
                return 1
            _log.debug("profile %s still busy (%s); retrying in %ss", name, exc, args.poll)
            time.sleep(args.poll)


# --------------------------------------------------------------------------- #
# Parser
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="eroica",
        description="EROICA — privacy hardening for any browser (named after Beethoven's Third).",
        epilog="Docs: https://github.com/BeethovenDev/eroica",
    )
    parser.add_argument("--version", action="version", version=f"eroica {__version__}")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    parser.add_argument("-v", "--verbose", action="count", default=0, help="increase log verbosity")
    parser.add_argument("-q", "--quiet", action="store_true", help="only log errors")

    sub = parser.add_subparsers(dest="command", required=True)

    p_version = sub.add_parser("version", help="show version")
    p_version.set_defaults(func=cmd_version)

    p_doctor = sub.add_parser("doctor", help="inspect the environment and installed browsers")
    p_doctor.add_argument("-b", "--browser", help="limit detection to one browser")
    p_doctor.set_defaults(func=cmd_doctor)

    p_sym = sub.add_parser("symphonies", help="list the hardening movements")
    p_sym.add_argument("-t", "--tier", choices=[t.name.lower() for t in Tier],
                       help="show settings that apply at this tier")
    p_sym.set_defaults(func=cmd_symphonies)

    p_config = sub.add_parser("config", help="show or update configuration")
    p_config.set_defaults(func=cmd_config)
    config_sub = p_config.add_subparsers(dest="config_command")
    config_sub.add_parser("show", help="show current configuration")
    p_set = config_sub.add_parser("set", help="update configuration")
    p_set.add_argument("-t", "--tier", choices=[t.name.lower() for t in Tier])
    p_set.add_argument("--doh", choices=sorted(DOH_PROVIDERS))
    p_set.add_argument("--ua-mode", choices=["consistent", "off"])
    backup_group = p_set.add_mutually_exclusive_group()
    backup_group.add_argument("--backup", dest="backup", action="store_true", default=None)
    backup_group.add_argument("--no-backup", dest="backup", action="store_false")

    p_new = sub.add_parser("new", help="create and harden a new isolated profile")
    p_new.add_argument("-b", "--browser")
    p_new.add_argument("-p", "--profile", required=True, help="profile name")
    p_new.add_argument("-t", "--tier", choices=[t.name.lower() for t in Tier])
    p_new.add_argument("--ua", help="pin an explicit User-Agent")
    p_new.add_argument("--no-harden", action="store_true", help="create without hardening")
    p_new.add_argument("--dry-run", action="store_true")
    p_new.set_defaults(func=cmd_new)

    p_profiles = sub.add_parser("profiles", aliases=["list"], help="list EROICA profiles")
    p_profiles.add_argument("-b", "--browser")
    p_profiles.set_defaults(func=cmd_profiles)

    p_remove = sub.add_parser("remove", aliases=["rm"], help="delete a profile")
    p_remove.add_argument("-b", "--browser")
    p_remove.add_argument("-p", "--profile", required=True)
    p_remove.add_argument("-y", "--yes", action="store_true", help="skip confirmation")
    p_remove.set_defaults(func=cmd_remove)

    p_harden = sub.add_parser("harden", help="(re)apply hardening to a profile")
    p_harden.add_argument("-b", "--browser")
    p_harden.add_argument("-p", "--profile", required=True)
    p_harden.add_argument("-t", "--tier", choices=[t.name.lower() for t in Tier])
    p_harden.add_argument("--ua")
    p_harden.add_argument("--dry-run", action="store_true")
    p_harden.add_argument("--no-backup", action="store_true")
    p_harden.set_defaults(func=cmd_harden)

    p_audit = sub.add_parser("audit", help="check a profile for drift")
    p_audit.add_argument("-b", "--browser")
    p_audit.add_argument("-p", "--profile", required=True)
    p_audit.add_argument("-t", "--tier", choices=[t.name.lower() for t in Tier])
    p_audit.set_defaults(func=cmd_audit)

    p_launch = sub.add_parser("launch", help="launch a hardened browser session")
    p_launch.add_argument("-b", "--browser")
    p_launch.add_argument("-p", "--profile", required=True)
    p_launch.add_argument("-t", "--tier", choices=[t.name.lower() for t in Tier])
    p_launch.add_argument("--private", action="store_true", help="extra private/incognito window")
    p_launch.add_argument("--dry-run", action="store_true", help="print the command only")
    p_launch.add_argument("urls", nargs=argparse.REMAINDER, help="URLs to open")
    p_launch.set_defaults(func=cmd_launch)

    p_stealth = sub.add_parser(
        "stealth",
        aliases=["anon"],
        help="launch a throwaway, fully hardened, private session (self-destructing)",
    )
    p_stealth.add_argument("-b", "--browser")
    p_stealth.add_argument(
        "-t", "--tier", choices=[t.name.lower() for t in Tier],
        default=None,
        help="hardening tier (default: paranoid)",
    )
    p_stealth.add_argument("--ua", help="pin an explicit User-Agent for this session")
    p_stealth.add_argument("--keep", action="store_true",
                           help="keep the throwaway profile after closing")
    p_stealth.add_argument("--dry-run", action="store_true",
                           help="print the command without launching")
    p_stealth.add_argument("urls", nargs=argparse.REMAINDER, help="URLs to open")
    p_stealth.set_defaults(func=cmd_stealth)

    p_purge = sub.add_parser(
        "purge",
        help="wait until a profile's files are released, then delete it",
    )
    p_purge.add_argument("-b", "--browser")
    p_purge.add_argument("-p", "--profile", required=True)
    p_purge.add_argument("--timeout", type=int, default=300,
                         help="seconds to keep trying before giving up (default: 300)")
    p_purge.add_argument("--poll", type=float, default=2.0,
                         help="seconds between retries (default: 2)")
    p_purge.set_defaults(func=cmd_purge)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point. Returns a process exit code."""
    _configure_console_encoding()
    parser = build_parser()
    args = parser.parse_args(argv)

    log.configure(verbosity=args.verbose, json_logs=False)
    if args.quiet:
        import logging

        logging.getLogger("eroica").setLevel(logging.ERROR)

    try:
        return int(args.func(args))
    except EroicaError as exc:
        _log.error("%s", exc)
        return 1
    except KeyboardInterrupt:  # pragma: no cover - interactive
        print("\naborted", file=sys.stderr)
        return 130


__all__ = ["build_parser", "main"]
