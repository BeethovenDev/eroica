"""Reading, rendering and writing Firefox ``user.js`` files.

EROICA never rewrites a ``user.js`` it did not create without first taking a
backup, and it confines its own output to a clearly marked block so your manual
edits above and below the block are preserved across re-runs.
"""

from __future__ import annotations

import shutil
import time
from collections.abc import Iterable
from pathlib import Path

from eroica import log
from eroica.errors import ProfileError
from eroica.symphonies.base import FirefoxPref

_log = log.get_logger("userjs")

__all__ = [
    "MARKER_BEGIN",
    "MARKER_END",
    "format_pref",
    "merge",
    "render_block",
    "render_document",
    "read_user_js",
    "write_user_js",
]

MARKER_BEGIN = "// >>> EROICA BEGIN — generated, do not edit inside this block >>>"
MARKER_END = "// <<< EROICA END <<<"


def _format_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    raise ProfileError(f"unsupported pref value type: {type(value).__name__}")


def format_pref(pref: FirefoxPref) -> str:
    """Render a single pref as a ``user_pref`` line, with an optional note."""
    line = f'user_pref("{pref.key}", {_format_value(pref.value)});'
    return f"{line}  // {pref.note}" if pref.note else line


def render_block(prefs: Iterable[FirefoxPref]) -> str:
    """Render the marked, machine-managed block for the given prefs."""
    ordered = sorted(prefs, key=lambda p: p.key)
    body = "\n".join(format_pref(p) for p in ordered)
    return f"{MARKER_BEGIN}\n{body}\n{MARKER_END}"


def render_document(prefs: Iterable[FirefoxPref]) -> str:
    """Render a standalone ``user.js`` document."""
    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    header = (
        "// EROICA — browser privacy hardening\n"
        "// https://github.com/BeethovenDev/eroica\n"
        f"// Generated: {stamp}\n"
        "// Prefs outside the marked block are preserved on the next run."
    )
    return f"{header}\n\n{render_block(prefs)}\n"


def read_user_js(path: Path) -> str | None:
    """Return the current ``user.js`` contents, or ``None`` if absent."""
    if not path.is_file():
        return None
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ProfileError(f"could not read {path}: {exc}") from exc


def merge(existing: str | None, block: str) -> str:
    """Splice ``block`` into ``existing``, replacing any previous EROICA block.

    Everything the user wrote before/after EROICA's markers is kept verbatim.
    """
    if existing is None or not existing.strip():
        return f"{block}\n"

    start = existing.find(MARKER_BEGIN)
    end = existing.find(MARKER_END)
    if start != -1 and end != -1 and end > start:
        end += len(MARKER_END)
        before = existing[:start].rstrip("\n")
        after = existing[end:].lstrip("\n")
        pieces = [p for p in (before, block, after) if p]
        return "\n\n".join(pieces) + "\n"
    # No prior block: append, keeping existing content untouched.
    return existing.rstrip("\n") + "\n\n" + block + "\n"


def write_user_js(
    path: Path,
    prefs: Iterable[FirefoxPref],
    *,
    backup: bool = True,
    dry_run: bool = False,
) -> tuple[str, Path | None]:
    """Write the merged ``user.js``.

    Returns:
        A tuple of ``(content, backup_path)`` where ``backup_path`` is ``None``
        when no backup was needed or ``dry_run`` was set.
    """
    block = render_block(prefs)
    existing = read_user_js(path)
    content = merge(existing, block)

    if dry_run:
        return content, None

    backup_path: Path | None = None
    if backup and existing is not None:
        backup_path = path.with_suffix(path.suffix + f".bak-{int(time.time())}")
        try:
            shutil.copy2(path, backup_path)
        except OSError as exc:  # pragma: no cover - rare FS failure
            raise ProfileError(f"could not back up {path}: {exc}") from exc
        _log.debug("backed up %s -> %s", path, backup_path)

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    except OSError as exc:
        raise ProfileError(f"could not write {path}: {exc}") from exc
    return content, backup_path
