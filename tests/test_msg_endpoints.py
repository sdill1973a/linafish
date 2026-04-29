"""Tests for the federation message broker endpoints in http_server.py.

POST /msg, GET /inbox/<mind_id>, POST /msg/read

Ported from .67 protofish (fish_server.py) on 2026-04-29 as part of the
v7 migration §THE.SORT.OUT — federating the message broker so it ships
with linafish instead of living in a single bespoke Flask app on .67.
"""

import json
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

from linafish.engine import FishEngine
from linafish.http_server import (
    FishHandler,
    _append_message,
    _gen_msg_id,
    _load_messages,
    _messages_file,
    _save_messages,
)


# --- Fixtures --------------------------------------------------------------


@pytest.fixture
def tmp_engine(tmp_path):
    """A fresh FishEngine with isolated state_dir."""
    return FishEngine(state_dir=tmp_path, name="testfish")


@pytest.fixture
def server(tmp_engine):
    """A live HTTP server bound to a random port, running in a background thread."""
    FishHandler.engine = tmp_engine
    srv = ThreadingHTTPServer(("127.0.0.1", 0), FishHandler)
    port = srv.server_address[1]
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        srv.shutdown()
        srv.server_close()


def _post(url: str, body: dict) -> tuple[int, dict]:
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def _get(url: str) -> tuple[int, dict]:
    try:
        with urllib.request.urlopen(url, timeout=5) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


# --- Helper-function tests -------------------------------------------------


def test_gen_msg_id_unique():
    ids = {_gen_msg_id() for _ in range(100)}
    assert len(ids) == 100
    assert all(i.startswith("msg_") for i in ids)
    assert all(len(i) == 16 for i in ids)  # "msg_" + 12 hex chars


def test_messages_file_default(tmp_engine):
    path = _messages_file(tmp_engine)
    assert path == Path(tmp_engine.state_dir) / "messages.jsonl"


def test_messages_file_env_override(tmp_engine, tmp_path, monkeypatch):
    override = tmp_path / "elsewhere.jsonl"
    monkeypatch.setenv("LINAFISH_MESSAGES_FILE", str(override))
    assert _messages_file(tmp_engine) == override


def test_load_messages_missing_file(tmp_path):
    assert _load_messages(tmp_path / "nope.jsonl") == []


def test_append_then_load_roundtrip(tmp_path):
    path = tmp_path / "msgs.jsonl"
    msg = {"id": "msg_test", "from": "A", "to": "B", "text": "hi"}
    _append_message(path, msg)
    assert _load_messages(path) == [msg]


def test_save_messages_atomic(tmp_path):
    path = tmp_path / "msgs.jsonl"
    msgs = [{"id": f"msg_{i}", "to": "B", "read": False} for i in range(3)]
    _save_messages(path, msgs)
    assert _load_messages(path) == msgs

    # rewrite with marks
    msgs[0]["read"] = True
    _save_messages(path, msgs)
    loaded = _load_messages(path)
    assert loaded[0]["read"] is True
    assert loaded[1]["read"] is False


def test_append_skips_invalid_json(tmp_path):
    path = tmp_path / "msgs.jsonl"
    _append_message(path, {"id": "msg_good", "to": "B"})
    # corrupt the file with a bad line
    path.write_text(path.read_text() + "this is not json\n", encoding="utf-8")
    msgs = _load_messages(path)
    assert len(msgs) == 1
    assert msgs[0]["id"] == "msg_good"


# --- End-to-end HTTP tests -------------------------------------------------


def test_msg_send_minimal(server):
    code, body = _post(f"{server}/msg",
                       {"from": "anchor", "to": "olorina", "text": "hello sister"})
    assert code == 200
    assert body["status"] == "sent"
    assert body["id"].startswith("msg_")
    assert "ts" in body


def test_msg_send_missing_fields(server):
    code, body = _post(f"{server}/msg", {"from": "anchor"})
    assert code == 400
    assert "required" in body["error"]


def test_msg_send_then_inbox_read_lifecycle(server):
    # Send two messages to olorina, one to thx
    _post(f"{server}/msg",
          {"from": "anchor", "to": "olorina", "text": "first"})
    time.sleep(0.01)
    _post(f"{server}/msg",
          {"from": "anchor", "to": "olorina", "text": "second"})
    _post(f"{server}/msg",
          {"from": "anchor", "to": "thx", "text": "for thx"})

    # Inbox for olorina returns 2 unread, newest first
    code, body = _get(f"{server}/inbox/olorina")
    assert code == 200
    assert body["count"] == 2
    assert body["messages"][0]["text"] == "second"
    assert body["messages"][1]["text"] == "first"

    # Inbox for thx returns 1
    code, body = _get(f"{server}/inbox/thx")
    assert code == 200
    assert body["count"] == 1

    # Mark olorina's first message read
    first_id = body["messages"][0]["id"]  # whoops that was thx's; refetch
    code, olorina_inbox = _get(f"{server}/inbox/olorina")
    target_id = olorina_inbox["messages"][0]["id"]
    code, body = _post(f"{server}/msg/read",
                       {"mind_id": "olorina", "ids": [target_id]})
    assert code == 200
    assert body["marked"] == 1

    # Olorina inbox now shows 1 unread
    code, body = _get(f"{server}/inbox/olorina")
    assert body["count"] == 1


def test_inbox_limit(server):
    for i in range(5):
        _post(f"{server}/msg",
              {"from": "anchor", "to": "olorina", "text": f"msg {i}"})
        time.sleep(0.005)

    code, body = _get(f"{server}/inbox/olorina?limit=2")
    assert code == 200
    assert body["count"] == 2


def test_inbox_since_filter(server):
    code, old_resp = _post(f"{server}/msg",
                           {"from": "anchor", "to": "olorina", "text": "old"})
    cutoff = old_resp["ts"]  # use actual ts as cutoff so lexical compare matches
    time.sleep(0.01)
    _post(f"{server}/msg",
          {"from": "anchor", "to": "olorina", "text": "new"})

    qs = urllib.parse.urlencode({"since": cutoff})
    code, body = _get(f"{server}/inbox/olorina?{qs}")
    assert code == 200
    # Filter is strict greater-than, so "old" (with ts==cutoff) is excluded
    texts = [m["text"] for m in body["messages"]]
    assert "new" in texts
    assert "old" not in texts


def test_msg_read_validates_mind_id(server):
    _post(f"{server}/msg",
          {"from": "anchor", "to": "olorina", "text": "test"})
    code, body = _get(f"{server}/inbox/olorina")
    msg_id = body["messages"][0]["id"]

    # Wrong mind tries to mark olorina's msg read — should not mark
    code, body = _post(f"{server}/msg/read",
                       {"mind_id": "imposter", "ids": [msg_id]})
    assert code == 200
    assert body["marked"] == 0

    # Olorina still has unread
    code, body = _get(f"{server}/inbox/olorina")
    assert body["count"] == 1


def test_msg_read_missing_fields(server):
    code, body = _post(f"{server}/msg/read", {"mind_id": "olorina"})
    assert code == 400


def test_msg_read_idempotent(server):
    _post(f"{server}/msg",
          {"from": "anchor", "to": "olorina", "text": "test"})
    code, inbox = _get(f"{server}/inbox/olorina")
    msg_id = inbox["messages"][0]["id"]

    code, body = _post(f"{server}/msg/read",
                       {"mind_id": "olorina", "ids": [msg_id]})
    assert body["marked"] == 1

    # Marking again returns 0 (already read)
    code, body = _post(f"{server}/msg/read",
                       {"mind_id": "olorina", "ids": [msg_id]})
    assert body["marked"] == 0


def test_inbox_unknown_mind_returns_empty(server):
    code, body = _get(f"{server}/inbox/nobody")
    assert code == 200
    assert body["count"] == 0
    assert body["messages"] == []


def test_existing_endpoints_still_work(server):
    """Regression: don't let the new routes shadow the old ones."""
    code, body = _get(f"{server}/health")
    assert code == 200
    assert "crystals" in body or "engine" in body or "service" in body or len(body) > 0
