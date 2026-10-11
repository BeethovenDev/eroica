"""Tests for the ``user.js`` render/merge/backup engine."""

from __future__ import annotations

from pathlib import Path

import pytest

from eroica.config import Tier
from eroica.symphonies.base import FirefoxPref
from eroica.userjs import (
    MARKER_BEGIN,
    MARKER_END,
    format_pref,
    merge,
    render_block,
    write_user_js,
)


def test_format_pref_value_types() -> None:
    assert format_pref(FirefoxPref("a.b", True)) == 'user_pref("a.b", true);'
    assert format_pref(FirefoxPref("a.b", False)) == 'user_pref("a.b", false);'
    assert format_pref(FirefoxPref("a.b", 5)) == 'user_pref("a.b", 5);'
    assert format_pref(FirefoxPref("a.b", "x")) == 'user_pref("a.b", "x");'


def test_format_pref_escapes_strings() -> None:
    rendered = format_pref(FirefoxPref("a.b", 'he said "hi"\\'))
    assert rendered == 'user_pref("a.b", "he said \\"hi\\"\\\\");'


def test_format_pref_includes_note() -> None:
    rendered = format_pref(FirefoxPref("a.b", 1, note="why"))
    assert rendered.endswith("// why")


def test_render_block_is_sorted_and_marked() -> None:
    block = render_block([FirefoxPref("z", 1), FirefoxPref("a", 2)])
    lines = block.splitlines()
    assert lines[0] == MARKER_BEGIN
    assert lines[-1] == MARKER_END
    assert '"a"' in lines[1]
    assert '"z"' in lines[2]


def test_merge_appends_when_empty() -> None:
    block = render_block([FirefoxPref("a", 1)])
    assert merge(None, block).count(MARKER_BEGIN) == 1
    assert merge("   ", block).count(MARKER_BEGIN) == 1


def test_merge_replaces_prior_block_and_keeps_manual_prefs() -> None:
    block_one = render_block([FirefoxPref("a", 1)])
    original = f'user_pref("manual.before", true);\n\n{block_one}\n\nuser_pref("manual.after", true);\n'
    block_two = render_block([FirefoxPref("a", 2)])

    merged = merge(original, block_two)

    assert merged.count(MARKER_BEGIN) == 1
    assert '"manual.before"' in merged
    assert '"manual.after"' in merged
    assert 'user_pref("a", 2);' in merged
    assert 'user_pref("a", 1);' not in merged


def test_merge_is_idempotent() -> None:
    block = render_block([FirefoxPref("a", 1)])
    once = merge(None, block)
    twice = merge(once, block)
    assert twice.count(MARKER_BEGIN) == 1
    assert 'user_pref("a", 1);' in twice


def test_write_user_js_creates_and_backs_up(tmp_path: Path) -> None:
    path = tmp_path / "user.js"
    content, backup = write_user_js(path, [FirefoxPref("a", 1)])
    assert backup is None
    assert path.read_text(encoding="utf-8") == content

    _, backup = write_user_js(path, [FirefoxPref("a", 2)])
    assert backup is not None and backup.exists()


def test_write_user_js_dry_run_does_not_write(tmp_path: Path) -> None:
    path = tmp_path / "user.js"
    content, backup = write_user_js(path, [FirefoxPref("a", 1)], dry_run=True)
    assert not path.exists()
    assert backup is None
    assert MARKER_BEGIN in content


@pytest.mark.parametrize("tier", list(Tier))
def test_write_accepts_every_tier(tier: Tier) -> None:
    pref = FirefoxPref("a", 1, tier=tier)
    assert '"a"' in render_block([pref])
