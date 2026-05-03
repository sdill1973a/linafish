"""
LiNafish HTTP Server — the universal interface.

Tiny HTTP server. Zero dependencies beyond stdlib. Any AI that can fetch
a URL can read the fish. Serves the same engine as the MCP server.

    GET  /pfc                — formations (the metacognitive overlay)
    GET  /health             — engine stats
    GET  /emerge             — emergence metrics (ν, μ, ρ, Ψ, phase)
    GET  /growth             — R(n) curve, coupling density, dimension entropy
    GET  /fish               — raw fish.md contents
    POST /eat                — feed text (JSON: {"text": "...", "source": "..."})
    POST /taste              — cross-corpus match (JSON: {"text": "...", "top": 5})
    POST /match              — tight recall (JSON: {"text": "...", "top": 3})
    POST /re-eat             — maintenance cycle (gardener + assessment + growth)

    Federation message broker (added 2026-04-29 from .67 protofish):
    POST /msg                — send a DM (JSON: {"from": "...", "to": "...",
                                                 "text": "...", "protocol": "..."})
    GET  /inbox/<mind_id>    — unread for a mind (?limit=20&since=ts)
    POST /msg/read           — mark read (JSON: {"mind_id": "...", "ids": [...]})

Usage:
    linafish http --feed ./my-docs
    linafish http --feed ./my-docs --port 8900
"""

import json
import os
import signal
import sys
import threading
import uuid
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse, parse_qs

from .engine import FishEngine


def _load_primer() -> str:
    """Load the AI primer document."""
    primer_path = Path(__file__).parent / "data" / "ai_primer.md"
    if primer_path.exists():
        return primer_path.read_text(encoding="utf-8", errors="replace")
    return ""


_PRIMER = ""  # loaded at server start


# --- Federation message broker (DM) helpers --------------------------------
# Ported from .67 protofish (fish_server.py) 2026-04-29 §THE.RECEIPTS.ON.THE.WIRE
# follow-up. Three endpoints: POST /msg, GET /inbox/<mind_id>, POST /msg/read.
# State lives in <state_dir>/messages.jsonl (override via LINAFISH_MESSAGES_FILE).

_MESSAGES_LOCK = threading.Lock()


def _messages_file(engine: FishEngine) -> Path:
    """Resolve the federation-DM message log path.

    Default: <state_dir>/messages.jsonl
    Override: LINAFISH_MESSAGES_FILE env var (absolute path).

    The override is what lets .67 cut over to master http_server while
    keeping the existing /home/sdill/fish_messages.jsonl as the authoritative
    message log — no migration of historical DMs needed.
    """
    override = os.environ.get("LINAFISH_MESSAGES_FILE")
    if override:
        return Path(override)
    return Path(engine.state_dir) / "messages.jsonl"


def _gen_msg_id() -> str:
    return "msg_" + uuid.uuid4().hex[:12]


def _load_messages(path: Path) -> list:
    msgs = []
    if path.exists():
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        msgs.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    return msgs


def _save_messages(path: Path, msgs: list) -> None:
    """Atomic rewrite of the entire message log (used to mark-read)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        for m in msgs:
            f.write(json.dumps(m) + "\n")
    os.replace(tmp, path)


def _append_message(path: Path, msg: dict) -> None:
    """Thread-safe append of a single message to the JSONL log."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with _MESSAGES_LOCK:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(msg) + "\n")


# ---------------------------------------------------------------------------


class FishHandler(BaseHTTPRequestHandler):
    """HTTP handler for the fish."""

    engine: FishEngine = None  # set by serve_http()

    def do_GET(self):
        if self.path == "/pfc":
            self._respond(200, self.engine.pfc())
        elif self.path == "/boot":
            # Warm boot payload: primer + fish for any AI to read at session start
            pfc = self.engine.pfc()
            if _PRIMER:
                payload = f"{_PRIMER}\n\n---\n\n# This Person's Fish\n\n{pfc}"
            else:
                payload = pfc
            self._respond(200, payload)
        elif self.path == "/health":
            self._respond(200, self.engine.health(), content_type="application/json")
        elif self.path == "/fish":
            if self.engine.fish_file.exists():
                self._respond(200, self.engine.fish_file.read_text(encoding="utf-8"))
            else:
                self._respond(200, "Fish is empty.")
        elif self.path.startswith("/inbox/"):
            self._handle_inbox()
        elif self.path == "/emerge":
            result = self.engine._check_emergence()
            if result is None:
                self._respond(200, json.dumps({"signal": False,
                    "reason": "no cognitive-op data or no formations"}),
                    content_type="application/json")
            else:
                self._respond(200, json.dumps(result, indent=2),
                    content_type="application/json")
        elif self.path == "/growth":
            tracker = getattr(self.engine, "tracker", None)
            if tracker is None or not tracker.snapshots:
                self._respond(200,
                    "No growth data yet. POST /re-eat to run a maintenance cycle first.")
            else:
                self._respond(200, tracker.growth_summary())
        elif self.path == "/":
            self._respond(200, (
                "LiNafish — Your mind. Versioned. Everywhere.\n\n"
                "GET  /boot          — warm boot (primer + fish, read this first)\n"
                "GET  /pfc           — metacognitive overlay (formations)\n"
                "GET  /health        — engine stats\n"
                "GET  /emerge        — emergence metrics (ν, μ, ρ, Ψ, phase)\n"
                "GET  /growth        — R(n) curve, coupling density, dimension entropy\n"
                "GET  /fish          — raw fish.md\n"
                "POST /eat           — feed text {\"text\": \"...\"}\n"
                "POST /taste         — search {\"text\": \"...\"}\n"
                "POST /match         — tight recall {\"text\": \"...\"}\n"
                "POST /re-eat        — maintenance cycle (gardener + assessment + growth)\n"
                "POST /msg           — federation DM send\n"
                "GET  /inbox/<id>    — unread for a mind\n"
                "POST /msg/read      — mark read\n"
                "POST /shutdown      — graceful exit (nssm restarts)\n"
            ))
        else:
            self._respond(404, "Not found")

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length)) if length else {}
        except (json.JSONDecodeError, ValueError):
            self._respond(400, "Invalid JSON")
            return

        if self.path == "/eat":
            text = body.get("text", "")
            source = body.get("source", "session")
            if not text:
                self._respond(400, "Missing 'text' field")
                return
            result = self.engine.eat(text, source=source)
            self._respond(200, json.dumps(result), content_type="application/json")

        elif self.path == "/taste":
            text = body.get("text", "")
            top = body.get("top", 5)
            fmt = body.get("format", "text")
            if not text:
                self._respond(400, "Missing 'text' field")
                return
            if fmt == "json":
                self._respond(
                    200,
                    json.dumps(self.engine.taste_dict(text, top=top)),
                    content_type="application/json",
                )
            else:
                self._respond(200, self.engine.taste(text, top=top))

        elif self.path == "/match":
            text = body.get("text", "")
            top = body.get("top", 3)
            if not text:
                self._respond(400, "Missing 'text' field")
                return
            self._respond(200, self.engine.match(text, top=top))

        elif self.path == "/msg":
            self._handle_msg_send(body)

        elif self.path == "/msg/read":
            self._handle_msg_read(body)

        elif self.path == "/re-eat":
            result = self.engine.re_eat()
            self._respond(200, json.dumps(result, indent=2),
                content_type="application/json")

        elif self.path == "/shutdown":
            self._respond(200, "Shutting down — nssm will restart.")
            def _do_shutdown():
                try:
                    self.engine.flush_commit("http shutdown endpoint")
                except Exception as e:
                    print(f"flush_commit on shutdown: {e}", file=sys.stderr)
                os._exit(0)
            threading.Timer(0.5, _do_shutdown).start()

        else:
            self._respond(404, "Not found")

    # --- Federation DM endpoint handlers ----------------------------------

    def _handle_inbox(self):
        """GET /inbox/<mind_id>?limit=20&since=ts — unread messages for a mind."""
        parsed = urlparse(self.path)
        mind_id = parsed.path[len("/inbox/"):]
        if not mind_id:
            self._respond(400, "Missing mind_id")
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

        self._respond(200,
                      json.dumps({"messages": filtered, "count": len(filtered)}),
                      content_type="application/json")

    def _handle_msg_send(self, body: dict):
        """POST /msg — send a DM, also crystallize via fish.eat()."""
        sender = body.get("from", "")
        recipient = body.get("to", "")
        text = body.get("text", "")
        protocol = body.get("protocol", "fish-dm")

        if not sender or not recipient or not text:
            self._respond(400,
                          json.dumps({"error": "from, to, and text are required"}),
                          content_type="application/json")
            return

        ts = datetime.now(timezone.utc).isoformat()
        msg_id = _gen_msg_id()

        # Crystallize the DM text into the fish so it couples with everything.
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

        self._respond(200,
                      json.dumps({"status": "sent", "ts": ts, "id": msg_id}),
                      content_type="application/json")

    def _handle_msg_read(self, body: dict):
        """POST /msg/read — mark messages as read for a mind."""
        mind_id = body.get("mind_id", "")
        ids = body.get("ids", [])

        if not mind_id or not ids:
            self._respond(400,
                          json.dumps({"error": "mind_id and ids are required"}),
                          content_type="application/json")
            return

        ids_set = set(ids)
        msgs_path = _messages_file(self.engine)

        # Load+mark+save under lock so we don't race with concurrent /msg appends.
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

        self._respond(200, json.dumps({"marked": marked}),
                      content_type="application/json")

    # --- response + log helpers -------------------------------------------

    def _respond(self, code: int, body: str, content_type: str = "text/plain; charset=utf-8"):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))

    def log_message(self, format, *args):
        # Quiet logging — only errors
        if args and "404" not in str(args[0]):
            return


BIND_MAP = {
    "local": "127.0.0.1",
    "localhost": "127.0.0.1",
    "lan": "0.0.0.0",
    "wan": "0.0.0.0",
}


def serve_http(feed_path: Optional[Path] = None, state_dir: Optional[Path] = None,
               name: str = "linafish", port: int = 8900,
               vocab_path: Optional[Path] = None,
               host: Optional[str] = None,
               bind: str = "local"):
    """Serve the fish over HTTP.

    ``bind`` is the convenience shorthand mirroring ``converse``:
      - "local" binds to 127.0.0.1 (the default)
      - "lan"   binds to 0.0.0.0 — reachable from the LAN
      - "wan"   binds to 0.0.0.0 with an exposure warning

    ``host`` is a raw override. If set, it takes precedence over ``bind``
    for callers that need an exact interface IP. The plate-15 callers
    that passed ``host="0.0.0.0"`` keep working unchanged.
    """

    global _PRIMER
    _PRIMER = _load_primer()

    # HTTP /eat path uses periodic commit (every 100 eats) instead of per-eat
    # autocommit — per-eat fired a `git commit` that wedged the request loop
    # (25-30s on .140, indefinite on .67's 393K corpus, diagnosed 2026-05-01).
    # The N=100 cadence keeps state-dir git history advancing so rollback
    # remains possible (codex round-1 finding 2026-05-02: pure git_autocommit=
    # False stranded daemon history because daemons never call session_end).
    # Plus a SIGTERM/SIGINT handler below flushes uncommitted eats on
    # graceful shutdown so the final commit is captured even if N hasn't
    # rolled over.
    engine = FishEngine(state_dir=state_dir, name=name, commit_every_n_eats=100)

    def _flush_on_shutdown(signum, frame):
        # Reentrancy-safe: if a _save_state is in progress we cannot commit
        # right now without risking torn-state capture (codex round-2
        # 2026-05-02). Mark intent and let the in-flight save's finally
        # clause handle the commit + exit. If idle, flush + exit here.
        engine._shutdown_pending = True
        if not engine._save_in_progress:
            try:
                engine.flush_commit(f"http daemon shutdown (signal {signum})")
            except Exception as e:
                print(f"flush_commit failed on shutdown: {e}", file=sys.stderr)
            sys.exit(0)
    signal.signal(signal.SIGTERM, _flush_on_shutdown)
    signal.signal(signal.SIGINT, _flush_on_shutdown)

    if feed_path and feed_path.exists() and not engine.crystals:
        print(f"  Feeding: {feed_path}", file=sys.stderr)
        result = engine.eat_path(feed_path)
        print(f"  {result['crystals_added']} crystals, {result['formations']} formations", file=sys.stderr)

    FishHandler.engine = engine

    resolved_host = host if host else BIND_MAP.get(bind, bind)
    if bind == "wan" and not host:
        print("Warning: WAN bind exposes the fish to the internet.", file=sys.stderr)

    server = ThreadingHTTPServer((resolved_host, port), FishHandler)
    print(f"LiNafish HTTP: http://localhost:{port}", file=sys.stderr)
    print(f"  {len(engine.crystals)} crystals, {len(engine.formations)} formations", file=sys.stderr)
    print(f"  Fish: {engine.fish_file}", file=sys.stderr)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.", file=sys.stderr)
