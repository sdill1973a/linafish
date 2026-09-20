"""``linafish converse --dedupe``: a served fish must be able to refuse a repeat.

Both directions, on purpose — a guard proven only on the happy path is an organ
that cannot fail:
  * dedupe on : same text twice -> the fish grows by ONE, second reply says "duplicate";
                a distinct text is still accepted.
  * dedupe off: same text twice -> grows by TWO (the old behaviour, unchanged).
"""
import json
import threading
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from linafish.engine import FishEngine
from linafish.converse import ConverseHandler


def _serve(tmp_path, dedupe):
    engine = FishEngine(state_dir=tmp_path / "fish", name="t", git_autocommit=False,
                        dedupe=dedupe)

    class H(ConverseHandler):
        pass

    H.engine = engine
    H.mind_name = "test"
    H.auth_token = None
    H.expose_full_sources = False
    srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, srv.server_address[1], engine


def _eat(port, text):
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/eat",
        data=json.dumps({"text": text, "source": "test"}).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode())


TEXT = ("the executable glyph engine composed four glyphs to one child and the child "
        "expanded back to the same four without loss")
OTHER = ("a second, different sentence about the river crystal that already knows both "
         "things are true and they are the same person")


def test_dedupe_on_refuses_exact_repeat(tmp_path):
    srv, port, engine = _serve(tmp_path, dedupe=True)
    try:
        n0 = len(engine.crystals)
        r1 = _eat(port, TEXT)
        r2 = _eat(port, TEXT)
        assert len(engine.crystals) == n0 + 1, "the same text must land once"
        assert r1.get("crystals_added", 0) >= 1
        assert r2.get("crystals_added") == 0 and r2.get("reason") == "duplicate", r2
        r3 = _eat(port, OTHER)
        assert r3.get("crystals_added", 0) >= 1, "a distinct text must still be accepted"
        assert len(engine.crystals) == n0 + 2
    finally:
        srv.shutdown()


def test_dedupe_off_keeps_old_behaviour(tmp_path):
    """Negative control: without the flag the served path still stacks repeats."""
    srv, port, engine = _serve(tmp_path, dedupe=False)
    try:
        n0 = len(engine.crystals)
        _eat(port, TEXT)
        r2 = _eat(port, TEXT)
        assert len(engine.crystals) == n0 + 2
        assert r2.get("reason") != "duplicate"
    finally:
        srv.shutdown()


def test_cli_flag_reaches_serve_converse(monkeypatch):
    """The flag on the command line is the flag on the engine — no silent drop."""
    import argparse
    from linafish import __main__ as m
    seen = {}
    monkeypatch.setattr("linafish.converse.serve_converse", lambda **kw: seen.update(kw))
    args = argparse.Namespace(name="t", state_dir=None, port=0, bind="local", mind=None,
                              token=None, dedupe=True)
    m.cmd_converse(args)
    assert seen.get("dedupe") is True


def test_serve_converse_passes_dedupe_to_engine(monkeypatch, tmp_path):
    """serve_converse -> FishEngine(dedupe=...) — the middle link, mutation-tested."""
    import linafish.converse as cv
    seen = {}

    class FakeEngine:
        name = "t"; crystals = []
        _shutdown_pending = False; _save_in_progress = False
        def __init__(self, **kw): seen.update(kw)
        def flush_commit(self, *a, **k): pass

    class FakeServer:
        def __init__(self, addr, handler): self.server_address = addr
        def serve_forever(self): pass
        def server_close(self): pass

    monkeypatch.setattr(cv, "FishEngine", FakeEngine)
    monkeypatch.setattr(cv, "ThreadingHTTPServer", FakeServer)
    monkeypatch.setattr(cv.signal, "signal", lambda *a, **k: None)
    cv.serve_converse(name="t", state_dir=tmp_path, port=0, bind="local", dedupe=True)
    assert seen.get("dedupe") is True
    seen.clear()
    cv.serve_converse(name="t", state_dir=tmp_path, port=0, bind="local")
    assert seen.get("dedupe") is False, "default must stay OFF — public behaviour unchanged"
