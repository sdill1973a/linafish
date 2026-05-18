"""Stale-lockfile scanner for linafish state directories.

Parallel to the .git/index.lock catch every git tool ships — this one
catches crashed `linafish` crystallizer processes that leave their
in-app lockfiles held by dead PIDs. The crystallizer takes locks to
serialize writes to shared vocabulary (`mi_vectorizer.json.lock`)
and similar; a crash mid-write strands the lock, and downstream
operations either silently fail or block on a 5s timeout and abort.

Catch shape (2026-05-18 §FISH.LOCK.STALENESS): the AnchorLinafishMe
NSSM service ate ambient MQTT crystals for THREE DAYS while its
``mi_vectorizer.json.lock`` was held by a dead PID since 2026-05-15.
The shared MI×ache vocabulary was silently frozen for 72 hours. No
surface flagged it; the drift was only caught when a manual
``linafish listen stdin -n me`` deposit needed the lock and got
TimeoutError. This module moves the catch to ``linafish doctor``
so any user (not just the one author of that bug) sees stale locks
at boot rather than at first-use.

Lock file format (crystallizer_v3): plain text, single line,
``"PID TIMESTAMP_ISO"`` (e.g. ``"6672 2026-05-15T16:06:11.104193+00:00"``).
Tolerant of variants — empty file, PID-only, malformed timestamp.

Staleness verdict:
  age > 60s  AND pid is confirmed dead  → stale
  age > 300s AND pid liveness undetermined → stale
  otherwise → not stale (live writer or fresh contention)
"""
from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


@dataclass
class LockEntry:
    """One lockfile found on disk."""
    path: str
    fish_dir: str
    age_seconds: float
    mtime_utc: str
    pid: Optional[int]
    pid_alive: Optional[bool]  # True / False / None (indeterminate)
    stale: bool


def pid_alive(pid: Optional[int]) -> Optional[bool]:
    """Best-effort liveness check for `pid`.

    Returns True if the process is alive, False if confirmed dead, None
    if indeterminate (tasklist/ps missing, timeout, unexpected output).
    The None case lets callers fall back to age-only heuristics.
    """
    if pid is None or pid <= 0:
        return None
    try:
        if sys.platform.startswith("win"):
            r = subprocess.run(
                ["tasklist", "/NH", "/FO", "CSV", "/FI", f"PID eq {pid}"],
                capture_output=True, text=True, timeout=5,
            )
            if r.returncode != 0:
                return None
            out = (r.stdout or "").strip()
            if not out or out.lstrip().upper().startswith("INFO:"):
                return False
            return True
        # POSIX
        r = subprocess.run(
            ["ps", "-p", str(pid)],
            capture_output=True, text=True, timeout=5,
        )
        return r.returncode == 0
    except Exception:
        return None


def _parse_lock_contents(raw: str) -> Optional[int]:
    """Extract PID from a lockfile body. Returns None if unparseable."""
    if not raw:
        return None
    parts = raw.strip().split(None, 1)
    if not parts:
        return None
    try:
        return int(parts[0])
    except ValueError:
        return None


def _classify_lock(
    age_seconds: float,
    pid_is_alive: Optional[bool],
    stale_age_dead: float = 60.0,
    stale_age_indeterminate: float = 300.0,
) -> bool:
    """Apply the staleness rule.

    A lock is stale if:
      - older than stale_age_dead AND its PID is confirmed dead, OR
      - older than stale_age_indeterminate AND its PID is indeterminate
        (probably crashed-before-writing-PID; treat as suspect).
    """
    if age_seconds > stale_age_dead and pid_is_alive is False:
        return True
    if age_seconds > stale_age_indeterminate and pid_is_alive is None:
        return True
    return False


def scan_locks(
    state_root: Optional[Path] = None,
    stale_age_dead: float = 60.0,
    stale_age_indeterminate: float = 300.0,
) -> list[LockEntry]:
    """Scan a linafish state root for `*.lock` files; return entries.

    Args:
        state_root: where the fish state lives (default: ~/.linafish/).
            Scans the root itself plus every immediate subdirectory.
            School facets typically live under <root>/school/<name>/ —
            we descend one more level into school/ if it exists.
        stale_age_dead: age in seconds above which a dead-PID lock is
            considered stale (default 60s).
        stale_age_indeterminate: age above which an indeterminate-PID
            lock is considered stale (default 300s).

    Returns:
        list[LockEntry], one per lockfile found, including both stale
        and non-stale. Callers filter by `entry.stale` as needed.
    """
    if state_root is None:
        state_root = Path.home() / ".linafish"
    if not state_root.exists():
        return []

    # Build the scan list: root + immediate subdirs + school/<facet>/ dirs.
    scan_dirs = [state_root]
    try:
        for child in sorted(state_root.iterdir()):
            if child.is_dir() and child.name != "school":
                scan_dirs.append(child)
    except OSError:
        pass

    school_root = state_root / "school"
    if school_root.exists() and school_root.is_dir():
        try:
            for child in sorted(school_root.iterdir()):
                if child.is_dir():
                    scan_dirs.append(child)
        except OSError:
            pass

    entries: list[LockEntry] = []
    now_ts = datetime.now(timezone.utc).timestamp()

    for d in scan_dirs:
        try:
            lock_paths = list(d.glob("*.lock"))
        except OSError:
            continue
        for lock_path in lock_paths:
            try:
                st = lock_path.stat()
            except (OSError, FileNotFoundError):
                continue
            age_seconds = max(0.0, now_ts - st.st_mtime)
            try:
                raw = lock_path.read_text(encoding="utf-8", errors="replace")
            except (OSError, FileNotFoundError):
                raw = ""
            pid = _parse_lock_contents(raw)
            alive = pid_alive(pid) if pid is not None else None
            stale = _classify_lock(
                age_seconds, alive, stale_age_dead, stale_age_indeterminate
            )
            entries.append(LockEntry(
                path=str(lock_path),
                fish_dir=(d.name if d != state_root else "(top-level)"),
                age_seconds=round(age_seconds, 1),
                mtime_utc=datetime.fromtimestamp(
                    st.st_mtime, tz=timezone.utc
                ).isoformat(),
                pid=pid,
                pid_alive=alive,
                stale=stale,
            ))
    return entries


def remove_lock(lock_path: Path) -> tuple[bool, str]:
    """Remove a lockfile. Returns (success, message)."""
    try:
        lock_path.unlink()
        return True, f"removed {lock_path}"
    except FileNotFoundError:
        return True, f"already gone: {lock_path}"
    except OSError as e:
        return False, f"failed to remove {lock_path}: {e}"


def entry_as_dict(e: LockEntry) -> dict:
    """Convert a LockEntry to a plain dict suitable for JSON."""
    return asdict(e)
