"""Audit a hardened profile and report drift.

For Firefox, "hardened" means the marked block exists in ``user.js`` and still
contains every pref the current tier expects. For Chromium, it means the stored
flag set is present and current. The audit is intentionally read-only.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from eroica.browsers import Browser, BrowserFamily
from eroica.config import Config, Tier
from eroica.hardening import build_plan
from eroica.profiles import Profile
from eroica.userjs import MARKER_BEGIN, MARKER_END, read_user_js

__all__ = ["AuditCheck", "AuditReport", "audit_profile"]


@dataclass(frozen=True)
class AuditCheck:
    """A single pass/fail observation about a profile."""

    label: str
    ok: bool
    detail: str = ""


@dataclass
class AuditReport:
    """The full audit result for one profile."""

    browser: Browser
    profile: Profile
    tier: Tier
    checks: list[AuditCheck]

    @property
    def healthy(self) -> bool:
        return all(check.ok for check in self.checks)

    def to_dict(self) -> dict[str, object]:
        return {
            "browser": self.browser.key,
            "profile": self.profile.name,
            "path": str(self.profile.path),
            "tier": self.tier.name.lower(),
            "healthy": self.healthy,
            "checks": [
                {"label": c.label, "ok": c.ok, "detail": c.detail} for c in self.checks
            ],
        }


def _audit_mozilla(profile: Profile, plan: object) -> list[AuditCheck]:
    checks: list[AuditCheck] = []
    user_js = profile.path / "user.js"
    content = read_user_js(user_js)
    checks.append(AuditCheck("user.js present", content is not None, str(user_js)))
    if content is None:
        return checks

    checks.append(
        AuditCheck("EROICA block present", MARKER_BEGIN in content and MARKER_END in content)
    )

    expected = _expected_pref_keys(plan)
    missing = sorted(key for key in expected if f'"{key}"' not in content)
    detail = ""
    if missing:
        shown = ", ".join(missing[:5]) + ("…" if len(missing) > 5 else "")
        detail = f"missing: {shown}"
    checks.append(AuditCheck("all expected prefs applied", not missing, detail))
    return checks


def _audit_chromium(profile: Profile, tier: Tier) -> list[AuditCheck]:
    checks: list[AuditCheck] = []
    flags_file = profile.path / ".eroica" / "flags.json"
    checks.append(AuditCheck("flags file present", flags_file.is_file(), str(flags_file)))
    if not flags_file.is_file():
        return checks

    try:
        payload = json.loads(flags_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        checks.append(AuditCheck("flags file readable", False, str(exc)))
        return checks

    args = payload.get("args", [])
    checks.append(AuditCheck("flags recorded", bool(args), f"{len(args)} args"))
    recorded_tier = str(payload.get("tier", "")).lower()
    checks.append(
        AuditCheck(
            "tier up to date",
            recorded_tier == tier.name.lower(),
            f"recorded={recorded_tier or 'none'} expected={tier.name.lower()}",
        )
    )
    return checks


def _expected_pref_keys(plan: object) -> set[str]:
    """Extract the set of pref keys from a resolved :class:`HardeningPlan`."""
    prefs = getattr(plan, "prefs", [])
    user_agent = getattr(plan, "user_agent", None)
    keys = {pref.key for pref in prefs}
    if user_agent:
        keys.add("general.useragent.override")
    return keys


def audit_profile(
    browser: Browser, profile: Profile, tier: Tier, config: Config
) -> AuditReport:
    """Audit ``profile`` against the plan implied by ``tier`` and ``config``."""
    plan = build_plan(browser, profile, tier, config)
    checks: list[AuditCheck] = [
        AuditCheck("profile directory exists", profile.path.is_dir(), str(profile.path))
    ]

    if browser.family is BrowserFamily.MOZILLA:
        checks.extend(_audit_mozilla(profile, plan))
    else:
        checks.extend(_audit_chromium(profile, tier))

    checks.append(
        AuditCheck(
            "tier recorded in metadata",
            profile.tier is not None and profile.tier == tier,
            f"recorded={profile.tier.name.lower() if profile.tier else 'none'}",
        )
    )
    checks.append(
        AuditCheck(
            "User-Agent pinned",
            plan.user_agent is None or bool(profile.meta.get("user_agent")),
            plan.user_agent or "disabled",
        )
    )
    return AuditReport(browser=browser, profile=profile, tier=tier, checks=checks)
