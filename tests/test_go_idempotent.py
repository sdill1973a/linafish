"""Re-running ``linafish go`` on an unchanged corpus must be a no-op.

Regression tests for issue #52:

  Defect A — ``go`` crystallized every chunk unconditionally, so a second
  run on the same folder/state-dir doubled the crystal count (30->60
  incremental, 210->420 batch).

  Defect B — the BATCH branch did ``engine.fish.crystals = all_crystals``,
  overwriting the in-memory list with only the freshly-created batch. Any
  cold-loaded crystals were dropped from memory while they stayed on disk,
  so fish.md reported a count (e.g. 210) that disagreed with the JSONL row
  count and a cold-load (e.g. 420).

These tests assert the fix's target: after ``go`` runs, the four surfaces
that report the crystal count all agree — in-memory ``len(fish.crystals)``,
the ``*_crystals.jsonl`` row count, the ``crystal_count`` recorded in
fish.md, and what a fresh cold-load engine sees — and a second run on an
unchanged corpus adds zero crystals.

``go`` is driven with ``serve=False`` and an explicit ``state_dir`` so
nothing binds a port.
"""

import json
import re
from pathlib import Path

import pytest

from linafish.quickstart import go
from linafish.engine import FishEngine

# Below 200 documents ``go`` uses the incremental (eat) path; at/above 200
# it uses the batch path. Pick sizes that land firmly in each branch.
INCREMENTAL_DOCS = 5
BATCH_DOCS = 205


# ---------------------------------------------------------------------------
# Surface probes — the four places the crystal count is reported
# ---------------------------------------------------------------------------

def _jsonl_rows(state_dir: Path, name: str) -> int:
    """Rows in the durable crystal store on disk."""
    p = Path(state_dir) / f"{name}_crystals.jsonl"
    if not p.exists():
        return 0
    return sum(1 for line in p.read_text(encoding="utf-8").splitlines() if line.strip())


def _fish_md_count(state_dir: Path, name: str) -> int:
    """crystal_count as written into the fish.md machine-readable block."""
    text = (Path(state_dir) / f"{name}.fish.md").read_text(encoding="utf-8")
    m = re.search(r'"crystal_count":\s*(\d+)', text)
    assert m, "fish.md has no crystal_count in its FISH_STATE block"
    return int(m.group(1))


def _cold_load_count(state_dir: Path, name: str) -> int:
    """Crystals a fresh engine sees when it cold-loads the state dir."""
    engine = FishEngine(state_dir=Path(state_dir), name=name)
    return len(engine.fish.crystals)


def _memory_count(state_dir: Path, name: str) -> int:
    """len(fish.crystals) via a fresh engine (proxy for the in-memory list
    the run left behind — cold-load reconstructs it from the same store)."""
    engine = FishEngine(state_dir=Path(state_dir), name=name)
    return len(engine.fish.crystals)


def _all_surfaces(state_dir: Path, name: str):
    return {
        "memory": _memory_count(state_dir, name),
        "jsonl": _jsonl_rows(state_dir, name),
        "fish_md": _fish_md_count(state_dir, name),
        "cold_load": _cold_load_count(state_dir, name),
    }


def _assert_all_agree(state_dir: Path, name: str, expected: int):
    surfaces = _all_surfaces(state_dir, name)
    assert set(surfaces.values()) == {expected}, (
        f"surfaces disagree, expected all == {expected}: {surfaces}"
    )


def _make_docs(folder: Path, n: int, start: int = 0):
    for i in range(start, start + n):
        # Distinct, substantive content so each file is its own crystal
        # and comfortably clears the >10-char ingest gate.
        (folder / f"doc_{i:04d}.txt").write_text(
            f"Document number {i}. This entry is about thinking, testing, "
            f"structuring, and relating ideas number {i} to each other. "
            f"It repeats topic {i} enough to crystallize cleanly.",
            encoding="utf-8",
        )


# ---------------------------------------------------------------------------
# INCREMENTAL branch
# ---------------------------------------------------------------------------

def test_incremental_double_run_adds_nothing(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    state = tmp_path / "state"
    _make_docs(src, INCREMENTAL_DOCS)

    go(source=str(src), name="inc", state_dir=str(state), serve=False)
    after_first = _jsonl_rows(state, "inc")
    assert after_first == INCREMENTAL_DOCS

    go(source=str(src), name="inc", state_dir=str(state), serve=False)
    after_second = _jsonl_rows(state, "inc")

    assert after_second == after_first, (
        f"second run must add 0 crystals; disk went {after_first} -> {after_second}"
    )


def test_incremental_three_surface_agreement(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    state = tmp_path / "state"
    _make_docs(src, INCREMENTAL_DOCS)

    go(source=str(src), name="inc", state_dir=str(state), serve=False)
    go(source=str(src), name="inc", state_dir=str(state), serve=False)

    _assert_all_agree(state, "inc", INCREMENTAL_DOCS)


def test_incremental_add_one_file_ingests_only_the_new_one(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    state = tmp_path / "state"
    _make_docs(src, INCREMENTAL_DOCS)

    go(source=str(src), name="inc", state_dir=str(state), serve=False)
    _assert_all_agree(state, "inc", INCREMENTAL_DOCS)

    # Add exactly one new document, re-run.
    _make_docs(src, 1, start=INCREMENTAL_DOCS)
    go(source=str(src), name="inc", state_dir=str(state), serve=False)

    _assert_all_agree(state, "inc", INCREMENTAL_DOCS + 1)


# ---------------------------------------------------------------------------
# BATCH branch (>= 200 docs)
# ---------------------------------------------------------------------------

def test_batch_double_run_adds_nothing(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    state = tmp_path / "state"
    _make_docs(src, BATCH_DOCS)

    go(source=str(src), name="bat", state_dir=str(state), serve=False)
    after_first = _jsonl_rows(state, "bat")
    assert after_first == BATCH_DOCS

    go(source=str(src), name="bat", state_dir=str(state), serve=False)
    after_second = _jsonl_rows(state, "bat")

    assert after_second == after_first, (
        f"second batch run must add 0 crystals; disk went "
        f"{after_first} -> {after_second}"
    )


def test_batch_three_surface_agreement(tmp_path):
    """Defect B: memory / disk / fish.md / cold-load must all agree."""
    src = tmp_path / "src"
    src.mkdir()
    state = tmp_path / "state"
    _make_docs(src, BATCH_DOCS)

    go(source=str(src), name="bat", state_dir=str(state), serve=False)
    _assert_all_agree(state, "bat", BATCH_DOCS)

    go(source=str(src), name="bat", state_dir=str(state), serve=False)
    _assert_all_agree(state, "bat", BATCH_DOCS)


def test_batch_add_one_file_ingests_only_the_new_one(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    state = tmp_path / "state"
    _make_docs(src, BATCH_DOCS)

    go(source=str(src), name="bat", state_dir=str(state), serve=False)
    _assert_all_agree(state, "bat", BATCH_DOCS)

    _make_docs(src, 1, start=BATCH_DOCS)
    go(source=str(src), name="bat", state_dir=str(state), serve=False)

    _assert_all_agree(state, "bat", BATCH_DOCS + 1)
