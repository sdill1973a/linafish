"""Three stopword-like sets, three jobs — pinned so a change is a decision, not drift.

2026-09-07: a review (Anchor, with Q) filed 'three stopword sets, not nested, tokenization
differs by code path — collapse to one.' Measured before acting: collapsing the vectorizer to
the union would evict 1,004 vocabulary entries across 89 live fish, and the parser's list is
not a filter at all but the 'stop' branch of a part-of-speech guesser in which pronouns and
auxiliaries deliberately carry the relating/acting dimensions. The vectorizer's set is small
because the design's premise is that common positional words ARE the cognitive signal
(docs/vision.md). Three organs, not one drifted list.

So nothing moves. These tests pin the EXACT contents and the one containment that is true
by construction, so that the next reviewer sees a deliberate table rather than an accident,
and so that any edit to any of the three has to touch this file and say why.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from linafish.crystallizer_v3 import STOPWORDS as VECTOR_STRIP
from linafish.grounding import STOPWORDS as GROUNDING_FLOOR
from linafish.parser import _STOPWORDS as POS_STOP_TAG

VECTOR_STRIP_PINNED = frozenset("""
a all an and are at be been but can could for from had has have he her his how in is it
not of on or our she should than that the their them there they this to was we were what
when which who will with would you your
""".split())

POS_STOP_TAG_PINNED = frozenset("""
a also an and as at but in just no not of on or so than that the these this those to too
very
""".split())


def test_vectorizer_strip_list_is_the_minimal_set():
    assert VECTOR_STRIP == VECTOR_STRIP_PINNED, (
        f"vectorizer STOPWORDS changed: +{sorted(VECTOR_STRIP - VECTOR_STRIP_PINNED)} "
        f"-{sorted(VECTOR_STRIP_PINNED - VECTOR_STRIP)}. Adding a word here removes an axis "
        f"from every fish that has it — update the pin and say why in the commit.")


def test_pos_stop_tag_is_the_declared_24():
    assert POS_STOP_TAG == POS_STOP_TAG_PINNED, (
        f"parser _STOPWORDS changed: +{sorted(POS_STOP_TAG - POS_STOP_TAG_PINNED)} "
        f"-{sorted(POS_STOP_TAG_PINNED - POS_STOP_TAG)}. This is a POS tag, not a filter.")


def test_grounding_floor_contains_the_vectorizer_set():
    missing = VECTOR_STRIP - GROUNDING_FLOOR
    assert not missing, f"grounding floor no longer covers the vectorizer set: {sorted(missing)}"
    assert len(GROUNDING_FLOOR) == 102, (
        f"grounding floor is {len(GROUNDING_FLOOR)} words, pinned at 102 — legibility over coverage")


def test_the_pins_can_fail():
    """The organ must be seen to fail: a one-word edit is caught."""
    assert (VECTOR_STRIP | {"zorbification"}) != VECTOR_STRIP_PINNED
    assert (POS_STOP_TAG - {"just"}) != POS_STOP_TAG_PINNED
