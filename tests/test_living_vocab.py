"""Tests for the living-vocabulary feature (Phases 1-3)."""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from linafish.crystallizer_v3 import MIVectorizer
from linafish.engine import FishEngine


def _vectorizer(texts):
    v = MIVectorizer()
    for t in texts:
        v.feed(t)
    return v


# Eight docs, each introducing one unique 4-letter token exactly once.
# All eight tokens tie on frequency and doc-frequency, so their scores
# are identical — the tie-break decides their order.
_TIE_DOCS = [
    "the token wordd appears here in a sentence of plain words",
    "the token wordh appears here in a sentence of plain words",
    "the token wordb appears here in a sentence of plain words",
    "the token wordf appears here in a sentence of plain words",
    "the token worda appears here in a sentence of plain words",
    "the token wordg appears here in a sentence of plain words",
    "the token wordc appears here in a sentence of plain words",
    "the token worde appears here in a sentence of plain words",
]


def test_get_vocab_is_order_independent():
    """Same texts fed in opposite order must yield identical vocab."""
    forward = _vectorizer(_TIE_DOCS)
    reverse = _vectorizer(list(reversed(_TIE_DOCS)))
    assert forward.get_vocab(size=20, d=4.0) == reverse.get_vocab(size=20, d=4.0)


def test_extend_vocab_preserves_positions_and_appends():
    """extend_vocab keeps current terms at their indices, appends new ones."""
    v = _vectorizer(_TIE_DOCS)
    current = ["worda", "wordb", "wordc"]
    extended = v.extend_vocab(current, size=20, d=4.0)
    # Existing terms unchanged, at the same indices (prefix preserved).
    assert extended[:3] == ["worda", "wordb", "wordc"]
    # New qualifying terms appended after the prefix.
    assert set(extended[3:]) == set(v.get_vocab(size=20, d=4.0)) - set(current)
    # No term appears twice.
    assert len(extended) == len(set(extended))


def test_extend_vocab_from_empty_equals_get_vocab():
    """With an empty current vocab, extend_vocab == get_vocab (first eat)."""
    v = _vectorizer(_TIE_DOCS)
    assert v.extend_vocab([], size=20, d=4.0) == v.get_vocab(size=20, d=4.0)
