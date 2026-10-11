"""Turn a :class:`~eroica.profiles.Profile` into a hardened profile.

This is the conductor: it asks each movement for the settings that apply at the
chosen tier, folds in the DoH endpoint and pinned User-Agent from configuration,
and then writes the result using the right strategy for the browser family.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from eroica import log, ua
from eroica.browsers import Browser, BrowserFamily
from eroica.config import Config, Tier
from eroica.flags import build_args
from eroica.net import parse_proxy, proxy_chromium_flags, proxy_firefox_prefs
from eroica.profiles import Profile
from eroica.symphonies import collect_flags, collect_prefs
from eroica.symphonies.base import ChromiumFlag, FirefoxPref
from eroica.userjs import write_user_js

_log = log.get_logger("hardening")

__all__ = [
    "HardeningPlan",
    "HardenResult",
    "build_plan",
    "harden",
    "load_materialized_args",
    "preview_firefox",
]

#: Prefix marking the DoH prefs that are dropped when the DoH provider is "system".
_TRR_PREFIX = "network.trr."


@dataclass
class HardeningPlan:
    """The fully-resolved settings for one profile at one tier."""

    tier: Tier
    prefs: list[FirefoxPref] = field(default_factory=list)
    flags: list[ChromiumFlag] = field(default_factory=list)
    user_agent: str | None = None
    doh_uri: str | None = None
    proxy: str | None = None


@dataclass
class HardenResult:
    """Outcome of applying a plan to a profile."""

    browser: Browser
    profile: Profile
    tier: Tier
    prefs_count: int = 0
    flags_count: int = 0
    user_js: Path | None = None
    backup: Path | None = None
    flags_file: Path | None = None
    user_agent: str | None = None
    doh_uri: str | None = None
    proxy: str | None = None
    dry_run: bool = False
    preview: str | None = None

    def summary(self) -> str:
        """A one-line, human-readable summary."""
        if self.browser.family is BrowserFamily.MOZILLA:
            detail = f"{self.prefs_count} prefs"
        else:
            detail = f"{self.flags_count} launch flags"
        target = self.user_js if self.user_js else self.flags_file
        suffix = " (dry run)" if self.dry_run else ""
        return f"{self.browser.name}: {detail} -> {target}{suffix}"


def _resolve_user_agent(
    config: Config, profile: Profile, *, requested: str | None
) -> str | None:
    if requested is not None:
        return ua.validate(requested)
    if config.ua_mode == "off":
        return None
    if profile.user_agent:
        return profile.user_agent
    return ua.pick(f"{profile.browser_key}:{profile.name}")


def build_plan(
    browser: Browser,
    profile: Profile,
    tier: Tier,
    config: Config,
    *,
    user_agent: str | None = None,
) -> HardeningPlan:
    """Resolve every setting for ``profile`` at ``tier``."""
    plan = HardeningPlan(tier=tier)
    plan.user_agent = _resolve_user_agent(config, profile, requested=user_agent)
    _log.debug("building plan for %s at tier %s", browser.key, tier.name.lower())

    prefs = collect_prefs(tier)
    flags = collect_flags(tier)

    doh_uri = config.doh_uri
    if doh_uri is None:
        # The user asked for the system resolver: strip every DoH directive so
        # we neither force nor advertise an encrypted resolver.
        prefs = [p for p in prefs if not p.key.startswith(_TRR_PREFIX)]
        flags = [f for f in flags if not f.flag.startswith("--dns-over-https-mode")]
        _log.debug("DoH provider is 'system'; removed %s directives", _TRR_PREFIX)
    else:
        plan.doh_uri = doh_uri
        prefs.append(FirefoxPref("network.trr.uri", doh_uri, Tier.STANDARD,
                                 f"Encrypted DNS via {config.doh_provider}."))
        prefs.append(FirefoxPref("network.trr.custom_uri", doh_uri, Tier.STANDARD))

    # Network layer: route everything through the configured SOCKS proxy. DNS is
    # forced inside the tunnel and DoH is switched off — a proxy is pointless if
    # hostnames still leak straight to the resolver.
    proxy = parse_proxy(config.proxy)
    if proxy is not None:
        plan.proxy = config.proxy
        if browser.family is BrowserFamily.MOZILLA:
            prefs = [p for p in prefs if not p.key.startswith(_TRR_PREFIX)]
            prefs.extend(proxy_firefox_prefs(proxy))
        else:
            flags = [f for f in flags if not f.flag.startswith("--dns-over-https-mode")]
            flags.extend(proxy_chromium_flags(proxy))
        plan.doh_uri = None
        _log.debug("proxy %s folded into plan for %s", proxy.as_url(), browser.key)

    # A user.js file is applied top-to-bottom — the *last* value wins. Collapse
    # repeated directives (e.g. Fate's paranoid-mode remote-DNS pref) to their
    # final value so the emitted profile stays clean and deterministic.
    final_prefs: dict[str, FirefoxPref] = {}
    for pref in prefs:
        final_prefs[pref.key] = pref
    final_flags: dict[str, ChromiumFlag] = {}
    for flag in flags:
        final_flags[flag.flag] = flag
    plan.prefs = list(final_prefs.values())
    plan.flags = list(final_flags.values())
    return plan


def preview_firefox(
    browser: Browser,
    profile: Profile,
    tier: Tier,
    config: Config,
    *,
    user_agent: str | None = None,
) -> str:
    """Render the ``user.js`` that :func:`harden` would write, without writing it."""
    from eroica.userjs import render_document

    plan = build_plan(browser, profile, tier, config, user_agent=user_agent)
    return render_document(_with_ua_pref(plan))


def _with_ua_pref(plan: HardeningPlan) -> list[FirefoxPref]:
    prefs = list(plan.prefs)
    if plan.user_agent:
        prefs.append(
            FirefoxPref(
                "general.useragent.override",
                plan.user_agent,
                Tier.STANDARD,
                "Pinned User-Agent so the profile stays internally consistent.",
            )
        )
    return prefs


def _harden_firefox(
    browser: Browser,
    profile: Profile,
    plan: HardeningPlan,
    *,
    dry_run: bool,
    backup: bool,
) -> HardenResult:
    user_js = profile.path / "user.js"
    content, backup_path = write_user_js(
        user_js, _with_ua_pref(plan), backup=backup, dry_run=dry_run
    )
    return HardenResult(
        browser=browser,
        profile=profile,
        tier=plan.tier,
        prefs_count=len(plan.prefs) + (1 if plan.user_agent else 0),
        user_js=user_js,
        backup=backup_path,
        user_agent=plan.user_agent,
        doh_uri=plan.doh_uri,
        proxy=plan.proxy,
        dry_run=dry_run,
        preview=content if dry_run else None,
    )


def _harden_chromium(
    browser: Browser,
    profile: Profile,
    plan: HardeningPlan,
    *,
    dry_run: bool,
) -> HardenResult:
    flags_file = profile.path / ".eroica" / "flags.json"
    payload = {
        "browser": browser.key,
        "tier": plan.tier.name.lower(),
        "user_agent": plan.user_agent,
        "doh_uri": plan.doh_uri,
        "args": build_args(
            profile.path,
            plan.flags,
            user_agent=plan.user_agent,
            doh_uri=plan.doh_uri,
        ),
    }
    if not dry_run:
        flags_file.parent.mkdir(parents=True, exist_ok=True)
        flags_file.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return HardenResult(
        browser=browser,
        profile=profile,
        tier=plan.tier,
        flags_count=len(plan.flags),
        flags_file=flags_file,
        user_agent=plan.user_agent,
        doh_uri=plan.doh_uri,
        proxy=plan.proxy,
        dry_run=dry_run,
        preview=json.dumps(payload, indent=2) if dry_run else None,
    )


def harden(
    browser: Browser,
    profile: Profile,
    tier: Tier,
    config: Config,
    *,
    user_agent: str | None = None,
    dry_run: bool = False,
    backup: bool | None = None,
) -> HardenResult:
    """Apply hardening to ``profile`` and persist the pinned settings.

    Args:
        browser: The browser the profile belongs to.
        profile: The profile to harden (already created on disk).
        tier: How aggressive to be.
        config: Global configuration (DoH provider, UA mode).
        user_agent: Override the pinned User-Agent for this run.
        dry_run: Compute everything but write nothing.
        backup: Back up an existing ``user.js`` first. Defaults to the config value.
    """
    plan = build_plan(browser, profile, tier, config, user_agent=user_agent)
    if backup is None:
        backup = config.backup_user_js

    if browser.family is BrowserFamily.MOZILLA:
        result = _harden_firefox(browser, profile, plan, dry_run=dry_run, backup=backup)
    else:
        result = _harden_chromium(browser, profile, plan, dry_run=dry_run)

    if not dry_run:
        profile.meta["tier"] = tier.name.lower()
        if plan.user_agent:
            profile.meta["user_agent"] = plan.user_agent
        else:
            profile.meta.pop("user_agent", None)
        if plan.doh_uri:
            profile.meta["doh_uri"] = plan.doh_uri
        else:
            profile.meta.pop("doh_uri", None)
        if plan.proxy:
            profile.meta["proxy"] = plan.proxy
        else:
            profile.meta.pop("proxy", None)
        profile.save()
        _log.info("hardened %s profile %s at tier %s", browser.key, profile.name, tier.name.lower())

    return result


def load_materialized_args(profile: Profile) -> list[str] | None:
    """The Chromium argument vector persisted at harden time.

    ``flags.json`` is the single source of truth for how a hardened profile is
    launched (``launch`` and ``stealth`` use it, exactly like ``audit`` verifies
    it). Returns ``None`` when the profile was never hardened, in which case the
    caller should fall back to building a vector on the fly.
    """
    flags_file = profile.path / ".eroica" / "flags.json"
    if not flags_file.is_file():
        return None
    try:
        payload = json.loads(flags_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    args = payload.get("args")
    return list(args) if isinstance(args, list) and args else None
