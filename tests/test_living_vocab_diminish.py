"""Tests for living-vocabulary Phase 5 — diminish (recency decay + compaction)."""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from linafish.crystallizer_v3 import MIVectorizer, gamma
from linafish.engine import FishEngine


def _make_engine(state_dir, **kw):
    return FishEngine(state_dir=Path(state_dir), name="testfish",
                      git_autocommit=False, **kw)


def test_feed_stamps_token_last_doc():
    """feed() records, per token, the doc index when it was last seen."""
    v = MIVectorizer()
    v.feed("alpha bravo charlie delta echo")     # doc 1
    v.feed("alpha foxtrot golf hotel india")     # doc 2 — alpha again
    v.feed("juliet kilo lima mike november")     # doc 3
    assert v.doc_count == 3
    assert v.token_last_doc["alpha"] == 2    # last seen doc 2
    assert v.token_last_doc["bravo"] == 1    # only in doc 1
    assert v.token_last_doc["juliet"] == 3   # only in doc 3


def test_token_last_doc_persists():
    """token_last_doc round-trips through save()/load()."""
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "mi_vectorizer.json")
        v = MIVectorizer()
        v.feed("alpha bravo charlie delta echo")
        v.feed("alpha foxtrot golf hotel india")
        v.save(path)
        v2 = MIVectorizer()
        v2.load(path)
        assert v2.token_last_doc == v.token_last_doc
        assert v2.token_last_doc["alpha"] == 2


def test_load_missing_token_last_doc_is_empty():
    """An old mi_vectorizer.json without the key loads cleanly (back-compat)."""
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "mi_vectorizer.json")
        import json
        json.dump({"token_counts": {"alpha": 3}, "pair_counts": {},
                   "doc_count": 1, "token_doc_counts": {"alpha": 1}},
                  open(path, "w"))
        v = MIVectorizer()
        v.load(path)
        assert v.token_last_doc == {}


def test_recency_factor_decays_with_staleness():
    """_recency_factor halves per half-life of staleness; off when half_life is None."""
    v = MIVectorizer()
    v.feed("alpha bravo charlie")             # doc 1
    for _ in range(9):
        v.feed("delta echo foxtrot")          # docs 2-10
    # alpha last seen doc 1, doc_count now 10 -> staleness 9
    assert v._recency_factor("alpha", None) == 1.0      # off
    assert v._recency_factor("alpha", 0) == 1.0         # off
    assert abs(v._recency_factor("alpha", 9) - 0.5) < 1e-9   # one half-life
    assert v._recency_factor("delta", 9) == 1.0         # staleness 0
    assert v._recency_factor("neverseen", 9) == 1.0     # unknown -> no decay


# 'obsolete' is hammered in the first 3 docs, then never again.
# 'current' is hammered in the last 12. 'matter/signal/pattern' are in
# all 15. All clear the blend-mode filters (len>=3, not stopwords).
def _decay_vectorizer():
    v = MIVectorizer()
    for _ in range(3):
        v.feed("obsolete obsolete obsolete matter signal pattern")
    for _ in range(12):
        v.feed("current current current matter signal pattern")
    return v


def test_get_vocab_recency_decay_reranks_stale_below_recent():
    """With decay on, a stale frequent term ranks below a recent one."""
    v = _decay_vectorizer()
    plain = v.get_vocab(size=50, d=4.0)
    decayed = v.get_vocab(size=50, d=4.0, recency_half_life=2)
    assert "obsolete" in plain and "current" in plain
    assert "obsolete" in decayed and "current" in decayed
    # 'obsolete' (staleness 12, 2-doc half-life) is crushed and must
    # fall below 'current' (staleness 0) once decay is applied.
    assert decayed.index("current") < decayed.index("obsolete")


def test_get_vocab_no_decay_is_unchanged():
    """recency_half_life=None leaves get_vocab identical (back-compat)."""
    v = _decay_vectorizer()
    assert (v.get_vocab(size=50, d=4.0)
            == v.get_vocab(size=50, d=4.0, recency_half_life=None))


# --- d-mode-robust corpora -------------------------------------------------
# A fish auto-assesses its `d`; at d>5 get_vocab runs in "stranger" mode,
# which drops any term appearing in >50% of docs. So a test that wants a
# term to SURVIVE compaction must keep that term's doc-frequency well
# under 50% — then recency is the only thing that separates terms, in
# every d-mode. 'matter signal pattern' pad each doc so eats crystallize;
# the pads are ubiquitous and may be filtered in stranger mode — fine,
# no test asserts on them.

_STALE_WORDS = ["aardvark", "beetle", "cobalt", "dolphin", "ember",
                "fjord", "granite", "harbor", "ivory", "jasmine",
                "kelp", "lichen", "marble", "nutmeg", "opal",
                "pewter", "quartz", "raven"]


def _feed_rerank_corpus(engine):
    """20 eats. 'fadeword' (4x/doc) is hammered in eats 1-5 then never
    again; 'freshword' (2x/doc) in eats 16-20. Both reach doc-frequency
    5 (5/20 = 0.25 — eligible in every d-mode). 'fadeword' has the
    higher raw frequency, so without recency decay it ranks ABOVE
    'freshword'; only recency can flip them."""
    for i in range(20):
        if i < 5:
            mark = "fadeword fadeword fadeword fadeword"
        elif i >= 15:
            mark = "freshword freshword"
        else:
            mark = "middle middle"
        engine.eat(f"{mark} matter signal pattern", source="t")


def _feed_shrink_corpus(engine):
    """24 eats. Each of the first 18 carries a unique stale word (one
    doc each — doc-frequency 1); the last 6 carry the recurring
    'freshword' (doc-frequency 6 of 24). Every distinctive term stays
    under the 50% stranger-mode ubiquity cutoff. The living vocab grows
    well past a small vocab_size; compaction must drop the stale ones."""
    for word in _STALE_WORDS:
        engine.eat(f"{word} {word} {word} matter signal pattern", source="t")
    for _ in range(6):
        engine.eat("freshword freshword freshword matter signal pattern", source="t")


def test_revectorize_all_recency_half_life_demotes_stale_term():
    """revectorize_all(recency_half_life=H) demotes a stale term below a
    recent one — even though the stale term has the higher raw frequency."""
    with tempfile.TemporaryDirectory() as tmp:
        e = _make_engine(tmp, living_vocab=True)
        _feed_rerank_corpus(e)
        # No decay: 'fadeword' (freq 20) outranks 'freshword' (freq 10).
        plain = e.revectorize_all()
        assert "vocab_size_before" in plain
        vp = e.fish.vocab
        assert "fadeword" in vp and "freshword" in vp
        assert vp.index("fadeword") < vp.index("freshword")
        # 3-doc half-life: 'fadeword' (staleness 15) is crushed below
        # 'freshword' (staleness 0).
        e.revectorize_all(recency_half_life=3)
        vd = e.fish.vocab
        assert vd.index("freshword") < vd.index("fadeword")
