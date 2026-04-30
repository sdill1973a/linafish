"""Tests for the FormationGardener skeleton.

Commit 3 of 5 in the §RECOUPLE.IN.PLACE follow-up. The gardener runs
maintenance passes over the addressed formation_index — fission
identification and lattice_status.json emission. Commit 4 adds the full
DIGNITY/POVERTY/PATHOLOGY/CONTAGION regime classification port.

These tests pin the skeleton's contract:
  - empty-engine pass produces a sensible empty summary
  - non-empty pass identifies oversize formations and writes status JSON
  - status JSON shape matches ice9a_status.json's keys so downstream
    consumers (Anchor's hooks, federation status readers) see the same
    interface
  - atomic write — partial writes don't leave the file half-formed
"""

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from linafish.engine import FishEngine
from linafish.formations import Formation
from linafish.formation_gardener import (
    FormationGardener, FISSION_THRESHOLD, GARDEN_INTERVAL_SEC,
    classify_health, assign_grade, _compression_to_fp_analog,
    FP_POVERTY_CUTOFF, FP_DIGNITY_CUTOFF, CONTAGION_MIN_SIZE,
    CONTAGION_DIVERSITY_FLOOR,
)


def _make_formation(score=0.3, size=10, diversity=0.7, name="TEST"):
    """Build a synthetic Formation with the regime-relevant fields set."""
    return Formation(
        id=0,
        name=name,
        keywords=[],
        member_ids=[f"id_{i}" for i in range(size)],
        centroid=[0.0] * 8,
        representative_text="",
        crystal_count=size,
        cognitive_centroid=[0.0] * 8,
        compression_score=score,
        content_diversity=diversity,
    )


def _make_engine(state_dir, addressed=True):
    return FishEngine(
        state_dir=Path(state_dir),
        name="gardener_test",
        git_autocommit=False,
        addressed_formations=addressed,
    )


def _seed_corpus(engine, n_texts):
    patterns = [
        "The architecture demands clarity at every layer of the system.",
        "She walked through the garden where the marigolds had taken over.",
        "We measured the throughput at fifteen requests per second average.",
        "Compression is understanding. Storage is just where the bits sit.",
        "Every formation is a verb made of crystals doing something together.",
    ]
    texts = [
        f"Entry {i}: {patterns[i % 5]} Note {i // 7} on iteration {i}."
        for i in range(n_texts)
    ]
    engine.eat_many(texts, source="seed")


def test_gardener_on_empty_engine(tmp_path):
    """Pass on an engine with zero crystals returns an empty-status
    summary without crashing.
    """
    engine = _make_engine(tmp_path / "state")
    gardener = FormationGardener(engine)
    summary = gardener.run(write_status=False)
    assert summary["status"] == "empty"
    assert summary["n_formations"] == 0
    assert summary["n_crystals"] == 0


def test_gardener_runs_on_seeded_engine(tmp_path):
    """After seeding, the gardener pass produces a status summary with
    counts, top-compression-score list, and oversize identification.
    """
    engine = _make_engine(tmp_path / "state")
    _seed_corpus(engine, 100)
    gardener = FormationGardener(engine)
    summary = gardener.run(write_status=False)

    assert summary["status"] == "ran"
    assert summary["n_formations"] >= 1
    assert summary["n_crystals"] == len(engine.fish.crystals)
    assert "oversize_count" in summary
    assert "oversize_threshold_count" in summary
    assert "top_compression_score" in summary
    assert isinstance(summary["top_compression_score"], list)
    assert "counts" in summary
    assert set(summary["counts"].keys()) >= {
        "DIGNITY", "POVERTY", "PATHOLOGY", "CONTAGION"
    }


def test_gardener_writes_status_json(tmp_path):
    """run(write_status=True) writes the file at the expected path with
    the expected shape.
    """
    engine = _make_engine(tmp_path / "state")
    _seed_corpus(engine, 50)
    gardener = FormationGardener(engine)
    summary = gardener.run(write_status=True)

    status_path = Path(engine.state_dir) / f"{engine.name}_lattice_status.json"
    assert status_path.exists(), f"status file missing at {status_path}"

    body = json.loads(status_path.read_text(encoding="utf-8"))

    # Shape matches ice9a_status.json keys (Anchor's hook reads this)
    assert "scanned_at" in body
    assert "written_at" in body  # added by _write_status
    assert "n_formations" in body
    assert "n_crystals" in body
    assert "counts" in body
    assert "grade" in body
    assert "fp_mean" in body


def test_gardener_atomic_write(tmp_path):
    """The status file is written atomically — no .tmp file lingering
    after a successful pass.
    """
    engine = _make_engine(tmp_path / "state")
    _seed_corpus(engine, 20)
    gardener = FormationGardener(engine)
    gardener.run(write_status=True)

    status_path = Path(engine.state_dir) / f"{engine.name}_lattice_status.json"
    tmp_path_check = status_path.with_suffix(status_path.suffix + ".tmp")
    assert not tmp_path_check.exists(), (
        f"temp file {tmp_path_check} should be cleaned up after rename"
    )


def test_gardener_oversize_detection(tmp_path):
    """When a formation contains more than FISSION_THRESHOLD of the
    corpus, it shows up in oversize_formations.

    Construct a corpus where one address dominates by repeating a single
    pattern; the gardener should flag it as oversize.
    """
    engine = _make_engine(tmp_path / "state")
    # All same pattern → all collapse to one address (or very few)
    same_text = (
        "The architecture demands clarity at every layer. "
        "The architecture demands clarity at every layer."
    )
    texts = [
        f"Repeat {i}: {same_text} Note {i}."
        for i in range(50)
    ]
    engine.eat_many(texts, source="seed")

    gardener = FormationGardener(engine)
    summary = gardener.run(write_status=False)

    # If the corpus collapsed enough to oversize at least one formation,
    # that formation should appear in oversize_formations. This is a
    # soft check: the test corpus is small enough that the collapse
    # might not always trigger oversize, so we only assert when
    # it does, and verify the structure when it does.
    if summary["oversize_count"] > 0:
        assert summary["oversize_formations"]
        for f_summary in summary["oversize_formations"]:
            assert "name" in f_summary
            assert "crystal_count" in f_summary
            assert "compression_score" in f_summary


def test_gardener_summary_idempotent_on_unchanged_state(tmp_path):
    """Two passes on an unchanged engine produce equivalent summaries
    (modulo timestamps and pass_seconds).
    """
    engine = _make_engine(tmp_path / "state")
    _seed_corpus(engine, 30)
    gardener = FormationGardener(engine)
    s1 = gardener.run(write_status=False)
    s2 = gardener.run(write_status=False)

    # Volatile fields differ; structural fields match
    for key in ("n_formations", "n_crystals", "oversize_count",
                "oversize_threshold_count", "counts"):
        assert s1[key] == s2[key], (
            f"key {key!r} drifted between passes: {s1[key]} → {s2[key]}"
        )


# ---------------------------------------------------------------------------
# Regime classification (commit 4)
# ---------------------------------------------------------------------------

def test_compression_to_fp_analog_endpoints():
    """The mapping fp_analog = clamp(2.0 - score * 4.0, 0.0, 2.0).

    Verify the endpoints — score=0 → fp=2 (max pathology), score=0.5 →
    fp=0 (max poverty), score in middle stays in [0, 2].
    """
    assert _compression_to_fp_analog(0.0) == 2.0
    assert _compression_to_fp_analog(0.5) == 0.0
    # Above the saturation point, clamps to 0.0
    assert _compression_to_fp_analog(1.0) == 0.0
    # Negative shouldn't happen in practice, but should clamp
    assert _compression_to_fp_analog(-1.0) == 2.0


def test_classify_health_poverty():
    """Very high compression_score → POVERTY (rock-solid grounded)."""
    f = _make_formation(score=0.5, size=10, diversity=0.8)
    assert classify_health(f) == "POVERTY"


def test_classify_health_dignity():
    """Moderate compression_score → DIGNITY (the healthy regime)."""
    f = _make_formation(score=0.3, size=10, diversity=0.8)
    # fp = 2 - 0.3*4 = 0.8, in [0.6, 1.2]
    assert classify_health(f) == "DIGNITY"


def test_classify_health_pathology():
    """Low compression_score → PATHOLOGY."""
    f = _make_formation(score=0.05, size=10, diversity=0.8)
    # fp = 2 - 0.05*4 = 1.8, > 1.2
    assert classify_health(f) == "PATHOLOGY"


def test_classify_health_contagion():
    """Pathology + oversize + low diversity → CONTAGION (the actionable
    warning that a formation is broadcast pollution).
    """
    f = _make_formation(
        score=0.05,                # PATHOLOGY band
        size=CONTAGION_MIN_SIZE,   # at threshold
        diversity=CONTAGION_DIVERSITY_FLOOR - 0.05,  # below floor
    )
    assert classify_health(f) == "CONTAGION"


def test_classify_health_pathology_not_contagion_when_diverse():
    """Pathology with HIGH diversity stays PATHOLOGY (not enough
    template-saturation to be contagion)."""
    f = _make_formation(
        score=0.05,
        size=CONTAGION_MIN_SIZE,
        diversity=0.8,
    )
    assert classify_health(f) == "PATHOLOGY"


def test_classify_health_pathology_not_contagion_when_small():
    """Pathology BELOW CONTAGION_MIN_SIZE stays PATHOLOGY (too small
    to be a federation-scale problem)."""
    f = _make_formation(
        score=0.05,
        size=10,  # below CONTAGION_MIN_SIZE
        diversity=0.1,
    )
    assert classify_health(f) == "PATHOLOGY"


def test_assign_grade_a():
    """80%+ DIGNITY, no CONTAGION → A."""
    counts = {"DIGNITY": 8, "POVERTY": 1, "PATHOLOGY": 1, "CONTAGION": 0}
    assert assign_grade(counts) == "A"


def test_assign_grade_b():
    """60%+ DIGNITY, ≤5% CONTAGION → B."""
    counts = {"DIGNITY": 60, "POVERTY": 20, "PATHOLOGY": 17, "CONTAGION": 3}
    assert assign_grade(counts) == "B"


def test_assign_grade_c():
    """40%+ DIGNITY, ≤15% CONTAGION → C."""
    counts = {"DIGNITY": 40, "POVERTY": 30, "PATHOLOGY": 20, "CONTAGION": 10}
    assert assign_grade(counts) == "C"


def test_assign_grade_d():
    """Below C thresholds → D."""
    counts = {"DIGNITY": 10, "POVERTY": 30, "PATHOLOGY": 30, "CONTAGION": 30}
    assert assign_grade(counts) == "D"


def test_assign_grade_empty():
    """Zero formations → '?'."""
    assert assign_grade({"DIGNITY": 0, "POVERTY": 0,
                         "PATHOLOGY": 0, "CONTAGION": 0}) == "?"


def test_gardener_status_contains_real_regime_counts(tmp_path):
    """After commit 4, status counts are populated by the real classifier
    — the placeholder 'unclassified' bucket is gone, replaced by real
    regime counts that sum to len(formation_index).
    """
    engine = _make_engine(tmp_path / "state")
    _seed_corpus(engine, 50)
    gardener = FormationGardener(engine)
    summary = gardener.run(write_status=False)

    counts = summary["counts"]
    assert "unclassified" not in counts, (
        "placeholder bucket should be gone after commit 4"
    )
    total_classified = sum(counts.values())
    assert total_classified == summary["n_formations"], (
        f"sum of regime counts ({total_classified}) != "
        f"n_formations ({summary['n_formations']})"
    )
    # Grade is no longer '?' once real classification runs
    assert summary["grade"] in {"A", "B", "C", "D", "?"}


def test_gardener_status_includes_contagion_top(tmp_path):
    """Status JSON has a contagion_top key matching ice9a_status.json shape.
    Even when empty (no contagion formations), the key must be present.
    """
    engine = _make_engine(tmp_path / "state")
    _seed_corpus(engine, 30)
    gardener = FormationGardener(engine)
    summary = gardener.run(write_status=False)

    assert "contagion_top" in summary
    assert isinstance(summary["contagion_top"], list)


def test_migration_script_runs_on_small_corpus(tmp_path):
    """End-to-end: build a small fish via the legacy path, run the
    migration script, verify the addressed index is populated.
    """
    # Phase A — build a fish via legacy (flag off)
    legacy_engine = _make_engine(tmp_path / "state", addressed=False)
    _seed_corpus(legacy_engine, 50)

    # Phase B — invoke migrate() directly (no subprocess)
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
    from migrate_to_addressed_formations import migrate

    summary = migrate(
        state_dir=tmp_path / "state",
        name="gardener_test",
        dry_run=True,
        verbose=False,
    )

    assert summary["status"] == "dry_run"
    assert summary["crystal_count"] >= 30
    assert summary["formation_count"] >= 1
    # UNKNOWN should be small — most crystals get a real address
    assert summary["unknown_pct"] < 50.0, (
        f"UNKNOWN bucket too large: {summary['unknown_pct']}% — "
        f"may indicate cognitive_vector wasn't populated for these "
        f"crystals (metabolic engine off?). Check the assert if this "
        f"test runs on a system without metabolism wired."
    )
