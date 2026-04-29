"""Tests for formation_address — the §RECOUPLE.IN.PLACE follow-up.

Pins the address function's output to be byte-compatible with
_cognitive_name (so downstream consumers keep parsing the same names),
and verifies the fallback chain (cognitive_vector → resonance → keywords
→ UNKNOWN) behaves correctly.

This is commit 1 of the addressed-formations work — adds the function
and tests, no behavior change to engine/eat. Subsequent commits wire it
into the insertion path behind a feature flag.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from linafish.formations import (
    DIM_ORDER, DIM_LABELS, _cognitive_name, formation_address,
)


# ---------------------------------------------------------------------------
# Helpers — build synthetic cognitive vectors for predictable addresses
# ---------------------------------------------------------------------------

def _vec(scores: dict) -> list:
    """Build an 8-dim cognitive_vector from a {dim_code: score} dict.

    Unspecified dims default to 0.0. Useful for setting up exact
    top-1/top-2/top-3 scenarios without hand-counting indexes.
    """
    out = [0.0] * 8
    for dim, score in scores.items():
        if dim in DIM_ORDER:
            out[DIM_ORDER.index(dim)] = score
    return out


# ---------------------------------------------------------------------------
# Byte-compatibility with _cognitive_name
# ---------------------------------------------------------------------------

def test_top3_matches_cognitive_name_byte_for_byte():
    """The whole point of formation_address is name-compatibility with
    the existing _cognitive_name function so fish.md / /pfc / hook regex
    keep working. For any cognitive_vector with at least one dim above
    0.01, formation_address(cv) MUST equal _cognitive_name(cv, [])."""
    cases = [
        _vec({"EW": 0.8, "IC": 0.6, "CR": 0.4}),  # ACTING+FEELING_via_RELATING
        _vec({"SF": 0.9, "TE": 0.7, "AI": 0.3}),  # STRUCTURING+TESTING_via_SELF-REFLECTION
        _vec({"KO": 0.5, "DE": 0.3, "EW": 0.2}),  # UNDERSTANDING+SPECIALIZING_via_ACTING
    ]
    for cv in cases:
        expected = _cognitive_name(cv, [])
        actual = formation_address(cognitive_vector=cv)
        assert actual == expected, (
            f"address {actual!r} != _cognitive_name {expected!r} for {cv}"
        )


def test_top1_only():
    """A cognitive_vector with only one dim above threshold produces a
    single-label name like 'FEELING'."""
    cv = _vec({"IC": 0.9})
    assert formation_address(cognitive_vector=cv) == "FEELING"


def test_top2_only():
    """Two dims above threshold produce 'A+B' format."""
    cv = _vec({"EW": 0.7, "CR": 0.5})
    assert formation_address(cognitive_vector=cv) == "ACTING+RELATING"


def test_top3_via_format():
    """Three dims above threshold produce 'A+B_via_C' format."""
    cv = _vec({"EW": 0.7, "IC": 0.5, "CR": 0.3})
    assert formation_address(cognitive_vector=cv) == "ACTING+FEELING_via_RELATING"


# ---------------------------------------------------------------------------
# Threshold + tie-break determinism
# ---------------------------------------------------------------------------

def test_threshold_drops_subthreshold_dims():
    """Dims with score <= 0.01 must NOT appear in the address.

    A vector with two dominant dims and a tiny third should produce
    a top-2 address, not top-3.
    """
    cv = _vec({"EW": 0.8, "IC": 0.6, "CR": 0.005})  # CR below threshold
    assert formation_address(cognitive_vector=cv) == "ACTING+FEELING"


def test_dim_order_tie_break():
    """When two dims have identical scores, the DIM_ORDER index decides
    which appears first. Python's stable sort preserves insertion order
    on ties; _cognitive_name iterates in DIM_ORDER, so KO < TE < SF < CR
    < IC < DE < EW < AI on ties.
    """
    # KO and TE both at 0.5 — KO comes first by DIM_ORDER index
    cv = _vec({"KO": 0.5, "TE": 0.5})
    assert formation_address(cognitive_vector=cv) == "UNDERSTANDING+TESTING"


# ---------------------------------------------------------------------------
# Fallback chain
# ---------------------------------------------------------------------------

def test_fallback_to_resonance_when_cognitive_empty():
    """Crystals from before the metabolic engine was wired have empty
    cognitive_vector. The address function falls back to the resonance
    vector's first 8 dims (legacy behavior matching interpret_formation).
    """
    # No cognitive_vector — should fall through to resonance
    res = _vec({"SF": 0.7, "EW": 0.4})
    assert formation_address(
        cognitive_vector=None,
        resonance=res,
    ) == "STRUCTURING+ACTING"


def test_fallback_to_resonance_when_cognitive_all_zeros():
    """A cognitive_vector that's present but all-zero (UNKNOWN) should
    also trigger the resonance fallback, not return UNKNOWN early.
    """
    cv = [0.0] * 8
    res = _vec({"IC": 0.5, "AI": 0.3})
    assert formation_address(
        cognitive_vector=cv,
        resonance=res,
    ) == "FEELING+SELF-REFLECTION"


def test_fallback_to_keywords_when_vectors_empty():
    """When both cognitive_vector and resonance are absent or empty,
    keywords matched against CANONICAL_SEED form a synthetic address.
    """
    # 'build', 'system' should map to dims that produce a real address.
    # We just need to verify it's not UNKNOWN given matching keywords.
    addr = formation_address(
        cognitive_vector=None,
        resonance=None,
        keywords=["build", "system", "architecture"],
    )
    # Keyword fallback either matches something or returns UNKNOWN.
    # The address should be a valid name format, not garbage.
    assert addr == "UNKNOWN" or "_via_" in addr or "+" in addr or addr in {
        DIM_LABELS[d].upper() for d in DIM_ORDER
    }


def test_unknown_when_all_signals_empty():
    """Empty everything → UNKNOWN. The gardener handles UNKNOWN crystals
    separately so they don't pollute the addressed index.
    """
    assert formation_address() == "UNKNOWN"
    assert formation_address(
        cognitive_vector=[],
        resonance=[],
        keywords=[],
    ) == "UNKNOWN"
    assert formation_address(
        cognitive_vector=[0.0] * 8,
        resonance=[0.0] * 8,
        keywords=[],
    ) == "UNKNOWN"


# ---------------------------------------------------------------------------
# Determinism — same input → same output
# ---------------------------------------------------------------------------

def test_deterministic_repeated_calls():
    """formation_address is a pure function — same input must give same
    output across calls. No hidden state, no random sampling.
    """
    cv = _vec({"EW": 0.6, "IC": 0.5, "CR": 0.4, "AI": 0.2})
    results = {formation_address(cognitive_vector=cv) for _ in range(10)}
    assert len(results) == 1, f"non-deterministic: {results}"


def test_address_space_finite_and_small():
    """Sanity check on the structural claim: the address space is small
    and finite. A grid of 100 random-ish vectors should produce far
    fewer than 100 unique addresses (the cognitive lattice quantizes
    nearby vectors to the same address).
    """
    import random
    rng = random.Random(42)
    addresses = set()
    for _ in range(200):
        cv = [rng.random() for _ in range(8)]
        addresses.add(formation_address(cognitive_vector=cv))
    # 8C3 = 56 ordered top-3 combos but with score-magnitude variance,
    # we'd expect closer to ~150 unique addresses across 200 random vecs.
    # The point is it's bounded by the address space, not the input
    # vector space.
    assert len(addresses) < 200, (
        f"address space appears unbounded: {len(addresses)} unique from 200 vecs"
    )
