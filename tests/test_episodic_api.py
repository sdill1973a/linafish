"""Episodic recall API surface (Cal SPEC_v0.2 §8-§9) on the converse server.

Spins an in-process ThreadingHTTPServer backed by a real FishEngine and
exercises POST /recall_episodic and GET /moment/<episode_id>, including the
default-off privacy gate on /moment.
"""

import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from linafish.engine import FishEngine
from linafish.converse import ConverseHandler

DOCS = {
    "harness": "We wired the playtest harness for the arena combat engine, "
               "logging every spawn and router decision to the registry seam.",
    "corndog": "At the county fair the third corndog was the best one, hot "
               "mustard and a paper tray, fried batter still steaming.",
    "river":   "The river road at dawn, fog over the water, gravel under the "
               "tires, the long quiet drive home through the bottoms.",
}


def _seed_engine(tmp_path):
    e = FishEngine(state_dir=tmp_path, name="t", git_autocommit=False,
                   save_state_every_n_eats=1)
    e.eat(DOCS["harness"], episode_id="ep-1", episode_seq=0, episode_kind="session")
    e.eat(DOCS["corndog"], episode_id="ep-1", episode_seq=1, episode_kind="session")
    e.eat(DOCS["river"],   episode_id="ep-1", episode_seq=2, episode_kind="session")
    return e


def _server(engine, expose):
    ConverseHandler.engine = engine
    ConverseHandler.mind_name = "test"
    ConverseHandler.auth_token = None
    ConverseHandler.expose_full_sources = expose
    srv = ThreadingHTTPServer(("127.0.0.1", 0), ConverseHandler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    return srv, srv.server_address[1]


def _post(port, path, body):
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}",
        data=json.dumps(body).encode(), method="POST",
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=5) as r:
        return r.status, json.loads(r.read())


def _get(port, path):
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", method="GET")
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def test_recall_episodic_endpoint(tmp_path):
    e = _seed_engine(tmp_path)
    srv, port = _server(e, expose=False)
    try:
        status, data = _post(port, "/recall_episodic",
                             {"text": "the third corndog at the fair", "k": 3})
        assert status == 200
        assert data["query"]
        assert data["moments"]
        top = data["moments"][0]
        assert "pivots" in top and "before" in top and "after" in top
        assert top["episode_id"] == "ep-1"
    finally:
        srv.shutdown(); srv.server_close()


def test_moment_gated_off_by_default(tmp_path):
    e = _seed_engine(tmp_path)
    srv, port = _server(e, expose=False)
    try:
        status, data = _get(port, "/moment/ep-1")
        assert status == 403
        assert "disabled" in data["error"]
    finally:
        srv.shutdown(); srv.server_close()


def test_moment_returns_full_source_when_opted_in(tmp_path):
    e = _seed_engine(tmp_path)
    srv, port = _server(e, expose=True)
    try:
        status, data = _get(port, "/moment/ep-1")
        assert status == 200
        assert data["episode_id"] == "ep-1"
        # Untruncated source contains all three crystals' text.
        assert "corndog" in data["full_text"]
        assert "playtest harness" in data["full_text"]
        assert "river road" in data["full_text"]
        assert data["metadata"]["crystal_count"] == 3
    finally:
        srv.shutdown(); srv.server_close()


def test_moment_404_unknown_episode(tmp_path):
    e = _seed_engine(tmp_path)
    srv, port = _server(e, expose=True)
    try:
        status, data = _get(port, "/moment/does-not-exist")
        assert status == 404
    finally:
        srv.shutdown(); srv.server_close()


def test_get_episode_source_engine_level(tmp_path):
    """Engine method assembles untruncated source from the episode crystals."""
    e = _seed_engine(tmp_path)
    src = e.get_episode_source("ep-1")
    assert src is not None
    assert src.episode_id == "ep-1"
    assert "corndog" in src.full_text
    assert e.get_episode_source("nope") is None


def test_moment_full_source_requires_token_on_nonlocal_bind():
    """1.6.0 cold-eye guard: expose_full_sources on a non-local bind without a
    token must refuse to start — no unauthenticated full-source exposure. The
    guard fires before any engine/port setup, so this raises immediately."""
    from linafish.converse import serve_converse
    with pytest.raises(SystemExit):
        serve_converse(bind="lan", expose_full_sources=True, token=None, port=0)
    with pytest.raises(SystemExit):
        serve_converse(bind="wan", expose_full_sources=True, token=None, port=0)
