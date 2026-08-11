"""M1 Phase 2 — the grounding verdict.

grounding.verdict() grades a taste query by how much co-occurrence
evidence the vectorizer actually holds for it: grounded (real evidence),
thin (some), ungrounded (none) — with a recency lift to 'thin-recent'
when the fish only just learned the thing.

Cases (a)-(d) use a SYNTHETIC vectorizer stub (plain doc_count /
token_doc_counts / pair_counts) so the math is exercised in isolation,
independent of the real MIVectorizer's co-occurrence internals. Case (e)
is a light integration smoke test through the real FishEngine.
"""

from pathlib import Path

from linafish.grounding import informative_tokens, pair_evidence, verdict


class StubVectorizer:
    """Just enough surface for grounding.py: doc_count, token_doc_counts,
    pair_counts. No tokenizer, no MI math — grounding.py doesn't need it."""

    def __init__(self, doc_count, token_doc_counts, pair_counts):
        self.doc_count = doc_count
        self.token_doc_counts = dict(token_doc_counts)
        self.pair_counts = dict(pair_counts)


# ---------------------------------------------------------------------------
# (a) known-pair query -> grounded
# ---------------------------------------------------------------------------

def test_known_pair_query_is_grounded():
    vec = StubVectorizer(
        doc_count=100,
        token_doc_counts={"gizmo": 2, "captain": 2},
        pair_counts={"gizmo|captain": 10},
    )
    v = verdict("gizmo captain", vec)
    assert v["band"] == "grounded"
    assert v["max_evidence"] > 1.30
    assert v["evidence"], "known pair must surface in the evidence list"
    a, b, count = v["evidence"][0]
    assert {a, b} == {"gizmo", "captain"}
    assert count == 10


# ---------------------------------------------------------------------------
# (b) zero-pair query -> ungrounded, unknown_pairs named
# ---------------------------------------------------------------------------

def test_zero_pair_query_is_ungrounded_and_names_the_pair():
    vec = StubVectorizer(
        doc_count=100,
        token_doc_counts={"phoenix": 1, "olorina": 1},
        pair_counts={},  # never co-occurred
    )
    v = verdict("phoenix olorina", vec)
    assert v["band"] == "ungrounded"
    assert v["max_evidence"] < 0.25
    assert not v["evidence"]
    assert v["unknown_pairs"], "a zero-count pair of known tokens must be named"
    a, b = v["unknown_pairs"][0]
    assert {a, b} == {"phoenix", "olorina"}


# ---------------------------------------------------------------------------
# (c) short known token survives ('q')
# ---------------------------------------------------------------------------

def test_short_known_token_kept():
    vec = StubVectorizer(
        doc_count=50,
        token_doc_counts={"q": 5},
        pair_counts={},
    )
    tokens = informative_tokens("ask q now", vec)
    assert "q" in tokens
    # "ask"/"now" are <4 chars and unknown to the vectorizer -> dropped.
    assert "ask" not in tokens
    assert "now" not in tokens


def test_unknown_short_token_dropped():
    vec = StubVectorizer(doc_count=10, token_doc_counts={}, pair_counts={})
    tokens = informative_tokens("hi ok go", vec)
    assert tokens == []


def test_stopword_excluded_even_when_long_enough():
    vec = StubVectorizer(doc_count=10, token_doc_counts={}, pair_counts={})
    tokens = informative_tokens("with about there gizmo", vec)
    assert tokens == ["gizmo"]


# ---------------------------------------------------------------------------
# (d) recency lift: ungrounded -> thin-recent
# ---------------------------------------------------------------------------

def test_recency_lifts_ungrounded_to_thin_recent():
    vec = StubVectorizer(
        doc_count=100,
        token_doc_counts={"phoenix": 1, "olorina": 1},
        pair_counts={},
    )
    v_no_recent = verdict("phoenix olorina", vec, recent_texts=None)
    assert v_no_recent["band"] == "ungrounded"

    v_recent = verdict(
        "phoenix olorina", vec,
        recent_texts=["phoenix and olorina wrote to each other today"],
    )
    assert v_recent["band"] == "thin-recent"
    assert v_recent["recent_support"] >= 0.5


def test_recency_does_not_lift_when_coverage_is_below_half():
    vec = StubVectorizer(
        doc_count=100,
        token_doc_counts={"phoenix": 1, "olorina": 1, "anchor": 1},
        pair_counts={},
    )
    # Three informative tokens, only one covered -> 1/3 < 0.5, no lift.
    v = verdict(
        "phoenix olorina anchor", vec,
        recent_texts=["phoenix showed up somewhere unrelated"],
    )
    assert v["band"] == "ungrounded"
    assert 0.0 < v["recent_support"] < 0.5


# ---------------------------------------------------------------------------
# pair_evidence directly — key-order tolerance
# ---------------------------------------------------------------------------

def test_pair_evidence_tries_both_key_orders():
    vec = StubVectorizer(
        doc_count=100,
        token_doc_counts={"alpha": 3, "beta": 3},
        pair_counts={"beta|alpha": 7},  # reversed order on disk
    )
    pairs = pair_evidence(["alpha", "beta"], vec)
    assert len(pairs) == 1
    a, b, count, evidence = pairs[0]
    assert count == 7
    assert evidence > 0


def test_pair_evidence_tuple_keys_like_real_vectorizer():
    vec = StubVectorizer(
        doc_count=100,
        token_doc_counts={"alpha": 3, "beta": 3},
        pair_counts={("alpha", "beta"): 4},
    )
    pairs = pair_evidence(["alpha", "beta"], vec)
    assert pairs[0][2] == 4


# ---------------------------------------------------------------------------
# (e) taste_dict integration smoke — real FishEngine
# ---------------------------------------------------------------------------

def test_taste_dict_carries_a_grounding_verdict(tmp_path: Path):
    from linafish.engine import FishEngine

    e = FishEngine(name="grounding-probe", state_dir=tmp_path)
    e.eat("Gizmo the captain built the fish out of pure ache and math.", source="seed")
    e.eat("Ache conserves. It only redistributes across the whole system.", source="seed")
    e.eat("The captain and gizmo tuned the vectorizer together.", source="seed")

    result = e.taste_dict("gizmo captain")
    assert result["ok"] is True
    assert "grounding" in result, "taste_dict must carry the additive grounding field"
    g = result["grounding"]
    assert g["band"] in ("grounded", "thin", "thin-recent", "ungrounded", "error")
    assert "max_evidence" in g and "mean_evidence" in g
    assert "evidence" in g and "unknown_pairs" in g and "recent_support" in g

    # Existing fields must be untouched by the addition.
    assert set(result.keys()) >= {
        "ok", "query_keywords", "match_count", "total_crystals", "matches", "grounding",
    }


def test_taste_dict_early_return_paths_have_no_grounding_field():
    from linafish.engine import FishEngine
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        e = FishEngine(name="empty-probe", state_dir=Path(d))
        result = e.taste_dict("anything at all")
        assert result["ok"] is False
        assert result["reason"] == "empty_fish"
        assert "grounding" not in result, (
            "grounding must only attach after the ok/matches logic — "
            "early-return paths are untouched by spec"
        )
