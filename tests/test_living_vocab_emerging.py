"""§TRADITIONAL.VS.EMERGING — the emerging door for a living vocabulary (linafish#71).

Captain, 2026-09-06: *"this is traditional versus emerging."* get_vocab ranks by lifetime
standing — the traditional door, sized for `size` incumbents. On a mature fish a genuinely
new recurring term never out-ranks them (measured: fed 40x into a 7,353-crystal fish, never
admitted). The emerging door admits a term whose recent-window doc-frequency is out of
proportion to its lifetime rate.

Both ways: the door must ADMIT a burst term, and must REFUSE (a) a steady word however
frequent, (b) a one-off / hex fragment, (c) anything on a non-living fish.
"""
import json
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from linafish.crystallizer_v3 import MIVectorizer
from linafish.engine import FishEngine

# Forty steady content words. With only twelve, a top-20 vocabulary has room for ANY term
# with a pulse and the traditional door admits the burst on its own — which is the case
# these tests are NOT about. A mature fish has a contested top-20.
STEADY = ["river", "willow", "otter", "water", "boat", "bank", "stone", "morning",
          "evening", "lantern", "harbor", "meadow", "bridge", "orchard", "kettle", "ledger",
          "window", "garden", "thunder", "saddle", "candle", "market", "anchor", "compass",
          "hollow", "silver", "copper", "wagon", "barrel", "letter", "mirror", "pasture",
          "shingle", "tallow", "quarry", "furrow", "hearth", "timber", "gutter", "beacon"]


def _steady_doc(i):
    # every doc carries 'river'; the rest rotate so lifetime df is spread evenly
    n = len(STEADY)
    a, b, c, d = STEADY[i % n], STEADY[(i * 7) % n], STEADY[(i * 11) % n], STEADY[(i * 13) % n]
    return f"the river runs past the {a} while the {b} waits near the {c} by the {d} at dusk {i}"


# A REAL burst: the same new term recurring across DIFFERENT sentences, built only from the
# corpus's own common words — so each sentence differs (the engine's gate admits it) while the
# term's co-occurrence partners are the same everyday words as everything else (the traditional
# door does not take it on distinctiveness alone). Twelve copies of one sentence is a repeated
# message, and the engine now refuses those on purpose; a burst of fresh vocabulary around the
# term is a topic shift, which the traditional door admits by itself.
# A REAL burst: the same new term recurring across DIFFERENT sentences. Twelve copies of one
# sentence is a repeated message, and the engine now refuses those on purpose.
VARIED = ["the harbor keeps a ledger of {w} and the tide does not argue",
          "she asked about {w} at dusk and the willow had no answer",
          "a stone remembers every {w} that failed to move it",
          "morning came late to the meadow and brought {w} with it",
          "the otter went under the boat and surfaced beside the {w}",
          "we tested the lantern against {w} until the water went quiet"]


def _burst_doc(w, i):
    # a REAL burst: the same new term recurring across DIFFERENT sentences. Twelve copies of
    # one sentence is a repeated message, and the engine now refuses those on purpose.
    return VARIED[i % len(VARIED)].format(w=w) + f" {i}"


def _vectorizer(n_steady=1200, burst=12, burst_word="zorbification", track=True):
    # 1,200 steady docs: with a VARIED burst, 400 was young enough for the new term to enter
    # the traditional top-20 on co-occurrence alone, which is the case the test is not about.
    v = MIVectorizer()
    v.track_emergence = track
    for i in range(n_steady):
        v.feed(_steady_doc(i))
    v.feed("the river carries a fragment deadbeefcafe once and never again")
    for i in range(burst):
        v.feed(_burst_doc(burst_word, i))
    return v


def test_burst_term_emerges_and_steady_word_does_not():
    v = _vectorizer()
    got = {t: (round(r, 2), round(rec, 1)) for t, r, rec in v.emerging_terms()}
    assert "zorbification" in got, f"burst term not emerging; table={got}"
    ratio, recent = got["zorbification"]
    assert recent >= 5 and ratio >= 3
    # 'river' is in EVERY doc — highest lifetime df in the fish — and is NOT emerging
    assert "river" not in got
    _, river_ratio = v.emergence("river")
    assert river_ratio < 1.5, river_ratio


def test_one_off_fragment_does_not_emerge():
    v = _vectorizer()
    names = {t for t, _, _ in v.emerging_terms()}
    assert "deadbeefcafe" not in names
    recent, _ = v.emergence("deadbeefcafe")
    assert recent < 5


def test_emergence_off_yields_nothing_and_costs_nothing():
    v = _vectorizer(track=False)
    assert v.emerge_df == {}
    assert v.emerging_terms() == []


def test_extend_vocab_emerging_door_is_append_only_and_capped():
    v = _vectorizer()
    current = v.get_vocab(size=20, d=4.0)
    traditional = [t for t in v.get_vocab(size=20, d=4.0) if t not in current]  # == []
    # cap = 1: exactly the top emerging term enters, nothing else
    ext1 = v.extend_vocab(current, size=20, d=4.0, emerging=True, emerge_limit=1)
    assert ext1[:len(current)] == current
    added1 = [t for t in ext1[len(current):] if t not in traditional]
    top = v.emerging_terms(exclude=set(current) | set(traditional), limit=1)
    assert added1 == [top[0][0]], (added1, top)
    # cap = 5: the burst word is in; the prefix is still untouched
    ext5 = v.extend_vocab(current, size=20, d=4.0, emerging=True, emerge_limit=5)
    assert ext5[:len(current)] == current
    assert "zorbification" in ext5
    assert len(ext5) - len(current) - len(traditional) <= 5
    assert len(ext5) == len(set(ext5))


def test_emergence_survives_save_and_load(tmp_path):
    v = _vectorizer()
    data = v.to_dict() if hasattr(v, "to_dict") else None
    if data is None:
        pytest.skip("vectorizer has no to_dict on this build")
    assert data.get("emerge_df"), "emerge_df not persisted"
    v2 = MIVectorizer()
    v2.from_dict(data) if hasattr(v2, "from_dict") else v2.load_dict(data)
    v2.track_emergence = True
    assert v2.emerge_recent("zorbification") == pytest.approx(v.emerge_recent("zorbification"), rel=1e-3)
    assert "zorbification" in {t for t, _, _ in v2.emerging_terms()}


def _engine(tmp, living):
    kw = {"living_vocab": True} if living else {}
    e = FishEngine(state_dir=Path(tmp), name="emerge", git_autocommit=False, **kw)
    for i in range(400):
        e.eat(_steady_doc(i))
    return e


def test_living_engine_admits_burst_term_per_text():
    with tempfile.TemporaryDirectory() as tmp:
        e = _engine(tmp, living=True)
        assert e.fish.vectorizer.track_emergence is True
        before = list(e.fish.vocab)
        assert "zorbification" not in before
        for i in range(12):
            e.eat(_burst_doc("zorbification", i))
        assert "zorbification" in e.fish.vocab, (
            f"emerging door did not admit; vocab {len(before)} -> {len(e.fish.vocab)}")
        assert e.fish.vocab[:len(before)] == before


def test_non_living_engine_never_admits_via_emerging_door():
    with tempfile.TemporaryDirectory() as tmp:
        e = _engine(tmp, living=False)
        assert e.fish.vectorizer.track_emergence is False
        for i in range(12):
            e.eat(_burst_doc("zorbification", i))
        assert e.fish.vectorizer.emerge_df == {}
        # the traditional door may or may not take it on a corpus this small; the
        # emerging door must have contributed nothing
        assert len(e.fish.vocab) <= e.vocab_size


def test_living_flag_from_disk_turns_tracking_on():
    with tempfile.TemporaryDirectory() as tmp:
        e = _engine(tmp, living=True)
        e._save_state()
        e2 = FishEngine(state_dir=Path(tmp), name="emerge", git_autocommit=False)
        assert e2.fish.living_vocab is True
        assert e2.fish.vectorizer.track_emergence is True
        assert e2.fish.vectorizer.emerge_df, "emergence record did not survive the reload"


def test_emergence_clock_survives_an_off_period():
    """Review P1 (2026-09-07): emerge_df used to decay against token_last_doc, which
    advances on every feed whether tracking is on or not. After an off period the decay
    saw a recent `last`, so a burst that had gone quiet read as still rising — measured
    2.2x overstated against an always-on control. With its own clock the off->on ratio
    must land within a small factor of the control. Both ways: the control itself must
    show the burst has faded (ratio < 1.5), or this test proves nothing."""
    def history(v, off_period):
        for i in range(400):
            v.feed(_steady_doc(i))
        for i in range(12):
            v.feed(_burst_doc("zorbification", i))
        return [(_steady_doc(400 + i) + (" zorbification" if i % 40 == 0 else ""))
                for i in range(off_period)]

    # subject: tracking OFF during the quiet period, then ON again
    v = MIVectorizer(); v.track_emergence = True
    tail = history(v, 800)
    v.track_emergence = False
    for d in tail:
        v.feed(d)
    v.track_emergence = True
    _, off_on = v.emergence("zorbification")

    # control: tracking ON throughout the same history
    w = MIVectorizer(); w.track_emergence = True
    for d in history(w, 800):
        w.feed(d)
    _, control = w.emergence("zorbification")

    assert control < 1.5, f"control did not fade: {control}"
    assert off_on <= control * 1.25 + 0.1, (
        f"off->on ratio {off_on:.2f} overstates the always-on control {control:.2f}")


def test_revectorize_keeps_the_emerging_door(tmp_path):
    """Review P1: revectorize_all built a fresh vectorizer with tracking off, so a living
    fish lost its whole emergence record on every revectorize. The re-feed must rebuild it."""
    eng = FishEngine(state_dir=tmp_path, name="revec", living_vocab=True)
    for i in range(60):
        eng.eat(_steady_doc(i), source="t")
    for i in range(12):
        eng.eat(_burst_doc("zorbification", i), source="t")
    assert eng.fish.vectorizer.track_emergence
    before = eng.fish.vectorizer.emerge_recent("zorbification")
    assert before > 0
    eng.revectorize_all(vocab_size=50)
    vec = eng.fish.vectorizer
    assert vec.track_emergence, "revectorize turned the door off"
    assert vec.emerge_recent("zorbification") > 0, "emergence history was wiped by revectorize"
