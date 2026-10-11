"""Isolated profile management.

Every hardened session lives in its own directory under EROICA's data home, so
that OSINT work never touches your everyday browser profile. A small sidecar
(``.eroica.json``) records the pinned tier and User-Agent for reproducibility.
"""

from __future__ import annotations

import json
import re
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from eroica import __version__, log
from eroica.config import Tier
from eroica.errors import ProfileError, ProfileNotFound
from eroica.paths import data_home

_log = log.get_logger("profiles")

#: Deletion retry budget. On Windows a browser that just closed can still have
#: a lingering child process holding profile files; chasing away those transient
#: locks is what makes ``stealth``'s self-destruct reliable.
_RETRY_ATTEMPTS = 8
_RETRY_BASE_DELAY = 0.25  # seconds; doubles per attempt, capped below.
_RETRY_MAX_DELAY = 1.0

__all__ = [
    "META_FILENAME",
    "Profile",
    "create_profile",
    "list_profiles",
    "profiles_root",
    "remove_profile",
    "resolve_profile",
    "validate_name",
]

META_FILENAME = ".eroica.json"
_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


def validate_name(name: str) -> str:
    """Validate and normalise a profile name.

    Names must be filesystem-safe and cannot escape the profiles root.
    """
    candidate = name.strip()
    if not _NAME_RE.match(candidate):
        raise ProfileError(
            "invalid profile name: use 1–64 characters of letters, digits, '.', '_' or '-'"
        )
    if candidate in {".", ".."}:
        raise ProfileError("invalid profile name")
    return candidate


def profiles_root(browser_key: str) -> Path:
    """Return the directory that holds profiles for a browser."""
    return data_home() / "profiles" / browser_key


@dataclass
class Profile:
    """A materialised, isolated browser profile."""

    name: str
    browser_key: str
    path: Path
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def meta_path(self) -> Path:
        return self.path / META_FILENAME

    @property
    def tier(self) -> Tier | None:
        raw = self.meta.get("tier")
        return Tier.coerce(raw) if raw else None

    @property
    def user_agent(self) -> str | None:
        value = self.meta.get("user_agent")
        return str(value) if value else None

    def save(self) -> None:
        """Persist the sidecar metadata atomically-ish."""
        self.meta.update(
            {
                "name": self.name,
                "browser": self.browser_key,
                "eroica_version": __version__,
            }
        )
        self.meta.setdefault("created", time.strftime("%Y-%m-%dT%H:%M:%S"))
        try:
            self.path.mkdir(parents=True, exist_ok=True)
            self.meta_path.write_text(
                json.dumps(self.meta, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        except OSError as exc:
            raise ProfileError(f"could not write metadata for {self.name}: {exc}") from exc


def create_profile(
    browser_key: str,
    name: str,
    *,
    tier: Tier,
    user_agent: str | None = None,
    exist_ok: bool = False,
) -> Profile:
    """Create an on-disk profile directory and sidecar.

    Args:
        exist_ok: Return the existing profile instead of raising.
    """
    profile_name = validate_name(name)
    path = profiles_root(browser_key) / profile_name
    if path.exists():
        if exist_ok:
            return load_profile(browser_key, profile_name)
        raise ProfileError(f"profile {profile_name!r} already exists for {browser_key}")

    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise ProfileError(f"could not create profile at {path}: {exc}") from exc

    profile = Profile(
        name=profile_name,
        browser_key=browser_key,
        path=path,
        meta={"created": time.strftime("%Y-%m-%dT%H:%M:%S"), "tier": tier.name.lower()},
    )
    if user_agent:
        profile.meta["user_agent"] = user_agent
    profile.save()
    _log.debug("created profile %s at %s", profile_name, path)
    return profile


def load_profile(browser_key: str, name: str) -> Profile:
    """Load an existing profile, raising :class:`ProfileNotFound` if absent."""
    profile_name = validate_name(name)
    path = profiles_root(browser_key) / profile_name
    if not path.is_dir():
        raise ProfileNotFound(f"no profile {profile_name!r} for {browser_key}")
    meta: dict[str, Any] = {}
    meta_path = path / META_FILENAME
    if meta_path.is_file():
        try:
            loaded = json.loads(meta_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                meta = loaded
        except (OSError, json.JSONDecodeError) as exc:
            _log.warning("ignoring unreadable metadata at %s: %s", meta_path, exc)
    return Profile(name=profile_name, browser_key=browser_key, path=path, meta=meta)


def resolve_profile(browser_key: str, name: str) -> Profile:
    """Alias for :func:`load_profile`, kept for readability at call sites."""
    return load_profile(browser_key, name)


def list_profiles(browser_key: str | None = None) -> list[Profile]:
    """List profiles, optionally filtered to one browser, sorted by browser then name."""
    if browser_key:
        keys = [browser_key]
    else:
        root = data_home() / "profiles"
        keys = sorted(child.name for child in root.iterdir() if child.is_dir()) if root.is_dir() else []

    found: list[Profile] = []
    for key in keys:
        root = profiles_root(key)
        if not root.is_dir():
            continue
        for child in sorted(root.iterdir()):
            if child.is_dir():
                try:
                    found.append(load_profile(key, child.name))
                except ProfileError:
                    continue
    return found


def remove_profile(
    profile: Profile,
    *,
    missing_ok: bool = False,
    retries: int = _RETRY_ATTEMPTS,
) -> None:
    """Delete a profile directory and everything in it.

    Modern Windows browsers keep a couple of child processes alive for a few
    moments after the last window closes; those hold file handles and make a
    single ``rmtree`` fail with ``WinError 32``. Deletion therefore retries with
    an exponential backoff until the locks clear (or ``retries`` is exhausted).
    """
    if not profile.path.exists():
        if missing_ok:
            return
        raise ProfileNotFound(f"profile {profile.name!r} does not exist")

    last_error: OSError | None = None
    for attempt in range(retries + 1):
        try:
            shutil.rmtree(profile.path)
            _log.debug("removed profile %s", profile.name)
            return
        except OSError as exc:
            last_error = exc
            if not profile.path.exists():
                # Removed by something else in the meantime — good enough.
                _log.debug("profile %s vanished during removal", profile.name)
                return
            if attempt >= retries:
                break
            delay = min(_RETRY_BASE_DELAY * (2**attempt), _RETRY_MAX_DELAY)
            _log.debug(  # transient lock; retrying
                "profile %s busy (%s); retry %d/%d",
                profile.name,
                exc.strerror or exc,
                attempt + 1,
                retries,
            )
            time.sleep(delay)

    raise ProfileError(
        f"could not remove {profile.path}: {last_error} "
        f"(still held by another process after {retries} retries)"
    )
