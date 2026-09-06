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

STEADY = ["river", "willow", "otter", "water", "boat", "bank", "stone", "morning",
          "evening", "lantern", "harbor", "meadow"]


def _steady_doc(i):
    # every doc carries 'river'; the rest rotate so lifetime df is spread evenly
    a, b, c = STEADY[i % 12], STEADY[(i * 5) % 12], STEADY[(i * 7) % 12]
    return f"the river runs past the {a} while the {b} waits near the {c} at dusk {i}"


def _vectorizer(n_steady=400, burst=12, burst_word="zorbification", track=True):
    v = MIVectorizer()
    v.track_emergence = track
    for i in range(n_steady):
        v.feed(_steady_doc(i))
    v.feed("the river carries a fragment deadbeefcafe once and never again")
    for i in range(burst):
        v.feed(f"the {burst_word} of the river was noted again in the record {i}")
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
            e.eat(f"the zorbification of the river was noted again in the record {i}")
        assert "zorbification" in e.fish.vocab, (
            f"emerging door did not admit; vocab {len(before)} -> {len(e.fish.vocab)}")
        assert e.fish.vocab[:len(before)] == before


def test_non_living_engine_never_admits_via_emerging_door():
    with tempfile.TemporaryDirectory() as tmp:
        e = _engine(tmp, living=False)
        assert e.fish.vectorizer.track_emergence is False
        for i in range(12):
            e.eat(f"the zorbification of the river was noted again in the record {i}")
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
