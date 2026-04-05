"""
LiNafish HTTP Server — the universal interface.

Tiny HTTP server. Zero dependencies beyond stdlib. Any AI that can fetch
a URL can read the fish. Serves the same engine as the MCP server.

    GET  /pfc     — formations (the metacognitive overlay)
    GET  /health  — engine stats
    POST /eat     — feed text (JSON body: {"text": "...", "source": "..."})
    POST /taste   — cross-corpus match (JSON body: {"text": "...", "top": 5})
    POST /match   — tight recall (JSON body: {"text": "...", "top": 3})
    GET  /fish    — raw fish.md contents

Usage:
    linafish http --feed ./my-docs
    linafish http --feed ./my-docs --port 8900
"""

import json
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Optional

from .engine import FishEngine


def _load_primer() -> str:
    """Load the AI primer document."""
    primer_path = Path(__file__).parent / "data" / "ai_primer.md"
    if primer_path.exists():
        return primer_path.read_text(encoding="utf-8", errors="replace")
    return ""


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


def serve_http(feed_path: Optional[Path] = None, state_dir: Optional[Path] = None,
               name: str = "linafish", port: int = 8900,
               vocab_path: Optional[Path] = None):
    """Serve the fish over HTTP."""

    global _PRIMER
    _PRIMER = _load_primer()

    engine = FishEngine(state_dir=state_dir, name=name)

    if feed_path and feed_path.exists() and not engine.crystals:
        print(f"  Feeding: {feed_path}", file=sys.stderr)
        result = engine.eat_path(feed_path)
        print(f"  {result['crystals_added']} crystals, {result['formations']} formations", file=sys.stderr)

    FishHandler.engine = engine

    server = HTTPServer(("127.0.0.1", port), FishHandler)
    print(f"LiNafish HTTP: http://localhost:{port}", file=sys.stderr)
    print(f"  {len(engine.crystals)} crystals, {len(engine.formations)} formations", file=sys.stderr)
    print(f"  Fish: {engine.fish_file}", file=sys.stderr)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.", file=sys.stderr)
