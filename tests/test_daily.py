"""Tests for linafish.daily — per-day fish builds.

Synthetic tmp dirs with date-stamped files exercise gather + build +
idempotent skip + list. End-to-end build verifies crystal-count > 0.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from linafish.daily import (
    DailyBuildResult,
    _daily_dir,
    _gather_seed_parts,
    _seed_digest,
    _seed_text,
    build_daily_fish,
    list_daily_fish,
    today_iso,
)


# ----------------------------- helpers -----------------------------

def test_today_iso_format():
    iso = today_iso()
    assert len(iso) == 10
    assert iso[4] == "-" and iso[7] == "-"


# ----------------------------- _gather_seed_parts -----------------------------

def test_gather_empty_when_no_match(tmp_path: Path):
    parts = _gather_seed_parts("2026-05-18", [tmp_path], ["*{date}*.md"])
    assert parts == []


def test_gather_finds_matching_files(tmp_path: Path):
    (tmp_path / "session_2026-05-18_morning.md").write_text("morning content")
    (tmp_path / "notes_2026-05-18_evening.md").write_text("evening content")
    (tmp_path / "felt_2026-05-17_other-day.md").write_text("wrong day")
    parts = _gather_seed_parts("2026-05-18", [tmp_path], ["*{date}*.md"])
    titles = sorted(p[0] for p in parts)
    assert titles == ["notes_2026-05-18_evening.md", "session_2026-05-18_morning.md"]


def test_gather_skips_missing_dir(tmp_path: Path):
    # Non-existent dir → no entries, no crash
    parts = _gather_seed_parts("2026-05-18", [tmp_path / "ghost"], ["*{date}*.md"])
    assert parts == []


def test_gather_includes_single_file_source_if_date_in_name(tmp_path: Path):
    single = tmp_path / "session_2026-05-18.md"
    single.write_text("content")
    parts = _gather_seed_parts("2026-05-18", [single], ["*{date}*.md"])
    assert len(parts) == 1
    assert parts[0][0] == "session_2026-05-18.md"


def test_gather_skips_single_file_source_if_date_not_in_name(tmp_path: Path):
    single = tmp_path / "session_2026-05-17.md"
    single.write_text("content")
    parts = _gather_seed_parts("2026-05-18", [single], ["*{date}*.md"])
    assert parts == []


def test_gather_supports_multiple_patterns(tmp_path: Path):
    (tmp_path / "a_2026-05-18.md").write_text("md")
    (tmp_path / "b_2026-05-18.txt").write_text("txt")
    parts = _gather_seed_parts(
        "2026-05-18", [tmp_path], ["*{date}*.md", "*{date}*.txt"]
    )
    titles = sorted(p[0] for p in parts)
    assert titles == ["a_2026-05-18.md", "b_2026-05-18.txt"]


# ----------------------------- _seed_text + _seed_digest -----------------------------

def test_seed_text_concatenates():
    parts = [("a.md", "content of A"), ("b.md", "content of B")]
    text = _seed_text(parts)
    assert "# a.md" in text
    assert "content of A" in text
    assert "# b.md" in text
    assert "content of B" in text


def test_seed_digest_stable():
    parts = [("a.md", "same content")]
    d1 = _seed_digest(_seed_text(parts))
    d2 = _seed_digest(_seed_text(parts))
    assert d1 == d2


def test_seed_digest_changes_with_content():
    p1 = [("a.md", "alpha")]
    p2 = [("a.md", "beta")]
    assert _seed_digest(_seed_text(p1)) != _seed_digest(_seed_text(p2))


# ----------------------------- _daily_dir -----------------------------

def test_daily_dir_structure(tmp_path: Path):
    d = _daily_dir("2026-05-18", state_root=tmp_path)
    assert d == tmp_path / "daily" / "2026-05-18"


# ----------------------------- build_daily_fish -----------------------------

def test_build_no_matching_content_succeeds_emptily(tmp_path: Path):
    src = tmp_path / "src"
    src.mkdir()
    # No matching files for 2026-05-18
    result = build_daily_fish(
        date_iso="2026-05-18",
        sources=[src],
        state_root=tmp_path,
    )
    assert isinstance(result, DailyBuildResult)
    assert result.date == "2026-05-18"
    assert result.parts_count == 0
    assert result.crystals == 0


def test_build_with_matching_content_creates_fish(tmp_path: Path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "session_2026-05-18.md").write_text(
        "The day's session contained much wisdom about cabbages and kings. "
        "Cabbages grow in gardens; kings rule kingdoms. The garden remembers "
        "what the kingdom forgets. This is the morning entry. "
        "The evening brought more thoughts about gardens and rulers."
    )
    result = build_daily_fish(
        date_iso="2026-05-18",
        sources=[src],
        state_root=tmp_path,
    )
    assert result.parts_count == 1
    assert result.crystals > 0
    assert result.fish_dir == tmp_path / "daily" / "2026-05-18"
    # State file written
    state_file = result.fish_dir / "daily.json"
    assert state_file.exists()
    state = json.loads(state_file.read_text())
    assert state["date"] == "2026-05-18"
    assert state["crystals"] == result.crystals


def test_build_idempotent_skip_on_unchanged_content(tmp_path: Path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "session_2026-05-18.md").write_text("alpha beta gamma delta")
    r1 = build_daily_fish(
        date_iso="2026-05-18",
        sources=[src],
        state_root=tmp_path,
    )
    assert r1.skipped_unchanged is False
    # Second build: same content → skip
    r2 = build_daily_fish(
        date_iso="2026-05-18",
        sources=[src],
        state_root=tmp_path,
    )
    assert r2.skipped_unchanged is True
    assert r2.seed_digest == r1.seed_digest


def test_build_force_overrides_skip(tmp_path: Path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "session_2026-05-18.md").write_text("alpha beta gamma delta")
    build_daily_fish(
        date_iso="2026-05-18",
        sources=[src],
        state_root=tmp_path,
    )
    r2 = build_daily_fish(
        date_iso="2026-05-18",
        sources=[src],
        state_root=tmp_path,
        force=True,
    )
    assert r2.skipped_unchanged is False


def test_build_rebuilds_on_content_change(tmp_path: Path):
    src = tmp_path / "src"
    src.mkdir()
    f = src / "session_2026-05-18.md"
    f.write_text("alpha beta gamma delta")
    r1 = build_daily_fish(date_iso="2026-05-18", sources=[src], state_root=tmp_path)
    # Change content
    f.write_text("epsilon zeta eta theta")
    r2 = build_daily_fish(date_iso="2026-05-18", sources=[src], state_root=tmp_path)
    assert r2.skipped_unchanged is False
    assert r2.seed_digest != r1.seed_digest


def test_build_defaults_to_today_when_no_date(tmp_path: Path):
    src = tmp_path / "src"
    src.mkdir()
    today = today_iso()
    (src / f"session_{today}.md").write_text("today's wisdom about subjects.")
    result = build_daily_fish(sources=[src], state_root=tmp_path)
    assert result.date == today


# ----------------------------- list_daily_fish -----------------------------

def test_list_empty(tmp_path: Path):
    assert list_daily_fish(state_root=tmp_path) == []


def test_list_missing_daily_root(tmp_path: Path):
    # state_root exists, but daily/ subdir does not
    assert list_daily_fish(state_root=tmp_path) == []


def test_list_finds_built_fish(tmp_path: Path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "session_2026-05-18.md").write_text("content one")
    (src / "session_2026-05-17.md").write_text("content two")
    build_daily_fish(date_iso="2026-05-18", sources=[src], state_root=tmp_path)
    build_daily_fish(date_iso="2026-05-17", sources=[src], state_root=tmp_path)
    entries = list_daily_fish(state_root=tmp_path)
    dates = sorted(e["date"] for e in entries)
    assert dates == ["2026-05-17", "2026-05-18"]
