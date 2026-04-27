"""Chaincode + Fish marriage tests.

Spec: data/chaincode_fish_marriage_spec.md (2026-03-25, Captain approved).

Phase 1 of the build: Crystal carries chain_id/chain_seq, coupling_strength
blends semantic gamma with temporal proximity under a staleness filter,
and the metadata round-trips through ingest -> persist -> reload.

Phase 2 (separate, not yet integrated) will wire coupling_strength into
_compute_couplings. Until then, _compute_couplings is unchanged and these
tests pin the coupling_strength contract so the integration step has a
known-good reference.
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
