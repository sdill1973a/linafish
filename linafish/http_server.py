"""
LiNafish HTTP Server — the universal interface.

Tiny HTTP server. Zero dependencies beyond stdlib. Any AI that can fetch
a URL can read the fish. Serves the same engine as the MCP server.

    GET  /pfc     — formations (the metacognitive overlay)
    GET  /health  — engine stats
    POST /eat     — feed text. Accepts JSON body or form-encoded data:
                    {"text": "...", "source": "...",
                     "chain_id": "...", "chain_seq": 123}
                    chain_id/chain_seq are optional — chaincode marriage spec
                    2026-03-25. When present, the crystal records its position
                    in the chaincode chain for temporal coupling. The form-
                    encoded path also accepts ``name`` as a synonym for
                    ``source`` (legacy field — pre-1.x feeders use it).
    POST /taste   — cross-corpus match (JSON body or form: {"text": "...", "top": 5})
    POST /match   — tight recall (JSON body: {"text": "...", "top": 3})
    GET  /fish    — raw fish.md contents

Usage:
    linafish http --feed ./my-docs
    linafish http --feed ./my-docs --port 8900
"""

import json
import sys
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Optional

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
        elif self.path == "/":
            self._respond(200, (
                "LiNafish — Your mind. Versioned. Everywhere.\n\n"
                "GET  /boot   — warm boot (primer + fish, read this first)\n"
                "GET  /pfc    — metacognitive overlay (formations)\n"
                "GET  /health — engine stats\n"
                "GET  /fish   — raw fish.md\n"
                "POST /eat    — feed text {\"text\": \"...\"}\n"
                "POST /taste  — search {\"text\": \"...\"}\n"
                "POST /match  — tight recall {\"text\": \"...\"}\n"
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
        # pre-1.x feeders the moment we deploy 1.x to .67 is a worse
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
            if not text:
                self._respond(400, "Missing 'text' field")
                return
            self._respond(200, self.engine.taste(text, top=top))

        elif self.path == "/match":
            text = body.get("text", "")
            top = body.get("top", 3)
            if not text:
                self._respond(400, "Missing 'text' field")
                return
            self._respond(200, self.engine.match(text, top=top))

        else:
            self._respond(404, "Not found")

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

    engine = FishEngine(state_dir=state_dir, name=name)

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
