"""Prediction is the gate — proven both ways, 2026-09-08.

Captain: "how does my brain deal with noise?" / "ai are pretty good at predictive math."
The fish writes in proportion to surprise; a stream it can predict is habituated; a spike in
surprise cuts a new episode; what it cannot predict it always writes. Measured first on real
streams (89% of noise refused at floor 0.05, 0% of prose). These tests pin the mechanism.
"""
import json
import os
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest


@pytest.fixture(autouse=True)
def _gate_on(monkeypatch):
    # these tests exercise the gate; it is OPT-IN in the package (see habituation_from_env)
    monkeypatch.setenv("LINAFISH_HABITUATION", "on")

from linafish.habituation import Habituation, cosine
from linafish.daemon import RoomListener


def _v(*xs):
    return list(xs)


def test_repeated_stream_habituates_and_varied_stream_writes():
    h = Habituation(floor=0.05, alpha=0.2)
    same = _v(1.0, 0.0, 0.0, 0.0)
    decisions = [h.observe("bot", same, now=100.0 + i) for i in range(30)]
    assert decisions[0].write and decisions[0].reason == "unpredictable"
    assert not decisions[-1].write and decisions[-1].reason == "habituated"
    assert sum(d.write for d in decisions) <= 3, "a constant stream must stop being written"
    # a varied stream keeps writing
    g = Habituation(floor=0.05, alpha=0.2)
    varied = [_v(1, 0, 0, 0), _v(0, 1, 0, 0), _v(0, 0, 1, 0), _v(0, 0, 0, 1)] * 5
    got = [g.observe("human", v, now=200.0 + i) for i, v in enumerate(varied)]
    assert all(d.write for d in got)


def test_spike_cuts_a_new_episode_and_counts_the_quiet():
    h = Habituation(floor=0.05, alpha=0.2, boundary=0.5)
    for i in range(20):
        h.observe("bot", _v(1, 0, 0, 0), now=300.0 + i)
    st = h.sources["bot"]
    first_episode, quiet = st.episode_id, st.habituated
    assert quiet > 10, "the quiet run must be COUNTED, not lost"
    d = h.observe("bot", _v(0, 0, 0, 1), now=330.0)      # orthogonal: full surprise
    assert d.write and d.reason == "novel" and d.episode_id != first_episode and d.episode_seq == 1


def test_cannot_predict_always_writes_and_off_means_off():
    h = Habituation()
    assert h.observe("x", None, now=1.0).write                 # no vector (no vocab yet)
    assert h.observe("x", _v(0, 0, 0, 0), now=2.0).write       # zero vector
    off = Habituation(enabled=False)
    for i in range(10):
        assert off.observe("bot", _v(1, 0, 0, 0), now=10.0 + i).reason == "off"


def test_state_survives_a_round_trip():
    h = Habituation()
    for i in range(5):
        h.observe("bot", _v(1, 0, 0, 0), now=1.0 + i)
    g = Habituation(); g.load(json.loads(json.dumps(h.to_dict())))
    assert g.sources["bot"].expected == h.sources["bot"].expected
    assert g.sources["bot"].episode_id == h.sources["bot"].episode_id


def test_daemon_refuses_a_repeated_stream_and_stamps_episodes(tmp_path):
    """Through the real listener path (no broker): a warmed fish, 40 identical status
    lines and 6 varied thoughts. Most of the repeats must be refused and counted; the
    thoughts must land, each carrying an episode."""
    rl = RoomListener(fish_name="probe", state_dir=tmp_path)
    # warm the fish so it has a vocabulary to predict with
    for i in range(12):
        rl.engine.eat(f"the river carries the lantern past the willow and the otter at dusk {i}", source="warm")
    def msg(topic, text):
        return types.SimpleNamespace(topic=topic, payload=text.encode("utf-8"))
    before = len(rl.engine.crystals)
    for i in range(40):
        rl._on_message(None, None, msg("bot/conv/anchor", json.dumps({"text": f"STATUS cpu 12 pct mem 41 pct net 3 kbs tick {i} all services nominal ok"})))
    thoughts = ["what she said at the harbor that evening changed how I read the whole year",
                "the otter went under the willow and did not come back up until the lantern was lit",
                "I keep testing the same idea against the river because the river does not flatter",
                "a stone in the water is a record of every current that failed to move it",
                "the morning after the storm the meadow was louder than the harbor",
                "he teaches around corners and the corner is the lesson"]
    for i, th in enumerate(thoughts):
        rl._on_message(None, None, msg("captain/conv/anchor", json.dumps({"text": th})))
    added = len(rl.engine.crystals) - before
    skipped = rl.stats.get("skipped", {})
    assert skipped.get("habituated", 0) >= 20, skipped
    assert added < 46 and added >= len(thoughts), (added, skipped)
    eps = {getattr(c, "episode_id", None) for c in rl.engine.crystals[before:]}
    assert None not in eps and any(e.startswith("captain:") for e in eps), eps


# --- Olorina's review of #84, 2026-09-08: two failures the fixed-vector tests could not reach ---

def test_a_rebased_vocabulary_invalidates_the_prior():
    """The expectation is indexed by vocabulary position. When the fish re-ranks its vocab
    (freeze() re-derives it; epoch increments), an old prior compared against a new-basis
    vector is a confident, meaningless float — and that float is the write/refuse decision,
    silent in both directions. A stale basis must read as 'cannot predict' -> write."""
    h = Habituation(floor=0.05, alpha=0.2)
    same = _v(1.0, 0.0, 0.0, 0.0)
    for i in range(10):
        h.observe("bot", same, now=100.0 + i, basis="epoch-1")
    assert not h.observe("bot", same, now=111.0, basis="epoch-1").write      # habituated, same basis
    d = h.observe("bot", same, now=112.0, basis="epoch-2")                    # basis moved
    assert d.write and d.reason == "unpredictable", d
    assert h.sources["bot"].basis == "epoch-2"


def test_two_cuts_in_the_same_second_get_distinct_episodes():
    h = Habituation(floor=0.05, alpha=0.2, boundary=0.5)
    h.observe("bot", _v(1, 0, 0, 0), now=500.0)
    a = h.observe("bot", _v(0, 1, 0, 0), now=500.0)   # orthogonal -> cut
    b = h.observe("bot", _v(0, 0, 1, 0), now=500.0)   # orthogonal again, same second -> cut
    assert a.write and b.write and a.reason == "novel" and b.reason == "novel"
    assert a.episode_id != b.episode_id, (a.episode_id, b.episode_id)
