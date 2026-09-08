"""The guard and the gate live in FishEngine.eat() — the resource, not each door.

Olorina's review of #85 (2026-09-08): the ceiling had been generalized to the engine while
habituation was hand-wired per transport (room daemon, then `listen`), leaving the HTTP and
converse `/eat` routes — the path her 19,481-crystal fish is fed through — exactly as open as
the node that was being OOM-killed. Guard the resource, or the next transport re-opens it.
Proven here at the engine, through the converse server's own feed route, and across a restart.
"""
import json
import os
import sys
import threading
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest


@pytest.fixture(autouse=True)
def _gate_on(monkeypatch):
    # these tests exercise the gate; it is OPT-IN in the package (see habituation_from_env)
    monkeypatch.setenv("LINAFISH_HABITUATION", "on")

from linafish.engine import FishEngine
from linafish.converse import ConverseHandler

STATUS = "STATUS cpu 12 pct mem 41 pct net 3 kbs tick {i} all services nominal ok"
THOUGHTS = ["what she said at the harbor that evening changed how I read the whole year",
            "the otter went under the willow and did not come back up until the lantern was lit",
            "a stone in the water is a record of every current that failed to move it"]


def _warm(eng):
    for i in range(12):
        eng.eat(f"the river carries the lantern past the willow and the otter at dusk {i}", source="warm")


def test_engine_refuses_a_predicted_stream_and_a_heartbeat_and_writes_thoughts(tmp_path):
    eng = FishEngine(state_dir=tmp_path, name="res", git_autocommit=False)
    _warm(eng)
    before = len(eng.fish.crystals)
    assert eng.eat("T^keeper|alive|2026-09-08T00:00:00 all quiet on the wire", source="bot")["reason"] == "heartbeat"
    reasons = [eng.eat(STATUS.format(i=i), source="bot").get("reason") for i in range(40)]
    assert reasons.count("habituated") >= 20, reasons.count("habituated")
    for th in THOUGHTS:
        r = eng.eat(th, source="captain")
        assert r["crystals_added"] >= 1, r
    added = len(eng.fish.crystals) - before
    assert 3 <= added < 43
    assert eng.refusals["heartbeat"] == 1 and eng.refusals["habituated"] >= 20
    # stream crystals carry an episode the engine stamped
    eps = {getattr(c, "episode_id", None) for c in eng.fish.crystals[before:]}
    assert None not in eps and any(str(e).startswith("captain:") for e in eps), eps


def test_deliberate_deposits_are_never_gated(tmp_path):
    """`eat FILE` / `go` go through eat_path -> crystallize_text, not eat(): a person feeding
    their own writing must never have a paragraph refused as 'predicted'."""
    eng = FishEngine(state_dir=tmp_path, name="dep", git_autocommit=False)
    _warm(eng)
    f = tmp_path / "status.txt"
    f.write_text("\n\n".join(STATUS.format(i=i) for i in range(20)), encoding="utf-8")
    before = len(eng.fish.crystals)
    eng.eat_path(f)
    assert len(eng.fish.crystals) - before >= 5
    assert eng.refusals.get("habituated", 0) == 0


def test_expectation_and_counts_survive_a_restart(tmp_path):
    eng = FishEngine(state_dir=tmp_path, name="persist", git_autocommit=False)
    _warm(eng)
    for i in range(30):
        eng.eat(STATUS.format(i=i), source="bot")
    eng._save_state()
    n_before = eng.refusals["habituated"]
    again = FishEngine(state_dir=tmp_path, name="persist", git_autocommit=False)
    assert again.refusals["habituated"] == n_before
    assert "bot" in again.habituation.sources and again.habituation.sources["bot"].expected is not None
    r = again.eat(STATUS.format(i=99), source="bot")
    assert r.get("reason") == "habituated", r      # no ~20-message re-learning after a restart


def _serve(engine):
    ConverseHandler.engine = engine
    ConverseHandler.mind_name = "test"
    ConverseHandler.auth_token = None
    ConverseHandler.expose_full_sources = False
    srv = ThreadingHTTPServer(("127.0.0.1", 0), ConverseHandler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def _post(port, path, body):
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode())


def test_the_converse_feed_route_is_gated_too(tmp_path):
    eng = FishEngine(state_dir=tmp_path, name="wire", git_autocommit=False)
    _warm(eng)
    srv = _serve(eng)
    try:
        port = srv.server_address[1]
        reasons = [_post(port, "/eat", {"text": STATUS.format(i=i), "source": "node"}).get("reason") for i in range(30)]
        assert reasons.count("habituated") >= 15, reasons
        r = _post(port, "/eat", {"text": THOUGHTS[0], "source": "human"})
        assert r.get("crystals_added", 0) >= 1, r
    finally:
        srv.shutdown()


def test_the_gate_is_opt_in_by_default(tmp_path, monkeypatch):
    """The 2026-01-17 fork: 'The valve is open. Everything enters. Ache sorts.' Refusing at
    the door is a departure a node must choose, not a default it inherits."""
    monkeypatch.delenv("LINAFISH_HABITUATION", raising=False)
    eng = FishEngine(state_dir=tmp_path, name="dflt", git_autocommit=False)
    _warm(eng)
    reasons = [eng.eat(STATUS.format(i=i), source="bot").get("reason") for i in range(25)]
    assert "habituated" not in reasons
    assert eng.eat("T^keeper|alive|2026-09-08T00:00:00 all quiet on the wire", source="bot")["reason"] == "heartbeat"  # the pulse guard is not the gate; it stays on
