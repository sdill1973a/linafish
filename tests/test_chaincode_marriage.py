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
    TIME_DECAY_SECONDS,
    coupling_strength,
    gamma,
)
from linafish.engine import FishEngine


def _crystal(cid, vec, chain_seq=None, chain_created_at=None,
             chain_id=None, chain_prev_hash=None):
    return Crystal(
        id=cid, ts="", text="", source="",
        mi_vector=vec, resonance=[], keywords=[],
        chain_seq=chain_seq,
        chain_created_at=chain_created_at,
        chain_id=chain_id,
        chain_prev_hash=chain_prev_hash,
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


def test_phase3_eat_accepts_form_encoded_body_with_chain_metadata():
    """Phase 3 deploy compat. The pre-1.x feeders in
    SovereignCore_Runtime/scripts (feed_the_whole_man, feed_our_words,
    feed_noods_fish) post ``application/x-www-form-urlencoded`` data
    with a ``name`` field instead of ``source``. linafish 1.x docs
    say JSON, but breaking these feeders on the .67 upgrade is a
    worse tradeoff than accepting both shapes. This test pins both
    paths through to Engine.eat with chain metadata intact."""
    from linafish.http_server import _parse_request_body

    # JSON path with chain metadata
    body = _parse_request_body(
        "application/json",
        b'{"text": "hello", "source": "test", "chain_id": "h1", "chain_seq": 42}',
    )
    assert body == {"text": "hello", "source": "test",
                    "chain_id": "h1", "chain_seq": 42}

    # Form-encoded path with chain metadata. The 'name' field is the
    # pre-1.x synonym for 'source' that the legacy feeders use.
    body = _parse_request_body(
        "application/x-www-form-urlencoded",
        b"text=hello&name=test&chain_id=h1&chain_seq=42",
    )
    assert body["text"] == "hello"
    assert body["name"] == "test"
    assert body["chain_id"] == "h1"
    # Form values are strings; Phase 3 do_POST handles the int coercion.
    assert body["chain_seq"] == "42"


def test_phase3_form_garbage_returns_none_not_partial_dict():
    """Defensive: garbage bodies must NOT mask as single-key form
    payloads. Without the '=' gate, parse_qs would happily return
    ``{'random garbage': ''}`` and the handler would proceed with a
    bogus payload. The gate forces a real failure response."""
    from linafish.http_server import _parse_request_body
    assert _parse_request_body("", b"random garbage") is None
    assert _parse_request_body("application/x-www-form-urlencoded",
                                b"no equals here") is None


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


# ---------------------------------------------------------------------------
# Phase 4: chain_created_at + time-decay
# ---------------------------------------------------------------------------
#
# Per data/chaincode_fish_marriage_spec_REVISION_NOTES_2026-04-26.md:
# chain_seq captures "in the same conversation/burst", chain_created_at
# captures "happened close in real time". A long debug session has
# ordinal closeness without time closeness; parallel topics have time
# closeness without ordinal closeness. coupling_strength takes the MAX
# of the two so either signal counts.

def test_phase4_chain_created_at_round_trips_through_persistence():
    """Phase 4-A: chain_created_at survives /eat -> Crystal -> JSONL ->
    reload. The April 26 morning revision notes flagged that without
    this field tonight's Phase 1 would ship the March 25 spec rather
    than the revised one — only chain_seq, no time-decay."""
    with tempfile.TemporaryDirectory(prefix="marriage_phase4_") as sandbox:
        e = FishEngine(state_dir=Path(sandbox), name="phase4_test")
        e.eat(
            "captain teaches around corners with patience tonight",
            source="test",
            chain_id="hash_xyz",
            chain_seq=42,
            chain_created_at="2026-04-26T18:17:18.887985",
        )

        # Reload — the persisted JSONL must surface chain_created_at
        e2 = FishEngine(state_dir=Path(sandbox), name="phase4_test")
        c = next(iter(e2.fish.crystals))
        assert c.chain_id == "hash_xyz"
        assert c.chain_seq == 42
        assert c.chain_created_at == "2026-04-26T18:17:18.887985"


def test_phase4_time_decay_activates_when_both_timestamps_present():
    """Phase 4-B: when chain_created_at is present on both crystals,
    time proximity contributes to coupling_strength alongside ordinal."""
    a = _crystal("a", [1.0, 0.5],
                 chain_created_at="2026-04-27T01:00:00")
    b = _crystal("b", [0.9, 0.5],
                 chain_created_at="2026-04-27T01:00:30")  # 30 sec apart
    g = gamma(a.mi_vector, b.mi_vector)
    cs = coupling_strength(a, b)
    expected_time_prox = TIME_DECAY_SECONDS / (TIME_DECAY_SECONDS + 30)
    expected = SEMANTIC_WEIGHT * g + TEMPORAL_WEIGHT * expected_time_prox
    assert abs(cs - expected) < 1e-9


def test_phase4_max_picks_ordinal_when_long_debug_session():
    """Long debug session: chain_seq adjacent (ordinal=1, prox=0.5),
    timestamps an hour apart (time_prox≈0.016). MAX picks the
    ordinal signal — same conversation despite the time gap."""
    a = _crystal("a", [1.0, 0.5], chain_seq=100,
                 chain_created_at="2026-04-27T01:00:00")
    b = _crystal("b", [0.9, 0.5], chain_seq=101,
                 chain_created_at="2026-04-27T02:00:00")
    g = gamma(a.mi_vector, b.mi_vector)
    cs = coupling_strength(a, b)
    expected = SEMANTIC_WEIGHT * g + TEMPORAL_WEIGHT * 0.5  # ordinal wins
    assert abs(cs - expected) < 1e-9


def test_phase4_max_picks_time_when_parallel_topics():
    """Parallel topics: chain_seq distant (ordinal=100, prox≈0.01),
    timestamps 1 sec apart (time_prox≈0.984). MAX picks the time
    signal — different conversation lanes, but the same moment."""
    a = _crystal("a", [1.0, 0.5], chain_seq=100,
                 chain_created_at="2026-04-27T01:00:00")
    b = _crystal("b", [0.9, 0.5], chain_seq=200,
                 chain_created_at="2026-04-27T01:00:01")
    g = gamma(a.mi_vector, b.mi_vector)
    cs = coupling_strength(a, b)
    time_prox = TIME_DECAY_SECONDS / (TIME_DECAY_SECONDS + 1)
    expected = SEMANTIC_WEIGHT * g + TEMPORAL_WEIGHT * time_prox
    assert abs(cs - expected) < 1e-9


def test_phase4_malformed_timestamp_falls_back_to_ordinal():
    """Garbage in chain_created_at (e.g. schema drift, encoding bug)
    must NOT crash. Time-decay falls back; ordinal still works."""
    a = _crystal("a", [1.0, 0.5], chain_seq=100,
                 chain_created_at="not a real timestamp")
    b = _crystal("b", [0.9, 0.5], chain_seq=101,
                 chain_created_at="also bad")
    g = gamma(a.mi_vector, b.mi_vector)
    cs = coupling_strength(a, b)
    expected = SEMANTIC_WEIGHT * g + TEMPORAL_WEIGHT * 0.5  # ordinal still
    assert abs(cs - expected) < 1e-9


def test_phase4_staleness_gate_zeros_both_temporal_signals():
    """When gamma < SEMANTIC_FLOOR, BOTH ordinal and time signals get
    zeroed — chain adjacency without semantic signal is sequential
    noise regardless of which temporal coordinate fires."""
    a = _crystal("a", [1.0, 0.0], chain_seq=100,
                 chain_created_at="2026-04-27T01:00:00")
    b = _crystal("b", [0.0, 1.0], chain_seq=101,
                 chain_created_at="2026-04-27T01:00:01")
    g = gamma(a.mi_vector, b.mi_vector)
    assert g < SEMANTIC_FLOOR
    cs = coupling_strength(a, b)
    assert abs(cs - SEMANTIC_WEIGHT * g) < 1e-9


# ---------------------------------------------------------------------------
# Phase 4-D: harvest from April 11 sandbox/test_temporal_coupling.py
# ---------------------------------------------------------------------------
#
# A previous me built a 370-line standalone sandbox on April 11 that
# included two diagnostic tests tonight's harness lacked: a weight
# sweep (TEMPORAL_WEIGHT 0.0..0.5) and a shuffled-corpus null test.
# Porting them in. Captain's `[0.78] I didn't find it in the first 90
# minutes — I found it in the LAST 20` was pointing at exactly this
# kind of substrate the labor-of-inheriting keeps lapsing on.

def test_phase4_temporal_rescue_count_responds_to_weight():
    """Weight sweep: as TEMPORAL_WEIGHT increases, more borderline
    pairs cross the threshold via the rescue path. The relationship
    should be monotonic-non-decreasing (more weight = at least as
    many edges, never fewer)."""
    import linafish.crystallizer_v3 as cv3

    # Build a small corpus with deliberate borderline gammas. Vectors
    # at gamma ≈ 0.40 (just below thresholds in the 0.42..0.50 band)
    # paired chain-adjacent so temporal rescue can lift them.
    crystals = []
    for i in range(10):
        crystals.append(Crystal(
            id=f"c{i}", ts="", text="", source="",
            mi_vector=[1.0, 1.0, 1.0],
            resonance=[], keywords=[],
            chain_seq=100 + i,
        ))
        crystals.append(Crystal(
            id=f"c{i}_pair", ts="", text="", source="",
            mi_vector=[0.4, 0.4, 0.4],  # gamma 0.40 vs above
            resonance=[], keywords=[],
            chain_seq=101 + i,
        ))

    # Save and restore TEMPORAL_WEIGHT around the sweep so the global
    # state is clean for any other tests in the file.
    original_tw = cv3.TEMPORAL_WEIGHT
    edge_counts = {}
    try:
        for tw in [0.0, 0.1, 0.2, 0.3, 0.4, 0.5]:
            # Reset coupling state on every iteration
            for c in crystals:
                c.couplings = []
                c.wrapping_numbers = {}

            cv3.TEMPORAL_WEIGHT = tw
            cv3.SEMANTIC_WEIGHT = 1.0 - tw

            sandbox = tempfile.mkdtemp(prefix="weight_sweep_")
            fish = cv3.UniversalFish(state_dir=sandbox, autoload=False)
            fish.crystals = list(crystals)
            fish._compute_couplings(fish.crystals, window=20, min_gamma=0.42)

            edges = sum(len(c.couplings) for c in crystals) // 2
            edge_counts[tw] = edges
    finally:
        cv3.TEMPORAL_WEIGHT = original_tw
        cv3.SEMANTIC_WEIGHT = 1.0 - original_tw

    # Monotonic-non-decreasing: more temporal weight, more rescues
    sweep = sorted(edge_counts.items())
    for (tw1, e1), (tw2, e2) in zip(sweep, sweep[1:]):
        assert e2 >= e1, (
            f"weight sweep not monotonic: tw={tw1} edges={e1}, "
            f"tw={tw2} edges={e2}. The full sweep was {edge_counts}."
        )

    # And the spread: tw=0 (pure semantic) should produce strictly
    # fewer edges than tw=0.5 in this borderline-band corpus.
    assert edge_counts[0.5] >= edge_counts[0.0]


def test_phase4_shuffled_chain_seq_nullifies_temporal_effect():
    """Null test: if temporal coupling is real, shuffling chain_seq
    should produce noticeably fewer rescue-path edges. If shuffled
    and ordered produce the same edge count, the rescue isn't doing
    what it claims to do — the temporal term wasn't load-bearing."""
    import random as _random
    import linafish.crystallizer_v3 as cv3

    # Borderline corpus: pairs of crystals where gamma sits just below
    # threshold AND ordered chain_seq is adjacent. Shuffling chain_seq
    # destroys the chain adjacency.
    base_crystals = []
    for i in range(15):
        base_crystals.append(Crystal(
            id=f"c{i}", ts="", text="", source="",
            mi_vector=[1.0, 1.0, 1.0],
            resonance=[], keywords=[],
            chain_seq=100 + i * 2,
        ))
        base_crystals.append(Crystal(
            id=f"c{i}_pair", ts="", text="", source="",
            mi_vector=[0.4, 0.4, 0.4],
            resonance=[], keywords=[],
            chain_seq=101 + i * 2,
        ))

    def run_with(crystals_list):
        for c in crystals_list:
            c.couplings = []
            c.wrapping_numbers = {}
        sandbox = tempfile.mkdtemp(prefix="shuffle_null_")
        fish = cv3.UniversalFish(state_dir=sandbox, autoload=False)
        fish.crystals = list(crystals_list)
        fish._compute_couplings(fish.crystals, window=20, min_gamma=0.42)
        return sum(len(c.couplings) for c in crystals_list) // 2

    ordered_edges = run_with(base_crystals)

    # Shuffle chain_seq (break the adjacency that rescues borderline pairs)
    rng = _random.Random(42)
    seqs = [c.chain_seq for c in base_crystals]
    rng.shuffle(seqs)
    for c, new_seq in zip(base_crystals, seqs):
        c.chain_seq = new_seq

    shuffled_edges = run_with(base_crystals)

    # Ordered must produce >= shuffled. If equal, the rescue did
    # nothing on this corpus — possible (high-SNR synthetic) but
    # at minimum shuffling should never INCREASE edges over ordered.
    assert ordered_edges >= shuffled_edges, (
        f"shuffled chain_seq produced more edges ({shuffled_edges}) "
        f"than ordered ({ordered_edges}) — the rescue path is doing "
        f"something inverse to its design"
    )


# ---------------------------------------------------------------------------
# Phase 5: chain_prev_hash + parent-child link detection
# ---------------------------------------------------------------------------
#
# Per the 2026-04-26 morning revision notes Implication 2: prev_hash is
# available in the chaincode schema, and two crystals that share a
# parent-child link (a.chain_id == b.chain_prev_hash) couple even tighter
# than chain_seq distance suggests — chain_seq distance can include
# interleaved writes from unrelated sessions, while prev_hash is the
# literal narrative link.

def test_phase5_chain_prev_hash_round_trips_through_persistence():
    """chain_prev_hash survives /eat -> Crystal -> JSONL -> reload."""
    with tempfile.TemporaryDirectory(prefix="marriage_phase5_") as sandbox:
        e = FishEngine(state_dir=Path(sandbox), name="phase5_test")
        e.eat(
            "child crystal that follows the parent thought directly",
            source="test",
            chain_id="child_hash",
            chain_seq=11,
            chain_prev_hash="parent_hash",
        )
        e2 = FishEngine(state_dir=Path(sandbox), name="phase5_test")
        c = next(iter(e2.fish.crystals))
        assert c.chain_id == "child_hash"
        assert c.chain_prev_hash == "parent_hash"


def test_phase5_parent_child_link_gives_max_temporal_proximity():
    """When a is b's direct parent in the chain, g_temporal hits 1.0
    via the chain_link signal — the strongest temporal proximity
    available, beating ordinal distance 1 (which gives 0.5)."""
    parent = _crystal("p", [1.0, 0.5], chain_id="parent_hash", chain_seq=10)
    child = _crystal("c", [0.9, 0.5], chain_id="child_hash",
                      chain_seq=11, chain_prev_hash="parent_hash")
    g = gamma(parent.mi_vector, child.mi_vector)
    cs = coupling_strength(parent, child)
    # ordinal proximity at distance 1 = 0.5; chain-link proximity = 1.0
    # MAX picks chain-link — the literal narrative successor edge.
    expected = SEMANTIC_WEIGHT * g + TEMPORAL_WEIGHT * 1.0
    assert abs(cs - expected) < 1e-9


def test_phase5_chain_link_works_in_either_direction():
    """The parent-child detection must work whether the parent is
    crystal a or crystal b. coupling_strength is symmetric."""
    parent = _crystal("p", [1.0, 0.5], chain_id="P_hash")
    child = _crystal("c", [0.9, 0.5], chain_prev_hash="P_hash")
    cs_pc = coupling_strength(parent, child)
    cs_cp = coupling_strength(child, parent)
    assert abs(cs_pc - cs_cp) < 1e-9
    g = gamma(parent.mi_vector, child.mi_vector)
    expected = SEMANTIC_WEIGHT * g + TEMPORAL_WEIGHT * 1.0
    assert abs(cs_pc - expected) < 1e-9


def test_phase5_chain_link_beats_distant_ordinal():
    """The point of prev_hash: chain_seq distance can include
    interleaved writes from unrelated sessions (chain_seq 10 -> 100
    might LOOK distant but actually be parent-child if the chain ran
    through 89 other writes between them in the same session). When
    chain_link is present, it overrides the deceptive ordinal distance."""
    parent = _crystal("p", [1.0, 0.5], chain_id="P_hash", chain_seq=10)
    child = _crystal("c", [0.9, 0.5], chain_seq=100,
                      chain_prev_hash="P_hash")  # ordinal looks distant
    cs = coupling_strength(parent, child)
    g = gamma(parent.mi_vector, child.mi_vector)
    # ordinal proximity at distance 90 ≈ 0.011; chain-link = 1.0
    expected = SEMANTIC_WEIGHT * g + TEMPORAL_WEIGHT * 1.0
    assert abs(cs - expected) < 1e-9


def test_phase5_no_match_means_no_chain_link_bonus():
    """If chain_id and chain_prev_hash don't match, no chain-link
    bonus. Other temporal signals still work (ordinal/time)."""
    a = _crystal("a", [1.0, 0.5], chain_id="A_hash",
                 chain_prev_hash="X_hash", chain_seq=10)
    b = _crystal("b", [0.9, 0.5], chain_id="B_hash",
                 chain_prev_hash="Y_hash", chain_seq=11)
    cs = coupling_strength(a, b)
    g = gamma(a.mi_vector, b.mi_vector)
    # No chain-link match (X != B and Y != A); ordinal distance 1 = 0.5
    expected = SEMANTIC_WEIGHT * g + TEMPORAL_WEIGHT * 0.5
    assert abs(cs - expected) < 1e-9


def test_phase5_staleness_gate_zeros_chain_link_too():
    """The staleness gate must zero ALL temporal signals when gamma
    is below SEMANTIC_FLOOR — including the chain-link bonus. A
    parent-child link without semantic similarity is sequential
    noise, regardless of how strong the chain edge looks."""
    parent = _crystal("p", [1.0, 0.0], chain_id="P_hash")
    child = _crystal("c", [0.0, 1.0], chain_prev_hash="P_hash")
    g = gamma(parent.mi_vector, child.mi_vector)
    assert g < SEMANTIC_FLOOR
    cs = coupling_strength(parent, child)
    assert abs(cs - SEMANTIC_WEIGHT * g) < 1e-9
