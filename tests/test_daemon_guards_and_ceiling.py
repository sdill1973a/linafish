"""Daemon guards and the engine ceiling — proven both ways, 2026-09-08.

Origin: a federation node's fish went from 189 crystals to 117,629 of eaten status tables and
was being OOM-killed (~90 KB per crystal resident). The package daemon had dedup and a
'pulse' downsampler but no heartbeat skip, no visible skip counts, and the engine had no
ceiling at all. Guards ported from the operator's runtime listener (§THE.LISTENER.WAS.ME).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from linafish.daemon import is_heartbeat
from linafish.engine import FishEngine


def test_heartbeat_prefixes_and_markers_are_skipped_and_prose_is_not():
    assert is_heartbeat("T^keeper|alive|2026-09-08T00:00:00")
    assert is_heartbeat("T^boot|cold|ok")
    assert is_heartbeat("status: heartbeat 12:00 all services up")
    assert is_heartbeat("nightly digest reason=session_keeper tick")
    assert not is_heartbeat("the river runs past the willow while the otter waits near the stone")
    assert not is_heartbeat("I keep thinking about what she said at the harbor that evening")


def test_ceiling_refuses_out_loud_and_off_means_off(tmp_path):
    eng = FishEngine(state_dir=tmp_path, name="ceiling", git_autocommit=False, max_crystals=2)
    r1 = eng.eat("the first thing worth remembering about the harbor at dusk", source="t")
    r2 = eng.eat("the second thing worth remembering about the lantern at night", source="t")
    r3 = eng.eat("the third thing that must be refused because the fish is full now", source="t")
    assert r1["crystals_added"] >= 1 and r2["crystals_added"] >= 1
    assert r3["crystals_added"] == 0 and r3["reason"] == "ceiling" and r3["ceiling"] == 2
    assert len(eng.fish.crystals) == 2
    # off means off: the same three eats with no ceiling all land
    eng2 = FishEngine(state_dir=tmp_path / "b", name="open", git_autocommit=False)
    for txt in ("first thing about the harbor at dusk worth remembering",
                "second thing about the lantern at night worth remembering",
                "third thing about the river in the morning worth remembering"):
        assert eng2.eat(txt, source="t")["crystals_added"] >= 1
    assert len(eng2.fish.crystals) == 3
