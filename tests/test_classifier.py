"""Tests for linafish.classifier — turn-level deposit gating.

Ported from a chat-ui sidecar during the 1.4 omnibus port. The
generic-defaults change means tests that depended on author-specific
defaults now supply those tokens explicitly — the same shape the
chat-ui code did, but now opt-in rather than hardcoded. The tokens
below are generic example fixtures; the shipped defaults are empty.
"""
from __future__ import annotations

from linafish.classifier import (
    DEFAULT_DOCTRINE_MARKERS,
    DEPOSIT_THRESHOLD,
    DepositDecision,
    classify,
)


# Helpful constants for tests that want to mimic the original chat-ui
# defaults (so the behavior is regression-tested against the seed source).
# Generic example tokens — the real product ships these empty.
HVT_TEST_DEFAULTS = [
    "lumen",
    "vega",
    "topic-a",
    "topic-b",
    "topic-c",
    "topic-d",
    "topic-e",
]
ROUTING_TEST_DEFAULTS = {
    # Order matters — later wins (dict iteration order). Peer last so
    # a vega+owner co-mention routes peer, matching the chat-ui behavior.
    "owner": [r"\b(owner|chief)\b"],
    "peer": [r"\b(vega|ally|peer)\b"],
}


def test_low_density_skips():
    """Trivial chitchat scores below threshold and skips deposit."""
    d = classify("hi", "hi back")
    assert d.deposit is False
    assert d.target_fish == "skip"
    assert d.score < DEPOSIT_THRESHOLD


def test_weather_skips():
    """Practical-but-low-signal turns skip."""
    d = classify("what's the weather?", "72 in the office.")
    assert d.deposit is False
    assert d.target_fish == "skip"


def test_doctrine_marker_deposits():
    """A 'from now on' phrase trips the doctrine marker and deposits."""
    user = "from now on never use the legacy path — it is deprecated"
    assistant = "Got it. Legacy path is off. Locked."
    d = classify(user, assistant)
    assert d.deposit is True
    assert d.target_fish == "linafish"  # default target name
    assert d.score >= 2.0
    assert any("doctrine-marker" in r for r in d.reasons)


def test_section_tag_deposits():
    """A §SECTION.TAG triggers the doctrine marker."""
    user = "what did we decide?"
    assistant = "§NEW.DOCTRINE landed: validate all input."
    d = classify(user, assistant)
    assert d.deposit is True
    assert d.score >= 2.0


def test_hvt_with_section_marker_routes_peer():
    """An HVT + a § marker clears threshold and routes peer when HVT+routing supplied."""
    user = "what did vega say in the last exchange?"
    assistant = "The last exchange landed at #345 — it acked §4.2. The doctrine moved."
    d = classify(
        user, assistant,
        high_value_tokens=HVT_TEST_DEFAULTS,
        routing_tags=ROUTING_TEST_DEFAULTS,
    )
    assert d.deposit is True, "hvt + § + doctrine should clear threshold"
    assert d.routing_tag == "peer"
    assert any("routing_tag:peer" in r for r in d.reasons)


def test_bare_hvt_mention_does_not_deposit():
    """A brief mention of a single HVT alone (1.0) is below threshold — by design."""
    user = "vega online?"
    assistant = "Yes."
    d = classify(
        user, assistant,
        high_value_tokens=HVT_TEST_DEFAULTS,
        routing_tags=ROUTING_TEST_DEFAULTS,
    )
    assert d.deposit is False, (
        "bare HVT mention should not auto-deposit; threshold protects "
        "the corpus from low-density per-message pollution"
    )
    assert d.routing_tag == "peer", "tag still attached even when skipping"


def test_owner_mention_routes_owner_tag_word_boundary():
    """Owner word-boundary match — 'you' alone does NOT trigger owner tag."""
    user = "owner wants the phase-6 plan tightened."
    assistant = "Reading the spec now, will surface edits."
    d = classify(user, assistant, routing_tags=ROUTING_TEST_DEFAULTS)
    assert d.routing_tag == "owner"


def test_you_alone_does_not_trigger_owner_tag():
    """Word 'you' must not promote routing_tag to owner — that was the original bug."""
    user = "could you do this?"
    assistant = "yes."
    d = classify(user, assistant, routing_tags=ROUTING_TEST_DEFAULTS)
    assert d.routing_tag == "ambient", (
        "v1 fix: 'you' alone must NOT route to owner"
    )


def test_length_bonus_alone_does_not_deposit():
    """Length > 1000 alone scores 0.5, below threshold."""
    long_response = "x" * 1500
    d = classify("a question", long_response)
    assert d.score == 0.5
    assert d.deposit is False


def test_doctrine_plus_length_deposits():
    """Doctrine marker (2.0) + length bonus (0.5) = 2.5, deposits."""
    user = "from now on, always validate input"
    assistant = "x" * 1500
    d = classify(user, assistant)
    assert d.score >= 2.0
    assert d.deposit is True


def test_two_hvt_hits_deposit_at_threshold():
    """Two HVT hits = 2.0, clears 1.5 threshold."""
    user = "lumen and topic-b come up in chapter 3"
    assistant = "noted, the parallel is structural."
    d = classify(user, assistant, high_value_tokens=HVT_TEST_DEFAULTS)
    assert d.score >= 2.0
    assert d.deposit is True


def test_generic_defaults_have_no_hvts():
    """Default HVT list ships empty — author-specific tokens are opt-in."""
    from linafish.classifier import DEFAULT_HIGH_VALUE_TOKENS
    assert DEFAULT_HIGH_VALUE_TOKENS == []


def test_generic_defaults_have_no_routing_tags():
    """Default routing tags ship empty — author-specific routing is opt-in."""
    from linafish.classifier import DEFAULT_ROUTING_TAGS
    assert DEFAULT_ROUTING_TAGS == {}


def test_default_target_fish_name():
    """Default target_fish is 'linafish', not a specific corpus name (generalization)."""
    user = "from now on always validate"
    assistant = "ok"
    d = classify(user, assistant)
    assert d.target_fish == "linafish"


def test_custom_target_fish_name():
    """target_fish_name flows through to deposit decision."""
    user = "from now on always validate"
    assistant = "ok"
    d = classify(user, assistant, target_fish_name="my-corpus")
    assert d.target_fish == "my-corpus"


def test_custom_threshold():
    """Custom threshold can gate deposit-vs-skip."""
    user = "vega online?"
    assistant = "Yes."
    # With HVT supplied, score = 1.0 (one hit). Default threshold 1.5 → skip.
    d_default = classify(user, assistant, high_value_tokens=HVT_TEST_DEFAULTS)
    assert d_default.deposit is False
    # With threshold lowered to 0.9, same input → deposit.
    d_loose = classify(
        user, assistant,
        high_value_tokens=HVT_TEST_DEFAULTS,
        deposit_threshold=0.9,
    )
    assert d_loose.deposit is True
