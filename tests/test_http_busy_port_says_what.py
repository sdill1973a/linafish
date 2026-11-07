"""`linafish http` on a busy port must say what is actually on the port.

Found 2026-11-07 (THX, Windows): with another fish already served on :8900, `http -n my-writing`
said "Another daemon is almost certainly already serving this fish" — it was a different fish.
The bind-first single-writer refusal stays; only the explanation changes.
"""
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from linafish.http_server import serve_http


def _holder(status, body, content_type="text/plain"):
    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            data = body.encode()
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *a):
            pass

    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def _refusal(capsys, tmp_path, srv, name):
    try:
        with pytest.raises(SystemExit) as ei:
            serve_http(state_dir=tmp_path, name=name, port=srv.server_address[1])
    finally:
        srv.shutdown()
        srv.server_close()
    assert ei.value.code == 1
    return capsys.readouterr().err


def test_busy_port_held_by_a_different_fish_names_it(capsys, tmp_path):
    srv = _holder(200, "# LiNafish: thx1138\n\n*250 formations*\n")
    err = _refusal(capsys, tmp_path, srv, "my-writing")
    assert "already serving this fish" not in err, err
    assert "thx1138" in err and "-p" in err, err


def test_busy_port_held_by_the_same_fish_says_so(capsys, tmp_path):
    srv = _holder(200, "# LiNafish: my-writing\n")
    err = _refusal(capsys, tmp_path, srv, "my-writing")
    assert "already serving" in err and "my-writing" in err, err


def test_busy_port_held_by_a_loading_fish_says_loading(capsys, tmp_path):
    srv = _holder(503, '{"status": "loading"}', "application/json")
    err = _refusal(capsys, tmp_path, srv, "my-writing")
    assert "loading" in err, err


def test_busy_port_held_by_something_else_says_not_linafish(capsys, tmp_path):
    srv = _holder(200, "<html>router admin</html>", "text/html")
    err = _refusal(capsys, tmp_path, srv, "my-writing")
    assert "already serving this fish" not in err, err
    assert "not a linafish" in err and "-p" in err, err
