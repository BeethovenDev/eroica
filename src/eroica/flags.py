"""Chromium-family command-line flag construction.

Chromium exposes most privacy knobs at launch time rather than through a
``user.js``-style file. EROICA therefore builds a deterministic argument vector
from the collected :class:`~eroica.symphonies.base.ChromiumFlag` objects and any
per-profile pins (User-Agent, DoH template).
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from pathlib import Path

from eroica.symphonies.base import ChromiumFlag

__all__ = ["build_args"]


def build_args(
    profile_dir: Path,
    flags: Iterable[ChromiumFlag],
    *,
    user_agent: str | None = None,
    doh_uri: str | None = None,
    private: bool = False,
    extra: Sequence[str] = (),
) -> list[str]:
    """Build the Chromium argument vector for a hardened launch.

    Args:
        profile_dir: Isolated ``--user-data-dir`` for this profile.
        flags: Flags contributed by the movements.
        user_agent: Optional pinned User-Agent (kept stable across sessions).
        doh_uri: Optional DNS-over-HTTPS template URL.
        private: Add ``--incognito`` (useful for one-off OSINT lookups).
        extra: Raw arguments appended last (they win).
    """
    args: list[str] = [f"--user-data-dir={profile_dir}"]
    args.extend(flag.flag for flag in flags)

    if user_agent:
        args.append(f"--user-agent={user_agent}")
    if doh_uri:
        args.append(f"--dns-over-https-templates={doh_uri}")
    if private:
        args.append("--incognito")
    args.extend(extra)
    return args
