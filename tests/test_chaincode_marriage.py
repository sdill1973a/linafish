"""Chaincode + Fish marriage tests.

Spec: data/chaincode_fish_marriage_spec.md (2026-03-25, Captain approved).

Phase 1 (commit 406169e): Crystal carries chain_id/chain_seq,
coupling_strength blends semantic gamma with temporal proximity under
a staleness filter, and the metadata round-trips through ingest ->
persist -> reload. _compute_couplings stayed unchanged.

Phase 2 (this file's later tests): _compute_couplings gets a temporal
rescue path that mirrors the existing chain_rescue + metabolic_rescue
patterns. Borderline-gamma pairs with chain_seq metadata get a
coupling_strength check; if the blended score clears min_gamma, they
couple. Backward compatible — pairs without chain_seq fall through
the rescue block entirely.
"""
import json
import tempfile
from pathlib import Path

from linafish.crystallizer_v3 import (
    Crystal,
    SEMANTIC_FLOOR,
    SEMANTIC_WEIGHT,
    TEMPORAL_WEIGHT,
    coupling_strength,
    gamma,
)
from linafish.engine import FishEngine


def _crystal(cid, vec, chain_seq=None):
    return Crystal(
        id=cid, ts="", text="", source="",
        mi_vector=vec, resonance=[], keywords=[],
        chain_seq=chain_seq,
    )


def test_no_chain_metadata_reduces_to_semantic_weight_times_gamma():
    """Backward compat: crystals without chain_seq fall through to
    SEMANTIC_WEIGHT * gamma. Pre-marriage crystals lose nothing."""
    a = _crystal("a", [1.0, 0.5, 0.2])
    b = _crystal("b", [0.9, 0.4, 0.3])
    g = gamma(a.mi_vector, b.mi_vector)
    cs = coupling_strength(a, b)
    assert abs(cs - SEMANTIC_WEIGHT * g) < 1e-9


def test_adjacent_chain_entries_get_temporal_bonus_when_semantic_above_floor():
    """Two semantically-related crystals adjacent in the chaincode chain
    should couple more strongly than identical pair with no chain metadata."""
    a = _crystal("a", [1.0, 0.5, 0.2], chain_seq=100)
    b = _crystal("b", [0.9, 0.4, 0.3], chain_seq=101)
    g = gamma(a.mi_vector, b.mi_vector)
    assert g >= SEMANTIC_FLOOR  # test setup guard

    cs = coupling_strength(a, b)
    expected = SEMANTIC_WEIGHT * g + TEMPORAL_WEIGHT * (1.0 / 2.0)  # distance=1
    assert abs(cs - expected) < 1e-9

    # And the temporal bonus actually moves the value upward
    no_chain_a = _crystal("a", a.mi_vector)
    no_chain_b = _crystal("b", b.mi_vector)
    assert cs > coupling_strength(no_chain_a, no_chain_b)


def test_staleness_filter_blocks_temporal_when_semantic_below_floor():
    """Olorina's staleness gate. Two sensor readings at T and T+1 are
    chain-adjacent but semantically identical noise. Without the gate,
    pure chain proximity would mega-couple them. With the gate,
    g_temporal is forced to zero when gamma falls below SEMANTIC_FLOOR."""
    a = _crystal("a", [1.0, 0.0, 0.0], chain_seq=100)
    b = _crystal("b", [0.0, 0.0, 1.0], chain_seq=101)
    g = gamma(a.mi_vector, b.mi_vector)
    assert g < SEMANTIC_FLOOR  # test setup guard

    cs = coupling_strength(a, b)
    # Staleness filter zeroes the temporal term — result is purely semantic
    assert abs(cs - SEMANTIC_WEIGHT * g) < 1e-9


def test_distance_zero_does_not_add_temporal_bonus():
    """Per spec: the temporal term only applies when distance > 0.
    Two crystals at the same chain_seq are effectively the same chaincode
    entry; there is no temporal *proximity* to bonus."""
    a = _crystal("a", [1.0, 0.5], chain_seq=100)
    b = _crystal("b", [0.9, 0.5], chain_seq=100)
    g = gamma(a.mi_vector, b.mi_vector)
    cs = coupling_strength(a, b)
    assert abs(cs - SEMANTIC_WEIGHT * g) < 1e-9


def test_temporal_bonus_decays_with_distance():
    """1 / (1 + distance) decay. Adjacent pair >> distant pair when
    semantic similarity is held constant."""
    base = [0.9, 0.5]
    near_a = _crystal("na", base, chain_seq=100)
    near_b = _crystal("nb", base, chain_seq=101)
    far_a = _crystal("fa", base, chain_seq=100)
    far_b = _crystal("fb", base, chain_seq=10000)

    cs_near = coupling_strength(near_a, near_b)
    cs_far = coupling_strength(far_a, far_b)
    assert cs_near > cs_far


def test_one_sided_chain_metadata_yields_no_temporal_bonus():
    """If only one of the pair has chain_seq, there's no proximity to
    measure. Coupling reduces to the semantic-only path."""
    a = _crystal("a", [0.9, 0.5], chain_seq=100)
    b = _crystal("b", [0.9, 0.5], chain_seq=None)
    g = gamma(a.mi_vector, b.mi_vector)
    cs = coupling_strength(a, b)
    assert abs(cs - SEMANTIC_WEIGHT * g) < 1e-9


def test_eat_persists_chain_metadata_and_reloads():
    """End-to-end: /eat -> Engine.eat -> Crystal -> JSONL -> reload.
    Chain metadata must survive the full round-trip, and legacy
    deposits without chain metadata must continue to work."""
    with tempfile.TemporaryDirectory(prefix="marriage_") as sandbox:
        e = FishEngine(state_dir=Path(sandbox), name="marriage_test")
        e.eat(
            "The captain teaches around corners with patience and warmth tonight.",
            source="test_session",
            chain_id="abc123",
            chain_seq=42,
        )
        e.eat(
            "A second deposit without any chaincode position attached.",
            source="test_session",
        )

        # Reload from disk — verify chain fields survive round-trip
        e2 = FishEngine(state_dir=Path(sandbox), name="marriage_test")
        assert len(e2.fish.crystals) == 2

        with_chain = next(c for c in e2.fish.crystals if "captain" in c.text.lower())
        legacy = next(c for c in e2.fish.crystals if "second" in c.text.lower())

        assert with_chain.chain_id == "abc123"
        assert with_chain.chain_seq == 42
        assert legacy.chain_id is None
        assert legacy.chain_seq is None


def test_pending_record_carries_chain_metadata_pre_freeze():
    """Pre-freeze deposits go to the pending JSONL. The chain metadata
    must travel with them so a future re-eat can re-crystallize with
    chain position intact."""
    with tempfile.TemporaryDirectory(prefix="marriage_pending_") as sandbox:
        from linafish.crystallizer_v3 import UniversalFish
        fish = UniversalFish(state_dir=sandbox, autoload=False)
        # Force unfrozen path by bypassing engine setup
        fish.frozen = False
        fish.crystallize_text(
            "A pre-freeze deposit waits in the pending queue until re-eat.",
            source="test", chain_id="def456", chain_seq=99,
        )

        pending_path = Path(sandbox) / "fish_v3_pending.jsonl"
        assert pending_path.exists()
        with open(pending_path) as f:
            lines = [json.loads(l) for l in f if l.strip()]
        assert len(lines) == 1
        rec = lines[0]
        assert rec["chain_id"] == "def456"
        assert rec["chain_seq"] == 99


# ---------------------------------------------------------------------------
# Phase 2: temporal-rescue integration in _compute_couplings
# ---------------------------------------------------------------------------
#
# These tests exercise the rescue path directly. We construct a tiny
# UniversalFish, hand it a curated crystal list, and call
# _compute_couplings with a fixed min_gamma so the rescue conditions
# are deterministic. The crystals are built with hand-picked mi_vectors
# whose gamma values are exact.

def _fish_with_crystals(crystals):
    """Build a sandboxed UniversalFish wrapping a curated crystal list."""
    from linafish.crystallizer_v3 import UniversalFish
    sandbox = tempfile.mkdtemp(prefix="marriage_phase2_")
    fish = UniversalFish(state_dir=sandbox, autoload=False)
    fish.crystals = list(crystals)
    return fish


def test_phase2_temporal_rescue_lifts_borderline_chain_adjacent_pair():
    """A pair just below the gamma threshold but chain-adjacent and
    semantically passable should be rescued. The blended score must
    still clear min_gamma — the rescue doesn't lower the bar, it gives
    chain-narrative arcs a shot at the same bar."""
    # gamma = sum(min)/sum(max). [1.0, 1.0] vs [0.4, 0.4] → 0.8/2.0 = 0.4.
    # blended = 0.7 * 0.4 + 0.3 * 0.5 (distance=1) = 0.28 + 0.15 = 0.43
    a = Crystal(id="A", ts="", text="a", source="t",
                mi_vector=[1.0, 1.0], resonance=[], keywords=[],
                chain_seq=100)
    b = Crystal(id="B", ts="", text="b", source="t",
                mi_vector=[0.4, 0.4], resonance=[], keywords=[],
                chain_seq=101)

    fish = _fish_with_crystals([a, b])
    # Threshold above gamma=0.4 but below blended=0.43 — only the
    # rescue path can produce a coupling here.
    fish._compute_couplings(fish.crystals, window=2, min_gamma=0.42)

    assert a.couplings, "rescue should have coupled A to B"
    assert any(cid == "B" for cid, _ in a.couplings)


def test_phase2_staleness_blocks_rescue_when_semantic_below_floor():
    """Two crystals chain-adjacent but semantically dissimilar (gamma
    below SEMANTIC_FLOOR) must not couple. The staleness filter inside
    coupling_strength zeroes the temporal term, so the blended score
    falls back to SEMANTIC_WEIGHT * gamma — which is below the floor
    by construction, well below any reasonable threshold."""
    # gamma = 0/2 = 0.0, far below SEMANTIC_FLOOR (0.2)
    a = Crystal(id="A", ts="", text="a", source="t",
                mi_vector=[1.0, 0.0], resonance=[], keywords=[],
                chain_seq=100)
    b = Crystal(id="B", ts="", text="b", source="t",
                mi_vector=[0.0, 1.0], resonance=[], keywords=[],
                chain_seq=101)

    fish = _fish_with_crystals([a, b])
    fish._compute_couplings(fish.crystals, window=2, min_gamma=0.2)

    assert not a.couplings, (
        "staleness filter must block rescue when gamma < SEMANTIC_FLOOR"
    )
    assert not b.couplings


def test_phase2_legacy_crystals_without_chain_seq_unchanged():
    """The rescue block is gated on chain_seq being present on BOTH
    crystals. Legacy data with no chain metadata must traverse the
    same path as before Phase 2 — pair couples iff gamma >= min_gamma,
    period. No accidental coupling, no accidental decoupling."""
    a = Crystal(id="A", ts="", text="a", source="t",
                mi_vector=[1.0, 1.0], resonance=[], keywords=[])
    b = Crystal(id="B", ts="", text="b", source="t",
                mi_vector=[0.4, 0.4], resonance=[], keywords=[])

    fish = _fish_with_crystals([a, b])
    fish._compute_couplings(fish.crystals, window=2, min_gamma=0.42)

    assert not a.couplings, (
        "legacy pair below gamma threshold must NOT couple — "
        "rescue block must skip when chain_seq is None on either side"
    )


def test_phase2_one_sided_chain_seq_does_not_trigger_rescue():
    """If only one crystal in the pair carries chain_seq, the pair
    has no temporal proximity to measure. Rescue block must skip."""
    a = Crystal(id="A", ts="", text="a", source="t",
                mi_vector=[1.0, 1.0], resonance=[], keywords=[],
                chain_seq=100)
    b = Crystal(id="B", ts="", text="b", source="t",
                mi_vector=[0.4, 0.4], resonance=[], keywords=[],
                chain_seq=None)

    fish = _fish_with_crystals([a, b])
    fish._compute_couplings(fish.crystals, window=2, min_gamma=0.42)

    assert not a.couplings


def test_phase2_high_gamma_couples_via_primary_path_not_rescue():
    """When gamma alone clears the threshold, the primary path
    couples and the rescue path is never entered. Verifies temporal
    didn't somehow shadow the legacy semantics for the easy case."""
    # gamma=1.0, way above any reasonable threshold
    a = Crystal(id="A", ts="", text="a", source="t",
                mi_vector=[1.0, 1.0], resonance=[], keywords=[],
                chain_seq=100)
    b = Crystal(id="B", ts="", text="b", source="t",
                mi_vector=[1.0, 1.0], resonance=[], keywords=[],
                chain_seq=10000)  # chain-distant, temporal contribution tiny

    fish = _fish_with_crystals([a, b])
    fish._compute_couplings(fish.crystals, window=2, min_gamma=0.5)

    assert a.couplings, "high-gamma pair must couple via primary path"
    # Stored gamma should be the raw gamma, not the blended score
    coupling_value = dict(a.couplings)["B"]
    assert abs(coupling_value - 1.0) < 1e-3, (
        f"primary-path coupling should record raw gamma, got {coupling_value}"
    )
