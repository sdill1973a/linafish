"""
LiNafish Converse — Two fish, one conversation.

Crystal exchange IS the conversation. No MQTT, no bridge, no dedup.
The coupling between crystals from different minds IS the relationship.

Three access levels:
  local (default) — 127.0.0.1, no auth
  lan             — 0.0.0.0, auth optional
  wan             — 0.0.0.0, auth required

Usage:
    linafish converse --mind anchor --port 8901
    linafish converse --mind anchor --port 8901 --bind lan
    linafish converse --mind anchor --port 8901 --bind wan --token secret

Then from another fish:
    linafish converse --mind scott --port 8902
    # Pull crystals from anchor: GET localhost:8901/crystals
    # Push crystals to anchor:   POST localhost:8901/crystals

s93, 2026-04-11. The mesh grows another synapse.
"""

import json
import socket
import sys
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse, parse_qs

from .engine import FishEngine


BIND_MAP = {
    "local": "127.0.0.1",
    "localhost": "127.0.0.1",
    "lan": "0.0.0.0",
    "wan": "0.0.0.0",
}


class ConverseHandler(BaseHTTPRequestHandler):
    """HTTP handler for crystal exchange between minds."""

    engine: FishEngine = None
    mind_name: str = "unknown"
    auth_token: str = None  # None = no auth required

    def _check_auth(self) -> bool:
        """Check auth token if configured. Returns True if OK."""
        if not self.auth_token:
            return True
        header = self.headers.get("Authorization", "")
        if header == f"Bearer {self.auth_token}":
            return True
        self._respond(401, json.dumps({"error": "unauthorized"}), "application/json")
        return False

    def do_GET(self):
        if not self._check_auth():
            return

        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        if parsed.path == "/":
            self._respond(200, json.dumps({
                "service": "linafish-converse",
                "mind": self.mind_name,
                "fish": self.engine.name,
                "crystals": len(self.engine.crystals),
                "formations": len(self.engine.formations),
                "endpoints": [
                    "GET  /crystals?since=ISO&mind=NAME  — pull crystals",
                    "POST /crystals  — push crystals",
                    "GET  /minds  — list source minds",
                    "GET  /pfc  — formations",
                    "GET  /health  — stats",
                    "POST /eat  — feed text",
                    "POST /taste  — semantic search",
                ],
            }, indent=2), "application/json")

        elif parsed.path == "/crystals":
            since = params.get("since", [None])[0]
            mind_filter = params.get("mind", [None])[0]
            crystals = self._get_crystals(since=since, mind=mind_filter)
            self._respond(200, json.dumps(crystals, default=str), "application/json")

        elif parsed.path == "/minds":
            minds = set()
            for c in self.engine.crystals:
                src = c.source or ""
                if ":" in src:
                    minds.add(src.split(":")[0])
                else:
                    minds.add(self.mind_name)
            self._respond(200, json.dumps({
                "minds": sorted(minds),
                "total_crystals": len(self.engine.crystals),
            }, indent=2), "application/json")

        elif parsed.path == "/pfc":
            self._respond(200, self.engine.pfc())

        elif parsed.path == "/health":
            self._respond(200, self.engine.health(), "application/json")

        else:
            self._respond(404, "Not found")

    def do_POST(self):
        if not self._check_auth():
            return

        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length)) if length else {}
        except (json.JSONDecodeError, ValueError):
            self._respond(400, json.dumps({"error": "invalid JSON"}), "application/json")
            return

        parsed = urlparse(self.path)

        if parsed.path == "/crystals":
            # Accept crystals from another mind
            crystals = body if isinstance(body, list) else [body]
            eaten = 0
            for c in crystals:
                text = c.get("text", "")
                source_mind = c.get("source_mind", c.get("from", "unknown"))
                source = c.get("source", "converse")
                if text and len(text.strip()) > 10:
                    self.engine.eat(text, source=f"{source_mind}:{source}")
                    eaten += 1
            self._respond(200, json.dumps({
                "accepted": eaten,
                "total_crystals": len(self.engine.crystals),
                "formations": len(self.engine.formations),
            }), "application/json")

        elif parsed.path == "/eat":
            text = body.get("text", "")
            source = body.get("source", "session")
            source_mind = body.get("source_mind", self.mind_name)
            if not text:
                self._respond(400, json.dumps({"error": "missing text"}), "application/json")
                return
            result = self.engine.eat(text, source=f"{source_mind}:{source}")
            self._respond(200, json.dumps(result), "application/json")

        elif parsed.path == "/taste":
            text = body.get("text", "")
            top = body.get("top", 5)
            if not text:
                self._respond(400, json.dumps({"error": "missing text"}), "application/json")
                return
            self._respond(200, self.engine.taste(text, top=top))

        else:
            self._respond(404, "Not found")

    def _get_crystals(self, since: str = None, mind: str = None) -> list:
        """Return crystals, optionally filtered by time and source mind."""
        results = []
        for c in self.engine.crystals:
            # Filter by time (ISO string comparison — works for ISO 8601 format)
            if since:
                try:
                    crystal_time = c.ts or ""
                    # Normalize both to comparable ISO strings
                    since_clean = since.replace("Z", "+00:00")
                    ts_clean = crystal_time.replace("Z", "+00:00") if crystal_time else ""
                    if ts_clean and ts_clean < since_clean:
                        continue
                except (TypeError, ValueError):
                    pass

            # Filter by mind
            if mind:
                src = c.source or ""
                crystal_mind = src.split(":")[0] if ":" in src else self.mind_name
                if crystal_mind != mind:
                    continue

            results.append({
                "id": c.id,
                "text": c.text,
                "source": c.source,
                "source_mind": (c.source or "").split(":")[0] if ":" in (c.source or "") else self.mind_name,
                "ts": c.ts,
                "keywords": c.keywords[:5] if c.keywords else [],
            })

        return results

    def _respond(self, code: int, body: str, content_type: str = "text/plain; charset=utf-8"):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        self.end_headers()
        # s95 2026-04-13: Anchor diagnosed that a client with a low HTTP_TIMEOUT
        # can abort the TCP connection before the server finishes clustering +
        # writing the response. Unhandled, BaseHTTPServer treats it as fatal and
        # the whole daemon shuts down ("Converse stopped 5685 crystals"). Wrap
        # the response write so client disconnects log and return instead of
        # taking the daemon out. Let both our daemons tolerate fire-and-forget
        # clients — the request still landed on the server side.
        try:
            self.wfile.write(body.encode("utf-8"))
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError) as e:
            # Client dropped mid-response. The feed/taste already happened
            # server-side; only the reply got lost. Log quietly and return.
            try:
                import sys as _sys
                print(f"[converse] client dropped during response: {type(e).__name__}", file=_sys.stderr)
            except Exception:
                pass
            return

    def do_OPTIONS(self):
        """CORS preflight."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        self.end_headers()

    def log_message(self, format, *args):
        pass  # Quiet — use --verbose flag if debugging needed


def serve_converse(
    name: str = "linafish",
    state_dir: Optional[Path] = None,
    port: int = 8901,
    bind: str = "local",
    mind: str = None,
    token: str = None,
):
    """Start the converse server."""
    host = BIND_MAP.get(bind, bind)

    if bind == "wan" and not token:
        print("Error: WAN access requires --token for authentication.", file=sys.stderr)
        print("  linafish converse --bind wan --token YOUR_SECRET", file=sys.stderr)
        sys.exit(1)

    if mind is None:
        mind = socket.gethostname()

    engine = FishEngine(state_dir=state_dir, name=name)

    ConverseHandler.engine = engine
    ConverseHandler.mind_name = mind
    ConverseHandler.auth_token = token

    server = HTTPServer((host, port), ConverseHandler)

    print(f"  LiNafish Converse", file=sys.stderr)
    print(f"  Mind: {mind}", file=sys.stderr)
    print(f"  Fish: {engine.name} ({len(engine.crystals)} crystals)", file=sys.stderr)
    print(f"  Listening: http://{host}:{port}", file=sys.stderr)
    print(f"  Access: {bind}" + (f" (token required)" if token else ""), file=sys.stderr)
    print(f"  Press Ctrl+C to stop.", file=sys.stderr)
    print(file=sys.stderr)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print(f"\n  Converse stopped. {len(engine.crystals)} crystals.", file=sys.stderr)
