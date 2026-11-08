"""`doctor` must only count daemons that serve this state dir's fish as yours.

Found 2026-11-07 (Anchor, Linux): from a fresh HOME, `doctor` printed "[+] converse at
127.0.0.1:8901" for whatever happened to hold the port, another user's or another state
dir's fish, as if it were the reader's. A live daemon's /health names its fish_file; doctor
now compares that file's folder with its own state dir.
"""
import json
import os
import socket
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PORT = 8901


def _fake_converse(fish_file):
    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/health":
                body = json.dumps({"name": Path(fish_file).stem.replace(".fish", ""),
                                   "fish_file": str(fish_file)}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
            else:
                body = f"# LiNafish: {Path(fish_file).stem}\n".encode()
                self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a):
            pass

    try:
        srv = HTTPServer(("127.0.0.1", PORT), H)
    except OSError:
        pytest.skip(f"port {PORT} is busy on this machine")
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def _doctor(home):
    env = {**os.environ, "HOME": str(home), "USERPROFILE": str(home), "PYTHONPATH": str(ROOT)}
    env.pop("LINAFISH_PROTECTED_VOCAB", None)
    r = subprocess.run([sys.executable, "-m", "linafish", "doctor"], env=env, capture_output=True,
                       text=True, timeout=120)
    port_line = next((l for l in r.stdout.splitlines() if f":{PORT}" in l), r.stdout)
    ai_line = next((l for l in r.stdout.splitlines() if "AI-facing" in l), "")
    return port_line, ai_line


def test_doctor_does_not_claim_another_state_dirs_daemon(tmp_path):
    home = tmp_path / "home"
    (home / ".linafish").mkdir(parents=True)
    other = tmp_path / "someone-else" / ".linafish" / "theirs.fish.md"
    srv = _fake_converse(other)
    try:
        line, ai_line = _doctor(home)
    finally:
        srv.shutdown()
        srv.server_close()
    assert "[+]" not in line, line
    assert "not yours" in line and "theirs" in line, line
    assert "[+]" not in ai_line, ai_line  # modes: another dir's daemon is not your AI-facing leg


def test_doctor_counts_a_daemon_serving_this_state_dir(tmp_path):
    home = tmp_path / "home"
    (home / ".linafish").mkdir(parents=True)
    mine = home / ".linafish" / "mine.fish.md"
    srv = _fake_converse(mine)
    try:
        line, ai_line = _doctor(home)
    finally:
        srv.shutdown()
        srv.server_close()
    assert "[+]" in line and "mine" in line, line
