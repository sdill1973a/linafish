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
