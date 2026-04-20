"""Regression test for issue #9: linafish HTTP servers must handle
concurrent requests without blocking.

Single-threaded HTTPServer blocks new requests while one is in flight.
ThreadingHTTPServer spawns a thread per request. Three linafish entry
points (converse, http_server, quickstart) all need the threaded base.
"""
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest


class _SlowHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        time.sleep(0.3)
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *a, **kw):
        pass


def test_threading_http_server_serves_concurrent_requests():
    """Prove the contract: ThreadingHTTPServer handles N slow requests
    in time << N*delay, because handlers run in parallel."""
    server = ThreadingHTTPServer(("127.0.0.1", 0), _SlowHandler)
    port = server.server_address[1]
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()

    try:
        n = 5
        results = []
        threads = []

        def fetch():
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/", timeout=5
                ) as r:
                    results.append(r.read())
            except Exception as e:
                results.append(e)

        start = time.monotonic()
        for _ in range(n):
            th = threading.Thread(target=fetch)
            th.start()
            threads.append(th)
        for th in threads:
            th.join(timeout=10)
        elapsed = time.monotonic() - start

        assert len(results) == n, f"expected {n} responses, got {len(results)}"
        assert all(r == b"ok" for r in results), f"bad responses: {results}"
        assert elapsed < n * 0.3 * 0.9, (
            f"elapsed {elapsed:.2f}s should be << {n * 0.3:.2f}s "
            "(serial) — server is not actually threading"
        )
    finally:
        server.shutdown()
        server.server_close()


@pytest.mark.parametrize("module_path,anchor_name", [
    ("linafish/converse.py", "ConverseHandler"),
    ("linafish/http_server.py", "FishHandler"),
    ("linafish/quickstart.py", "actual_port"),
])
def test_modules_use_threading_http_server(module_path, anchor_name):
    """Static guard: each linafish HTTP entry point must instantiate
    ThreadingHTTPServer, not HTTPServer. Regresses if someone reverts.
    """
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    src = (root / module_path).read_text(encoding="utf-8")
    assert anchor_name in src, (
        f"{module_path} missing anchor {anchor_name!r} — "
        "test needs updating or file moved"
    )
    assert "ThreadingHTTPServer" in src, (
        f"{module_path} does not reference ThreadingHTTPServer — "
        "the threading fix for issue #9 has regressed"
    )
