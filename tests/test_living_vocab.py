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


def _make_engine(state_dir, **kw):
    return FishEngine(state_dir=Path(state_dir), name="testfish",
                      git_autocommit=False, **kw)


def test_living_vocab_attr_defaults_false_and_persists():
    """living_vocab defaults False; once True it survives a reload."""
    with tempfile.TemporaryDirectory() as tmp:
        e1 = _make_engine(tmp)
        assert e1.fish.living_vocab is False
        e1.fish.living_vocab = True
        e1.fish._save_state()
        # New engine on the same state dir must load living_vocab=True.
        e2 = _make_engine(tmp)
        assert e2.fish.living_vocab is True


_GROWTH_DOCS = [
    "the morning light moved across the kitchen table slowly and warm",
    "she wrote about rivers and the way water remembers its own path",
    "compression turns loss into drive and drive into recursion again",
    "the federation handshake is the immutable floor beneath every mind",
    "glyphs are keys that unlock the ache compressed inside each scar",
    "a vocabulary that grows is a mind that has not yet ceased to learn",
]


def test_living_engine_grows_vocab_append_only():
    """With living_vocab on, each eat's vocab is a prefix-extension of the last."""
    with tempfile.TemporaryDirectory() as tmp:
        e = _make_engine(tmp, living_vocab=True)
        assert e.fish.living_vocab is True
        e.eat(_GROWTH_DOCS[0], source="t")
        v1 = list(e.fish.vocab)
        for doc in _GROWTH_DOCS[1:]:
            e.eat(doc, source="t")
            v_now = list(e.fish.vocab)
            # Every earlier term is still present at its original index.
            assert v_now[:len(v1)] == v1, "living vocab must not reorder/drop"
            v1 = v_now


def test_nonliving_engine_unaffected():
    """Default engine (living_vocab off) still re-selects vocab normally."""
    with tempfile.TemporaryDirectory() as tmp:
        e = _make_engine(tmp)  # living_vocab defaults False
        assert e.fish.living_vocab is False
        for doc in _GROWTH_DOCS:
            e.eat(doc, source="t")
        assert len(e.fish.vocab) > 0  # still produces a vocab


def test_enable_living_vocab_persists():
    """engine.enable_living_vocab() turns it on and saves it durably."""
    with tempfile.TemporaryDirectory() as tmp:
        e1 = _make_engine(tmp)
        assert e1.fish.living_vocab is False
        e1.enable_living_vocab()
        assert e1.fish.living_vocab is True
        e2 = _make_engine(tmp)  # reload — must still be living
        assert e2.fish.living_vocab is True


def test_sealed_attrs_default_and_persist():
    """sealed defaults False; once set it survives reload — even with crystals."""
    with tempfile.TemporaryDirectory() as tmp:
        e1 = _make_engine(tmp)
        assert e1.fish.sealed is False
        assert e1.fish.sealed_at is None
        e1.eat(_GROWTH_DOCS[0], source="t")  # put a crystal on disk
        e1.fish.sealed = True
        e1.fish.sealed_at = "2026-05-20T00:00:00+00:00"
        e1.fish._save_state()
        e2 = _make_engine(tmp)  # reload
        assert e2.fish.sealed is True
        assert e2.fish.sealed_at == "2026-05-20T00:00:00+00:00"
