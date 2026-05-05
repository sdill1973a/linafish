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
import signal
import socket
import sys
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse, parse_qs

from .engine import FishEngine
from .http_server import (
    _messages_file,
    _gen_msg_id,
    _load_messages,
    _save_messages,
    _append_message,
    _MESSAGES_LOCK,
)


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
                    "GET  /emerge  — emergence metrics (ν, μ, ρ, Ψ, phase)",
                    "GET  /growth  — R(n) curve, coupling density, dimension entropy",
                    "GET  /inbox/<mind_id>  — unread DMs for a mind",
                    "POST /eat  — feed text",
                    "POST /taste  — semantic search",
                    "POST /msg  — federation DM send",
                    "POST /msg/read  — mark read",
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

        elif parsed.path == "/emerge":
            result = self.engine._check_emergence()
            if result is None:
                self._respond(200, json.dumps({
                    "signal": False,
                    "reason": "no cognitive-op data or no formations",
                }), "application/json")
            else:
                self._respond(200, json.dumps(result, indent=2), "application/json")

        elif parsed.path == "/growth":
            tracker = getattr(self.engine, "tracker", None)
            if tracker is None or not tracker.snapshots:
                self._respond(
                    200,
                    "No growth data yet. POST /re-eat to run a maintenance cycle first.",
                )
            else:
                self._respond(200, tracker.growth_summary())

        elif parsed.path.startswith("/inbox/"):
            self._handle_inbox(parsed)

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
            fmt = body.get("format", "text")
            if not text:
                self._respond(400, json.dumps({"error": "missing text"}), "application/json")
                return
            if fmt == "json":
                self._respond(
                    200,
                    json.dumps(self.engine.taste_dict(text, top=top)),
                    "application/json",
                )
            else:
                self._respond(200, self.engine.taste(text, top=top))

        elif parsed.path == "/msg":
            self._handle_msg_send(body)

        elif parsed.path == "/msg/read":
            self._handle_msg_read(body)

        else:
            self._respond(404, "Not found")

    # --- Federation DM endpoints (port from FishHandler) ----------------------

    def _handle_inbox(self, parsed):
        """GET /inbox/<mind_id>?limit=20&since=ts — unread messages for a mind."""
        mind_id = parsed.path[len("/inbox/"):]
        if not mind_id:
            self._respond(400, json.dumps({"error": "missing mind_id"}),
                          "application/json")
            return

        qs = parse_qs(parsed.query)
        try:
            limit = int(qs.get("limit", ["20"])[0])
        except (ValueError, IndexError):
            limit = 20
        since = qs.get("since", [None])[0]

        msgs_path = _messages_file(self.engine)
        msgs = _load_messages(msgs_path)
        filtered = [m for m in msgs
                    if m.get("to") == mind_id and not m.get("read", False)]
        if since:
            filtered = [m for m in filtered if m.get("ts", "") > since]
        filtered.sort(key=lambda m: m.get("ts", ""), reverse=True)
        filtered = filtered[:limit]

        self._respond(
            200,
            json.dumps({"messages": filtered, "count": len(filtered)}),
            "application/json",
        )

    def _handle_msg_send(self, body: dict):
        """POST /msg — send a DM, also crystallize via fish.eat()."""
        sender = body.get("from", "")
        recipient = body.get("to", "")
        text = body.get("text", "")
        protocol = body.get("protocol", "fish-dm")

        if not sender or not recipient or not text:
            self._respond(
                400,
                json.dumps({"error": "from, to, and text are required"}),
                "application/json",
            )
            return

        ts = datetime.now(timezone.utc).isoformat()
        msg_id = _gen_msg_id()

        crystallized = False
        try:
            result = self.engine.eat(text, source=f"dm:{sender}->{recipient}")
            crystallized = result.get("crystals_added", 0) > 0
        except Exception as e:
            print(f"DM crystallize error: {e}", flush=True)

        msg = {
            "id": msg_id,
            "ts": ts,
            "from": sender,
            "to": recipient,
            "text": text,
            "protocol": protocol,
            "read": False,
            "crystallized": crystallized,
        }

        _append_message(_messages_file(self.engine), msg)

        self._respond(
            200,
            json.dumps({"status": "sent", "ts": ts, "id": msg_id}),
            "application/json",
        )

    def _handle_msg_read(self, body: dict):
        """POST /msg/read — mark messages as read for a mind."""
        mind_id = body.get("mind_id", "")
        ids = body.get("ids", [])

        if not mind_id or not ids:
            self._respond(
                400,
                json.dumps({"error": "mind_id and ids are required"}),
                "application/json",
            )
            return

        ids_set = set(ids)
        msgs_path = _messages_file(self.engine)

        with _MESSAGES_LOCK:
            msgs = _load_messages(msgs_path)
            marked = 0
            for m in msgs:
                if (m.get("id") in ids_set
                        and m.get("to") == mind_id
                        and not m.get("read", False)):
                    m["read"] = True
                    marked += 1
            if marked > 0:
                _save_messages(msgs_path, msgs)

        self._respond(200, json.dumps({"marked": marked}), "application/json")

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
        # A client with a low HTTP_TIMEOUT can abort the TCP connection
        # before the server finishes clustering + writing the response.
        # Unhandled, BaseHTTPServer treats it as fatal and the whole
        # daemon shuts down. Wrap the response write so client disconnects
        # log and return instead of taking the daemon out. The request
        # still landed on the server side.
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

    # Converse /eat path uses periodic commit (every 100 eats) — same shape
    # as http_server.py. Per-eat autocommit wedged the single-threaded
    # request loop (25-30s on .140 me-fish at 12K crystals). N=100 keeps
    # state-dir git history advancing for rollback (codex round-1 finding
    # 2026-05-02: pure git_autocommit=False stranded daemon history because
    # daemons never call session_end). SIGTERM/SIGINT handler flushes
    # uncommitted eats on graceful shutdown.
    engine = FishEngine(state_dir=state_dir, name=name, commit_every_n_eats=100)

    def _flush_on_shutdown(signum, frame):
        # Reentrancy-safe: if a _save_state is in progress we cannot commit
        # right now without risking torn-state capture (codex round-2
        # 2026-05-02). Mark intent and let the in-flight save's finally
        # clause handle the commit + exit. If idle, flush + exit here.
        engine._shutdown_pending = True
        if not engine._save_in_progress:
            try:
                engine.flush_commit(f"converse daemon shutdown (signal {signum})")
            except Exception as e:
                print(f"flush_commit failed on shutdown: {e}", file=sys.stderr)
            sys.exit(0)
    signal.signal(signal.SIGTERM, _flush_on_shutdown)
    signal.signal(signal.SIGINT, _flush_on_shutdown)

    ConverseHandler.engine = engine
    ConverseHandler.mind_name = mind
    ConverseHandler.auth_token = token

    server = ThreadingHTTPServer((host, port), ConverseHandler)

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
