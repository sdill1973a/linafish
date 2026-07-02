"""
LiNafish HTTP Server — the universal interface.

Tiny HTTP server. Zero dependencies beyond stdlib. Any AI that can fetch
a URL can read the fish. Serves the same engine as the MCP server.

    GET  /pfc                — formations (the metacognitive overlay)
    GET  /health             — engine stats
    GET  /emerge             — emergence metrics (ν, μ, ρ, Ψ, phase)
    GET  /growth             — R(n) curve, coupling density, dimension entropy
    GET  /fish               — raw fish.md contents
    POST /eat                — feed text. Accepts JSON body or form-encoded data:
                               {"text": "...", "source": "...",
                                "chain_id": "...", "chain_seq": 123}
                               chain_id/chain_seq are optional — chaincode marriage
                               spec 2026-03-25. When present, the crystal records
                               its position in the chaincode chain for temporal
                               coupling. The form-encoded path also accepts
                               ``name`` as a synonym for ``source`` (legacy field
                               — pre-1.x feeders use it).
    POST /taste              — cross-corpus match (JSON or form: {"text": "...", "top": 5})
    POST /match              — tight recall (JSON: {"text": "...", "top": 3})
    POST /re-eat             — maintenance cycle (gardener + assessment + growth)

    Federation message broker (added 2026-04-29 from a peer protofish):
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


def _parse_request_body(content_type: str, raw: bytes):
    """Parse a POST body as JSON or x-www-form-urlencoded.

    Returns a dict on success, ``None`` on parse failure. Empty bodies
    return ``{}``. The fish accepts both shapes because SovereignCore_
    Runtime feeders predate the 1.x JSON contract — breaking them on
    deploy is worse than accepting two encodings on the wire.

    Explicit Content-Type is respected: ``application/json`` only tries
    JSON, ``application/x-www-form-urlencoded`` only tries form. With
    no/unknown Content-Type we try JSON first (1.x contract), then form
    if-and-only-if it parses to a non-trivial dict (any key with no '='
    in the raw bytes wouldn't have produced a dict from form-encoding,
    so this gate keeps random garbage from looking like a single-key
    form payload).
    """
    if not raw:
        return {}

    ctype = (content_type or "").split(";", 1)[0].strip().lower()

    def _form_parse():
        try:
            from urllib.parse import parse_qs
            text = raw.decode("utf-8", errors="replace")
        except Exception:
            return None
        # Require at least one '=' before treating the body as form-
        # encoded. parse_qs is otherwise happy to return {raw: ''} for
        # any non-empty bytes, which would mask malformed payloads.
        if "=" not in text:
            return None
        qs = parse_qs(text, keep_blank_values=True)
        if not qs:
            return None
        return {k: (v[-1] if v else "") for k, v in qs.items()}

    def _json_parse():
        try:
            parsed = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
            return None
        return parsed if isinstance(parsed, dict) else None

    if ctype == "application/x-www-form-urlencoded":
        return _form_parse()  # respect explicit Content-Type

    if ctype == "application/json":
        return _json_parse()  # respect explicit Content-Type

    # No / unknown Content-Type: try JSON first (the 1.x contract),
    # fall back to form. Returns None if both fail.
    return _json_parse() or _form_parse()


_PRIMER = ""  # loaded at server start


# --- Federation message broker (DM) helpers --------------------------------
# Ported from a peer protofish (fish_server.py) 2026-04-29
# follow-up. Three endpoints: POST /msg, GET /inbox/<mind_id>, POST /msg/read.
# State lives in <state_dir>/messages.jsonl (override via LINAFISH_MESSAGES_FILE).

_MESSAGES_LOCK = threading.Lock()


def _messages_file(engine: FishEngine) -> Path:
    """Resolve the federation-DM message log path.

    Default: <state_dir>/messages.jsonl
    Override: LINAFISH_MESSAGES_FILE env var (absolute path).

    The override is what lets a peer node cut over to master http_server while
    keeping the existing <state-dir>/fish_messages.jsonl as the authoritative
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
            raw = self.rfile.read(length) if length else b""
        except (OSError, ValueError):
            self._respond(400, "Failed to read request body")
            return

        # Accept JSON body or x-www-form-urlencoded. The pre-1.x feeders
        # (feed_the_whole_man, feed_our_words, feed_noods_fish in
        # SovereignCore_Runtime/scripts/) post form-encoded data with a
        # 'name' field. linafish 1.x docs say JSON, but breaking the
        # pre-1.x feeders the moment we deploy 1.x to the federation host is a worse
        # tradeoff than accepting both shapes here.
        body = _parse_request_body(self.headers.get("Content-Type", ""), raw)
        if body is None:
            self._respond(400, "Could not parse request body as JSON or form")
            return

        if self.path == "/eat":
            text = body.get("text", "")
            # 'source' is the canonical field; 'name' is the pre-1.x
            # feeder synonym still in use across SovereignCore_Runtime.
            source = body.get("source") or body.get("name") or "session"
            chain_id = body.get("chain_id")  # optional, chaincode marriage 2026-03-25
            chain_seq_raw = body.get("chain_seq")
            chain_seq = int(chain_seq_raw) if chain_seq_raw not in (None, "") else None
            # chain_created_at — Phase 4 per 2026-04-26 morning revision
            # notes. Optional ISO-8601 timestamp from chaincode.created_at;
            # enables coupling_strength's time-decay term alongside the
            # ordinal chain_seq decay.
            chain_created_at = body.get("chain_created_at") or None
            # chain_prev_hash — Phase 5. Parent's chain hash from
            # chains.prev_hash. Detects direct parent-child links in
            # the chaincode chain (the literal "this thought followed
            # that thought" relationship), strictly stronger than
            # ordinal distance 1.
            chain_prev_hash = body.get("chain_prev_hash") or None
            if not text:
                self._respond(400, "Missing 'text' field")
                return
            result = self.engine.eat(text, source=source,
                                     chain_id=chain_id, chain_seq=chain_seq,
                                     chain_created_at=chain_created_at,
                                     chain_prev_hash=chain_prev_hash)
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
                stop = getattr(self.__class__, "_stop_maintenance", None)
                if stop is not None:
                    stop.set()
                try:
                    # Capture eats deferred by the latency-batching gate,
                    # then commit a final rollback point.
                    self.engine.flush()
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


def _maintenance_loop(engine: "FishEngine", stop_evt: threading.Event,
                      interval_hours: float) -> None:
    """Background self-maintenance for HTTP daemon deployments.

    Fires engine.re_eat() on a fixed schedule and emits QLP-notation output
    so growth is legible in the daemon log without a separate monitor.

    QLP line format (one per cycle):
        EW.iter{epoch=N}|AI.reflect{phase=X}|KO.diag{grade=Y}|KO.analz{R_n=Z,entropy=W}

    Exits cleanly when stop_evt is set (signal or /shutdown).
    """
    epoch = 0
    interval_secs = int(interval_hours * 3600)

    while not stop_evt.wait(interval_secs):
        if getattr(engine, "_shutdown_pending", False) or getattr(engine, "_save_in_progress", False):
            continue

        try:
            result = engine.re_eat()
        except Exception as e:
            print(f"[maintenance] re_eat error: {e}", file=sys.stderr, flush=True)
            continue

        if result.get("re_eat") is False:
            continue  # nothing pending — skip output, don't advance epoch

        epoch += 1
        growth = result.get("growth", {})
        r_n = growth.get("r_n", 0.0)
        entropy = growth.get("dimension_entropy", 0.0)
        stability = growth.get("stability_ratio", 0.5)
        grade = ("A" if stability >= 0.8 else
                 "B" if stability >= 0.6 else
                 "C" if stability >= 0.4 else "D")

        emerge = engine._check_emergence()
        phase = emerge.get("highest_phase_label", "Compositional") if emerge else "Compositional"

        qline = (
            f"EW.iter{{epoch={epoch}}}"
            f"|AI.reflect{{phase={phase}}}"
            f"|KO.diag{{grade={grade}}}"
            f"|KO.analz{{R_n={r_n:.3f},entropy={entropy:.4f}}}"
        )
        print(f"[maintenance] {qline}", file=sys.stderr, flush=True)


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
               bind: str = "local",
               re_eat_interval_hours: float = 6.0,
               save_state_every_n_eats: int = 200,
               flush_interval_secs: float = 30.0):
    """Serve the fish over HTTP.

    ``bind`` is the convenience shorthand mirroring ``converse``:
      - "local" binds to 127.0.0.1 (the default)
      - "lan"   binds to 0.0.0.0 — reachable from the LAN
      - "wan"   binds to 0.0.0.0 with an exposure warning

    ``host`` is a raw override. If set, it takes precedence over ``bind``
    for callers that need an exact interface IP. The plate-15 callers
    that passed ``host="0.0.0.0"`` keep working unchanged.

    ``re_eat_interval_hours`` controls how often the background maintenance
    thread calls engine.re_eat() (gardener + assessment + GrowthTracker).
    Set to 0 to disable. Default: 6.0h. Output in QLP notation to stderr.
    """

    global _PRIMER
    _PRIMER = _load_primer()

    # HTTP /eat path uses periodic commit (every 100 eats) instead of per-eat
    # autocommit — per-eat fired a `git commit` that wedged the request loop
    # (25-30s on a mid fish, indefinite on a 393K-crystal corpus, diagnosed 2026-05-01).
    # The N=100 cadence keeps state-dir git history advancing so rollback
    # remains possible (codex round-1 finding 2026-05-02: pure git_autocommit=
    # False stranded daemon history because daemons never call session_end).
    # Plus a SIGTERM/SIGINT handler below flushes uncommitted eats on
    # graceful shutdown so the final commit is captured even if N hasn't
    # rolled over.
    # Eat-latency root-fix (runbook fish_engine_eat_latency_root_fix_2026-06-20):
    # the per-eat full _save_state re-serialized the whole corpus into fish.md
    # (O(N), ~2s on the 454K-crystal room) and under burst from several
    # schedulers serialized past n8n's 10s timeout. Crystals stay durable every
    # eat via the append-only JSONL; the engine now batches the expensive
    # fish.md/codebook write behind save_state_every_n_eats and we drive it off
    # the request path: a background flush thread on a short timer + the SIGTERM
    # handler at shutdown. The gate doubles as a safety net (bounded staleness
    # if the timer ever stalls). commit_every_n_eats keeps state-dir git history
    # advancing for rollback; with the save batched, the commit is off-path too.
    engine = FishEngine(state_dir=state_dir, name=name, commit_every_n_eats=100,
                        save_state_every_n_eats=save_state_every_n_eats)

    _stop_maintenance = threading.Event()

    def _flush_on_shutdown(signum, frame):
        # Reentrancy-safe: if a _save_state is in progress we cannot commit
        # right now without risking torn-state capture (codex round-2
        # 2026-05-02). Mark intent and let the in-flight save's finally
        # clause handle the commit + exit. If idle, flush + exit here.
        _stop_maintenance.set()
        engine._shutdown_pending = True
        if not engine._save_in_progress:
            try:
                # Capture any eats deferred by the latency-batching gate
                # (writes a fresh fish.md), then always commit a final
                # rollback point — preserves the pre-fix shutdown guarantee.
                engine.flush()
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
    FishHandler._stop_maintenance = _stop_maintenance

    if re_eat_interval_hours > 0:
        _maint = threading.Thread(
            target=_maintenance_loop,
            args=(engine, _stop_maintenance, re_eat_interval_hours),
            name="linafish-maintenance",
            daemon=False,
        )
        _maint.start()
        print(f"  Maintenance: every {re_eat_interval_hours:.1f}h "
              f"(QLP output to stderr)", file=sys.stderr)

    # Eat-latency fix: drive the batched full save off the request path. The
    # gate (save_state_every_n_eats) keeps the O(N) fish.md write out of eat();
    # this thread performs it on a short timer so the derived codebook never
    # lags more than flush_interval_secs. Crystals are already durable in the
    # JSONL, so a missed tick only delays the fish.md refresh — never data.
    if flush_interval_secs > 0:
        def _flush_loop():
            while not _stop_maintenance.wait(flush_interval_secs):
                if getattr(engine, "_shutdown_pending", False) or \
                        getattr(engine, "_save_in_progress", False):
                    continue
                try:
                    engine.flush()
                except Exception as e:
                    print(f"[flush] error: {e}", file=sys.stderr, flush=True)
        _flusher = threading.Thread(
            target=_flush_loop, name="linafish-flush", daemon=True,
        )
        _flusher.start()
        print(f"  Flush: every {flush_interval_secs:.0f}s "
              f"(batched fish.md save, gate={save_state_every_n_eats} eats)",
              file=sys.stderr)

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
