"""exp/sparse-key: the crystal's own terms are the retrieval key (docs/sparse-key-seed.md).

What these tests pin: (1) a one-word query finds the crystal that holds the word — the dense key returned zero
candidates for a full name plus a date against 2,032 crystals holding it; (2) a query with no known term is a loud
nothing, not a confident wrong list; (3) the engine's taste_sparse keeps taste_dict's schema and extends the index
with the tail after an eat without any hook; (4) the env route sends taste_dict through it; (5) the sparse route carries the same grounding band as the
dense one, marked route=sparse — never "unscored" (2026-10-18).
"""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from linafish.sparse import SparseIndex, default_tokenize  # noqa: E402
from linafish.engine import FishEngine  # noqa: E402


DOCS = [
    "The river carried the lantern downstream past the old mill while the teacher wrote about memory.",
    "Caroline walked the ridge at dawn; the lantern in her hand did not dim.",
    "A compression protocol carries more with less: the key is small, the body is whole.",
    "Breakfast was eggs and coffee; the dog came home safe before noon.",
]


def test_one_word_query_finds_its_crystal():
    idx = SparseIndex().build(DOCS)
    ranked = idx.score("Caroline", top=3)
    assert ranked and ranked[0][0] == 1
    assert idx.candidates("Caroline") == 1


def test_unknown_terms_are_a_loud_nothing():
    idx = SparseIndex().build(DOCS)
    assert idx.score("zyxxqw plorf", top=5) == []
    assert idx.query_terms("zyxxqw plorf") == []


def test_rare_terms_outrank_common_ones():
    idx = SparseIndex().build(DOCS)
    # "lantern" is in two docs, "mill" in one: the doc with both wins a query naming both
    ranked = idx.score("lantern mill", top=2)
    assert ranked[0][0] == 0
    assert idx.n_postings == sum(len(set(default_tokenize(d))) for d in DOCS)


def test_engine_taste_sparse_schema_and_tail_growth(monkeypatch):
    with tempfile.TemporaryDirectory() as td:
        e = FishEngine(state_dir=Path(td), name="sparse-test")
        for d in DOCS * 3:                     # enough to freeze
            e.eat(d, source="test")
        r = e.taste_sparse("Caroline at dawn", top=3)
        assert r["ok"] and r["total_crystals"] == len(e.fish.crystals)
        assert {"id", "text", "source", "ts", "relevance", "keywords"} <= set(r["matches"][0])
        assert "caroline" in r["matches"][0]["text"].lower()
        assert r["grounding"]["band"] in ("grounded", "thin", "ungrounded", "thin-recent")
        assert r["grounding"]["route"] == "sparse" and "gamma" in r["grounding"] or r["grounding"]["band"] != "grounded"
        n_before = e._sparse.n_docs
        e.eat("A brand new sentence about a zeppelin over the harbour at midnight.", source="test")
        r2 = e.taste_sparse("zeppelin harbour", top=1)
        assert r2["ok"] and "zeppelin" in r2["matches"][0]["text"]
        assert e._sparse.n_docs == n_before + 1
        # env route: taste_dict becomes the sparse taste
        monkeypatch.setenv("LINAFISH_TASTE_SPARSE", "on")
        r3 = e.taste_dict("zeppelin harbour", top=1)
        assert r3["grounding"]["route"] == "sparse"
        assert r3["grounding"]["band"] != "unscored"
        monkeypatch.delenv("LINAFISH_TASTE_SPARSE")
        r4 = e.taste_dict("zeppelin harbour", top=1)
        assert "route" not in r4.get("grounding", {})          # dense route is unmarked, as before
