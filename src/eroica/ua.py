"""User-Agent selection.

Counter-intuitively, the safest User-Agent is the *boring and stable* one. A UA
that changes between requests is itself a fingerprint, and an exotic UA stands
out. EROICA therefore pins exactly one mainstream UA per profile, deterministically
derived from the profile name unless you supply your own.

The pool below should be refreshed periodically; browsers move fast.
"""

from __future__ import annotations

import hashlib

from eroica.errors import ConfigError

__all__ = ["UA_POOL", "describe_pool", "platform_key", "pick", "validate"]

#: Curated, mainstream User-Agents. Keep the spread plausible: one recent
#: version per engine, plus macOS/Linux variants so the OS is not a giveaway.
UA_POOL: dict[str, tuple[str, ...]] = {
    "windows": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    ),
    "macos": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:128.0) Gecko/20100101 Firefox/128.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    ),
    "linux": (
        "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    ),
}


def platform_key() -> str:
    """Map the running platform onto a UA pool key."""
    import sys

    if sys.platform.startswith("win"):
        return "windows"
    if sys.platform == "darwin":
        return "macos"
    return "linux"


def pick(seed: str, platform: str | None = None) -> str:
    """Deterministically choose a UA for ``seed`` (usually the profile name).

    The same seed always yields the same UA, which keeps a profile internally
    consistent across sessions.
    """
    key = platform or platform_key()
    pool = UA_POOL.get(key)
    if not pool:
        raise ConfigError(f"no User-Agent pool for platform {key!r}")
    digest = hashlib.sha256(seed.encode("utf-8")).digest()
    return pool[digest[0] % len(pool)]


def validate(user_agent: str) -> str:
    """Reject obviously broken custom User-Agents early."""
    candidate = user_agent.strip()
    if not candidate or "\n" in candidate or len(candidate) > 512:
        raise ConfigError("User-Agent must be a single non-empty line under 512 characters")
    if not candidate.startswith("Mozilla/"):
        raise ConfigError("User-Agent should start with 'Mozilla/' to blend in")
    return candidate


def describe_pool() -> list[str]:
    """Return every UA in the pool, for ``--json`` output and audits."""
    return [ua for pool in UA_POOL.values() for ua in pool]
