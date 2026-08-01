"""The port must never lie in either direction during startup.

Pre-#42: the port was bound only after the engine loaded, so a probe during
load got a false DOWN and starters spawned a second daemon (two writers).

Binding first fixed that but introduced the mirror lie: bound-and-silent.
A connect-probe read UP for the entire load, and past request_queue_size the
connections were dropped. On a ~150K-crystal fish that is a multi-minute
window where a health probe hangs to its timeout instead of answering
(anchor-dill, PR #42 review).

So the socket answers from the first instant: 503 while loading, real
responses once the engine is live.
"""
import json
import socket
import threading
import urllib.error
import urllib.request

import pytest

from linafish import http_server


def _free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def test_probe_during_load_gets_fast_503_not_a_hang(monkeypatch, tmp_path):
    """The load window must answer, quickly and truthfully."""
    port = _free_port()
    engine_may_finish = threading.Event()
    probed = {}

    class SlowEngine:
        """Stands in for a large fish: slow to construct."""

        def __init__(self, *a, **kw):
            # The server is already accepting by now. Probe it mid-load.
            try:
                req = urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/health", timeout=5)
                probed["code"] = req.status
            except urllib.error.HTTPError as e:
                probed["code"] = e.code
                probed["body"] = json.loads(e.read().decode())
            except Exception as e:  # a hang lands here as a timeout
                probed["error"] = repr(e)
            engine_may_finish.set()
            raise RuntimeError("stop serve_http after the probe")

    monkeypatch.setattr(http_server, "FishEngine", SlowEngine)
    with pytest.raises(RuntimeError):
        http_server.serve_http(state_dir=tmp_path, name="tester", port=port)

    assert engine_may_finish.is_set()
    assert "error" not in probed, \
        f"probe did not get an answer during load: {probed.get('error')}"
    assert probed["code"] == 503, f"expected 503 during load, got {probed}"
    assert probed["body"]["status"] == "loading"


def test_not_ready_handler_is_honest_and_cheap():
    """Body must say loading and advise a retry, so starters can act on it."""
    port = _free_port()
    server = http_server._ExclusiveHTTPServer(
        ("127.0.0.1", port), http_server._NotReadyHandler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    try:
        with pytest.raises(urllib.error.HTTPError) as ei:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=5)
        assert ei.value.code == 503
        assert ei.value.headers.get("Retry-After") == "5"
        assert json.loads(ei.value.read().decode())["status"] == "loading"
    finally:
        server.shutdown()
        server.server_close()
