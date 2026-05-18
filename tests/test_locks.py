"""Tests for linafish.locks — stale lockfile detection.

Synthetic .lock files in a tmp dir exercise the scan logic without
touching the real ~/.linafish state.
"""
from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

from linafish.locks import (
    LockEntry,
    _classify_lock,
    _parse_lock_contents,
    entry_as_dict,
    pid_alive,
    remove_lock,
    scan_locks,
)


# ----------------------------- _parse_lock_contents -----------------------------

def test_parse_pid_and_timestamp():
    pid = _parse_lock_contents("6672 2026-05-15T16:06:11.104193+00:00")
    assert pid == 6672


def test_parse_pid_only():
    assert _parse_lock_contents("12345") == 12345


def test_parse_empty():
    assert _parse_lock_contents("") is None
    assert _parse_lock_contents("\n") is None


def test_parse_malformed():
    assert _parse_lock_contents("not-a-pid foo") is None


# ----------------------------- _classify_lock -----------------------------

def test_classify_fresh_lock_not_stale():
    # 10s old, PID alive
    assert _classify_lock(10.0, True) is False
    # 10s old, PID dead — still under the 60s threshold
    assert _classify_lock(10.0, False) is False
    # 10s old, indeterminate — under both thresholds
    assert _classify_lock(10.0, None) is False


def test_classify_old_dead_pid_is_stale():
    # 120s old, PID dead — crosses 60s + dead threshold
    assert _classify_lock(120.0, False) is True


def test_classify_old_indeterminate_below_300s_not_stale():
    # 120s old, indeterminate — under 300s indeterminate threshold
    assert _classify_lock(120.0, None) is False


def test_classify_very_old_indeterminate_is_stale():
    # 400s old, indeterminate — crosses 300s indeterminate threshold
    assert _classify_lock(400.0, None) is True


def test_classify_old_alive_pid_not_stale():
    # 1000s old, but PID is alive — never stale (live writer holds it)
    assert _classify_lock(1000.0, True) is False


# ----------------------------- pid_alive -----------------------------

def test_pid_alive_handles_none():
    assert pid_alive(None) is None
    assert pid_alive(0) is None
    assert pid_alive(-1) is None


def test_pid_alive_current_process_is_alive():
    # The current Python process MUST be alive
    assert pid_alive(os.getpid()) is True


def test_pid_alive_obviously_dead_pid_is_dead():
    # PID 999999 is effectively never assigned on common systems
    # (Linux default pid_max 32768; Windows ranges vary but 999999
    # almost never refers to a running process). Tolerate None too —
    # some platforms / harnesses may return indeterminate.
    result = pid_alive(999999)
    assert result in (False, None)


# ----------------------------- scan_locks -----------------------------

def test_scan_empty_dir(tmp_path: Path):
    # Empty state root → no entries
    entries = scan_locks(state_root=tmp_path)
    assert entries == []


def test_scan_missing_dir(tmp_path: Path):
    # Non-existent state root → no entries, no crash
    entries = scan_locks(state_root=tmp_path / "does-not-exist")
    assert entries == []


def test_scan_finds_top_level_lock(tmp_path: Path):
    lock = tmp_path / "anchor-writing.lock"
    lock.write_text("999999 2026-05-15T16:06:11+00:00")
    # Backdate it so it's clearly stale
    old_ts = time.time() - 3600  # 1h old
    os.utime(lock, (old_ts, old_ts))
    entries = scan_locks(state_root=tmp_path)
    assert len(entries) == 1
    assert entries[0].fish_dir == "(top-level)"
    assert entries[0].pid == 999999
    # 1h old + dead PID (or indeterminate) → stale either way
    assert entries[0].stale is True


def test_scan_finds_subdir_lock(tmp_path: Path):
    subdir = tmp_path / "me"
    subdir.mkdir()
    lock = subdir / "mi_vectorizer.json.lock"
    lock.write_text("999999")
    old_ts = time.time() - 3600
    os.utime(lock, (old_ts, old_ts))
    entries = scan_locks(state_root=tmp_path)
    assert len(entries) == 1
    assert entries[0].fish_dir == "me"


def test_scan_finds_school_facet_lock(tmp_path: Path):
    school = tmp_path / "school" / "captain"
    school.mkdir(parents=True)
    lock = school / "mi_vectorizer.json.lock"
    lock.write_text("999999")
    old_ts = time.time() - 3600
    os.utime(lock, (old_ts, old_ts))
    entries = scan_locks(state_root=tmp_path)
    assert len(entries) == 1
    assert entries[0].fish_dir == "captain"


def test_scan_fresh_lock_not_flagged_stale(tmp_path: Path):
    lock = tmp_path / "fresh.lock"
    lock.write_text(f"{os.getpid()} 2026-05-15T16:06:11+00:00")
    # Don't backdate — fresh + alive PID = not stale
    entries = scan_locks(state_root=tmp_path)
    assert len(entries) == 1
    assert entries[0].stale is False
    assert entries[0].pid_alive is True


def test_scan_returns_LockEntry_objects(tmp_path: Path):
    lock = tmp_path / "x.lock"
    lock.write_text("999999")
    entries = scan_locks(state_root=tmp_path)
    assert all(isinstance(e, LockEntry) for e in entries)


def test_entry_as_dict_is_jsonable(tmp_path: Path):
    import json
    lock = tmp_path / "x.lock"
    lock.write_text("999999")
    entries = scan_locks(state_root=tmp_path)
    d = entry_as_dict(entries[0])
    # Should round-trip through JSON without TypeError
    json.dumps(d)
    assert "path" in d and "stale" in d and "pid" in d


# ----------------------------- remove_lock -----------------------------

def test_remove_lock_succeeds(tmp_path: Path):
    lock = tmp_path / "removable.lock"
    lock.write_text("999999")
    ok, msg = remove_lock(lock)
    assert ok is True
    assert not lock.exists()


def test_remove_lock_missing_is_idempotent(tmp_path: Path):
    lock = tmp_path / "never-existed.lock"
    ok, msg = remove_lock(lock)
    assert ok is True
    assert "already gone" in msg


# ----------------------------- end-to-end -----------------------------

def test_end_to_end_dead_pid_stale_then_remove(tmp_path: Path):
    """Full cycle: stale lock detected, removed, next scan finds nothing."""
    lock = tmp_path / "me" / "mi_vectorizer.json.lock"
    lock.parent.mkdir()
    lock.write_text("999999 2026-05-15T16:06:11+00:00")
    old_ts = time.time() - 3600
    os.utime(lock, (old_ts, old_ts))

    entries = scan_locks(state_root=tmp_path)
    stale = [e for e in entries if e.stale]
    assert len(stale) == 1

    ok, _ = remove_lock(Path(stale[0].path))
    assert ok is True

    entries_after = scan_locks(state_root=tmp_path)
    assert entries_after == []
