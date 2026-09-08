"""The gate must be on the path the product runs — `linafish listen` -> FishListener.feed().

2026-09-08: the heartbeat guard and the habituation gate were first put in daemon.py (the
`room` verb). `linafish listen mqtt://…` — the verb in the README, the one Olorina's nodes
run — goes through listener.FishListener, a different file. A guard on the wrong path is no
guard. These tests drive the real listener feed path with no broker, both ways.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from linafish.engine import FishEngine
from linafish.listener import FishListener


def _warm(engine):
    for i in range(12):
        engine.eat(f"the river carries the lantern past the willow and the otter at dusk {i}", source="warm")


def test_listen_refuses_repeats_and_heartbeats_and_writes_thoughts(tmp_path, capsys):
    eng = FishEngine(state_dir=tmp_path, name="listen", git_autocommit=False)
    _warm(eng)
    fl = FishListener(eng)
    before = len(eng.fish.crystals)
    fl.feed("T^keeper|alive|2026-09-08", source="mqtt://bot/fish")               # heartbeat
    for i in range(40):                                                          # a status stream
        fl.feed(f"STATUS cpu 12 pct mem 41 pct net 3 kbs tick {i} all services nominal ok", source="mqtt://bot/conv")
    thoughts = ["what she said at the harbor that evening changed how I read the whole year",
                "the otter went under the willow and did not come back up until the lantern was lit",
                "a stone in the water is a record of every current that failed to move it"]
    for th in thoughts:
        fl.feed(th, source="mqtt://captain/conv")
    added = len(eng.fish.crystals) - before
    assert fl._refused["heartbeat"] == 1
    assert fl._refused["habituated"] >= 20, fl._refused
    assert len(thoughts) <= added < 44, (added, fl._refused)
    eps = {getattr(c, "episode_id", None) for c in eng.fish.crystals[before:]}
    assert None not in eps and any(str(e).startswith("mqtt://captain") for e in eps), eps
    assert "refused this session" in fl.refusal_summary()


def test_listen_gate_can_be_switched_off_by_env(tmp_path, monkeypatch):
    monkeypatch.setenv("LINAFISH_HABITUATION", "off")
    eng = FishEngine(state_dir=tmp_path, name="open", git_autocommit=False)
    _warm(eng)
    fl = FishListener(eng)
    before = len(eng.fish.crystals)
    for i in range(15):
        fl.feed(f"STATUS cpu 12 pct mem 41 pct net 3 kbs tick {i} all services nominal ok", source="mqtt://bot/conv")
    assert fl._refused["habituated"] == 0
    assert len(eng.fish.crystals) - before >= 10


def test_ceiling_is_reachable_from_the_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("LINAFISH_MAX_CRYSTALS", "3")
    eng = FishEngine(state_dir=tmp_path, name="capped", git_autocommit=False)
    assert eng.max_crystals == 3
    results = [eng.eat(f"a distinct thought about the harbor number {i} worth keeping", source="t") for i in range(5)]
    assert results[-1]["reason"] == "ceiling" and len(eng.fish.crystals) == 3
    monkeypatch.delenv("LINAFISH_MAX_CRYSTALS")
    assert FishEngine(state_dir=tmp_path / "b", name="open", git_autocommit=False).max_crystals is None
