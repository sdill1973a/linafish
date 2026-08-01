"""Regression test: serve_http must bind the port BEFORE loading the engine.

Starters decide "is the daemon already up?" by probing the port. Engine load
on a large fish takes seconds to minutes. While the port was bound only after
that load, every second of it was a window in which the probe said DOWN and a
second daemon spawned. The loser's bind then failed — but the non-daemon
maintenance thread had already started, so the process did not exit. It stayed
alive calling re_eat() (which writes state) against the same state dir as the
winner: two writers to one fish, the exact thing the disjoint-writer rule
forbids, reached silently and by accident.

The fix is ordering. These tests pin it.
"""
import socket
import threading

import pytest

from linafish import http_server


def _free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def test_second_daemon_dies_before_building_an_engine(monkeypatch, tmp_path):
    """The whole point: a loser must exit without ever touching the fish."""
    port = _free_port()
    holder = socket.socket()
    holder.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    holder.bind(("127.0.0.1", port))
    holder.listen(1)

    built = []

    def spy(*a, **kw):
        built.append(kw)
        raise AssertionError("engine must not be constructed after bind failure")

    monkeypatch.setattr(http_server, "FishEngine", spy)
    try:
        with pytest.raises(SystemExit):
            http_server.serve_http(state_dir=tmp_path, name="tester", port=port)
    finally:
        holder.close()

    assert built == [], "loser constructed an engine — second writer possible"


def test_port_is_listening_before_engine_load(monkeypatch, tmp_path):
    """Ordering, observed from the outside: by the time the engine is being
    built, a starter probing the port must already see it occupied."""
    port = _free_port()
    seen = {}

    class FakeEngine:
        def __init__(self, *a, **kw):
            probe = socket.socket()
            probe.settimeout(2)
            try:
                probe.connect(("127.0.0.1", port))
                seen["bound"] = True
            except OSError:
                seen["bound"] = False
            finally:
                probe.close()
            raise RuntimeError("stop serve_http here")

    monkeypatch.setattr(http_server, "FishEngine", FakeEngine)

    t = threading.Thread(
        target=lambda: pytest.raises(RuntimeError)(
            lambda: http_server.serve_http(
                state_dir=tmp_path, name="tester", port=port)
        )(),
        daemon=True,
    )
    # signal.signal only works on the main thread, and serve_http installs
    # handlers after the engine — we never get that far, so run inline.
    with pytest.raises(RuntimeError):
        http_server.serve_http(state_dir=tmp_path, name="tester", port=port)
    del t

    assert seen.get("bound") is True, \
        "port was still closed during engine load — the race window is open"
