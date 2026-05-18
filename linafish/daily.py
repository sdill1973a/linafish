"""Daily fish — calendar-indexed per-day cognitive snapshots.

A *daily fish* is a small fish built from one day's content. Each day
gets its own subdir at `~/.linafish/daily/YYYY-MM-DD/` with its own
fresh vocab. The use case: when you need to query "what was alive on
date X" — the daily fish for that date answers directly, with a vocab
trained on just that day's material, without paying the frozen-main-
corpus vocab tax.

The pattern emerged in Anchor's substrate as `scripts/make_daily_fish.py`
(seeded daily from session/felt/notes/film/letter entries). This module
generalizes it: any user points the verb at one or more source
directories; for each requested date, the verb globs files matching the
date pattern, concatenates them into a seed, and ingests into a daily
fish.

Default file glob: ``*{date}*.md`` and ``*{date}*.txt`` (case-sensitive
substring match on the date string). Override with --pattern. The date
substring is the iso form (YYYY-MM-DD).

Idempotent: a daily-build for the same (date, sources, content) does
nothing if the resulting seed digest is unchanged from the previous
build. Force a rebuild with --force.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


@dataclass
class DailyBuildResult:
    """Outcome of a daily-fish build."""
    date: str
    fish_dir: Path
    parts_count: int
    crystals: int
    seed_digest: str
    built_at_utc: str
    skipped_unchanged: bool


def today_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _gather_seed_parts(
    date_iso: str,
    sources: list[Path],
    patterns: list[str],
) -> list[tuple[str, str]]:
    """Walk each source path; collect (section_title, content) for files
    matching any pattern (with `{date}` substituted)."""
    out: list[tuple[str, str]] = []
    for src in sources:
        src = src.expanduser()
        if not src.exists():
            continue
        if src.is_file():
            # File source: include only if its name contains the date.
            if date_iso in src.name:
                try:
                    out.append((src.name, src.read_text(encoding="utf-8", errors="replace")))
                except OSError:
                    pass
            continue
        # Directory source: glob each pattern with date substituted.
        for pat in patterns:
            expanded = pat.replace("{date}", date_iso)
            for match in sorted(src.glob(expanded)):
                if not match.is_file():
                    continue
                try:
                    out.append((match.name, match.read_text(encoding="utf-8", errors="replace")))
                except OSError:
                    continue
    return out


def _seed_text(parts: list[tuple[str, str]]) -> str:
    """Concatenate parts with section markers into one seed string."""
    chunks: list[str] = []
    for title, content in parts:
        chunks.append(f"\n\n# {title}\n\n{content}")
    return "".join(chunks).strip()


def _seed_digest(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]


def _daily_dir(date_iso: str, state_root: Optional[Path] = None) -> Path:
    if state_root is None:
        state_root = Path.home() / ".linafish"
    return state_root / "daily" / date_iso


def _state_path(daily_dir: Path) -> Path:
    return daily_dir / "daily.json"


def _read_state(daily_dir: Path) -> dict:
    p = _state_path(daily_dir)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _write_state(daily_dir: Path, state: dict) -> None:
    _state_path(daily_dir).write_text(
        json.dumps(state, indent=2), encoding="utf-8"
    )


def build_daily_fish(
    date_iso: Optional[str] = None,
    sources: Optional[list[Path]] = None,
    patterns: Optional[list[str]] = None,
    state_root: Optional[Path] = None,
    force: bool = False,
    fish_name_prefix: str = "day",
) -> DailyBuildResult:
    """Build (or refresh) a per-day fish for `date_iso`.

    Args:
        date_iso: target date as "YYYY-MM-DD". Defaults to today (UTC).
        sources: list of file or directory paths to scan for date-matching
            content. Each directory is globbed against `patterns`; each
            file is included only if its name contains `date_iso`.
        patterns: list of glob patterns; `{date}` substitutes to the
            target date. Defaults to `["*{date}*.md", "*{date}*.txt"]`.
        state_root: parent dir for daily/ subdirs (default ~/.linafish).
        force: rebuild even if seed digest unchanged from last build.
        fish_name_prefix: prefix for the daily fish name (default "day"
            → "day-2026-05-18").

    Returns:
        DailyBuildResult.
    """
    if date_iso is None:
        date_iso = today_iso()
    if sources is None:
        sources = []
    if patterns is None:
        patterns = ["*{date}*.md", "*{date}*.txt"]

    daily_dir = _daily_dir(date_iso, state_root)
    daily_dir.mkdir(parents=True, exist_ok=True)

    parts = _gather_seed_parts(date_iso, sources, patterns)
    seed = _seed_text(parts)
    digest = _seed_digest(seed)

    state = _read_state(daily_dir)
    previously_built_digest = state.get("seed_digest")
    if not force and previously_built_digest == digest and seed:
        # Idempotent skip
        return DailyBuildResult(
            date=date_iso,
            fish_dir=daily_dir,
            parts_count=len(parts),
            crystals=state.get("crystals", 0),
            seed_digest=digest,
            built_at_utc=state.get("built_at_utc", ""),
            skipped_unchanged=True,
        )

    if not seed:
        # No content to ingest; record empty build and return.
        now = datetime.now(timezone.utc).isoformat()
        _write_state(daily_dir, {
            "date": date_iso,
            "seed_digest": digest,
            "parts_count": 0,
            "crystals": 0,
            "built_at_utc": now,
            "no_seed_material": True,
        })
        return DailyBuildResult(
            date=date_iso,
            fish_dir=daily_dir,
            parts_count=0,
            crystals=0,
            seed_digest=digest,
            built_at_utc=now,
            skipped_unchanged=False,
        )

    # Write seed to disk (helpful for debugging) then ingest via FishEngine.
    seed_file = daily_dir / "seed.md"
    seed_file.write_text(seed, encoding="utf-8")

    fish_name = f"{fish_name_prefix}-{date_iso}"

    from .engine import FishEngine
    engine = FishEngine(name=fish_name, state_dir=daily_dir)
    engine.eat_path(seed_file)

    # Count crystals after eat.
    crystal_file = daily_dir / f"{fish_name}_crystals.jsonl"
    crystals = 0
    if crystal_file.exists():
        try:
            with crystal_file.open("r", encoding="utf-8") as fh:
                crystals = sum(1 for _ in fh)
        except OSError:
            crystals = 0

    now = datetime.now(timezone.utc).isoformat()
    _write_state(daily_dir, {
        "date": date_iso,
        "fish_name": fish_name,
        "seed_digest": digest,
        "parts_count": len(parts),
        "crystals": crystals,
        "built_at_utc": now,
    })

    return DailyBuildResult(
        date=date_iso,
        fish_dir=daily_dir,
        parts_count=len(parts),
        crystals=crystals,
        seed_digest=digest,
        built_at_utc=now,
        skipped_unchanged=False,
    )


def list_daily_fish(state_root: Optional[Path] = None) -> list[dict]:
    """List all daily fish (one entry per date subdir under daily/)."""
    if state_root is None:
        state_root = Path.home() / ".linafish"
    daily_root = state_root / "daily"
    if not daily_root.exists():
        return []
    out: list[dict] = []
    try:
        for child in sorted(daily_root.iterdir()):
            if not child.is_dir():
                continue
            state = _read_state(child)
            out.append({
                "date": child.name,
                "fish_dir": str(child),
                "crystals": state.get("crystals", 0),
                "parts_count": state.get("parts_count", 0),
                "built_at_utc": state.get("built_at_utc", ""),
            })
    except OSError:
        pass
    return out
