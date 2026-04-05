"""
LiNafish MCP Server — Claude Code integration.

Thin wrapper around FishEngine. Exposes the fish as MCP tools
over stdio transport. For Claude users who want the tightest integration.

For other AIs, use http_server.py or just read the fish.md file directly.
"""

import json
import sys
import os
from pathlib import Path
from typing import Optional

from .engine import FishEngine


def _load_primer() -> str:
    """Load the AI primer document that teaches any LLM to read fish."""
    primer_path = Path(__file__).parent / "data" / "ai_primer.md"
    if primer_path.exists():
        return primer_path.read_text(encoding="utf-8", errors="replace")
    return ""


def serve_fish(feed_path: Optional[Path] = None, state_dir: Optional[Path] = None,
               name: str = "linafish", vocab_path: Optional[Path] = None):
    """Serve a fish as a stdio MCP server."""

    engine = FishEngine(state_dir=state_dir, name=name)
    primer = _load_primer()

    if feed_path and feed_path.exists():
        if engine.crystals:
            print(f"  State loaded ({len(engine.crystals)} crystals). Skipping re-ingest.", file=sys.stderr)
        else:
            print(f"  Feeding: {feed_path}", file=sys.stderr)
            _real_stdout = sys.stdout
            sys.stdout = sys.stderr
            try:
                result = engine.eat_path(feed_path)
            finally:
                sys.stdout = _real_stdout
            print(f"  {result['crystals_added']} crystals, {result['formations']} formations", file=sys.stderr)

    print(f"LiNafish MCP: {name}", file=sys.stderr)
    print(f"  {len(engine.crystals)} crystals, {len(engine.formations)} formations", file=sys.stderr)
    print(f"  Fish: {engine.fish_file}", file=sys.stderr)
    print(f"  Listening on stdio...", file=sys.stderr)

    server_info = {
        "name": f"linafish-{name}",
        "version": "0.3.0",
        "description": "Your mind. Versioned. Everywhere. Semantic intelligence via compression.",
    }

    tools = [
        {
            "name": "fish_pfc",
            "description": "Get the metacognitive overlay. Returns formations that represent HOW the user thinks. Read this at session start for a warm boot.",
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "fish_eat",
            "description": "Feed new content to the fish. Text gets crystallized into cognitive signatures and coupled with existing crystals. Formations grow as the fish learns.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "The text to feed the fish."},
                    "source": {"type": "string", "description": "Label for source (e.g. 'email', 'journal').", "default": "session"},
                },
                "required": ["text"],
            },
        },
        {
            "name": "fish_taste",
            "description": "Cross-corpus matching. Ask the fish what it knows about a topic. Returns crystals ranked by cognitive similarity.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "What to search for."},
                    "top": {"type": "integer", "description": "Number of results.", "default": 5},
                },
                "required": ["text"],
            },
        },
        {
            "name": "fish_match",
            "description": "Tight recall. Higher threshold than taste. Only strong cognitive matches.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Text to match."},
                    "top": {"type": "integer", "description": "Number of results.", "default": 3},
                },
                "required": ["text"],
            },
        },
        {
            "name": "fish_health",
            "description": "Fish engine stats.",
            "inputSchema": {"type": "object", "properties": {}},
        },
    ]

    def _warm_boot(args):
        """Return primer + fish formations as a warm-boot payload.
        The AI reads this once at session start and arrives knowing the person."""
        pfc = engine.pfc()
        if primer:
            return f"{primer}\n\n---\n\n# This Person's Fish\n\n{pfc}"
        return pfc

    handlers = {
        "fish_pfc": _warm_boot,
        "fish_eat": lambda args: json.dumps(engine.eat(args.get("text", ""), args.get("source", "session"))),
        "fish_taste": lambda args: engine.taste(args.get("text", ""), args.get("top", 5)),
        "fish_match": lambda args: engine.match(args.get("text", ""), args.get("top", 3)),
        "fish_health": lambda args: engine.health(),
    }

    _run_stdio_loop(server_info, tools, handlers)


def _run_stdio_loop(server_info: dict, tools: list, handlers: dict):
    """JSON-RPC stdio loop for MCP."""
    _fd_out = sys.stdout.fileno()

    def _write(obj):
        data = (json.dumps(obj) + "\n").encode("utf-8")
        os.write(_fd_out, data)

    while True:
        line = sys.stdin.readline()
        if not line:
            break
        line = line.strip()
        if not line:
            continue

        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            continue

        method = request.get("method", "")
        req_id = request.get("id")
        params = request.get("params", {})

        response = None

        if method == "initialize":
            response = {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": server_info,
                },
            }
        elif method == "notifications/initialized":
            continue
        elif method == "tools/list":
            response = {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"tools": tools},
            }
        elif method == "tools/call":
            tool_name = params.get("name", "")
            tool_args = params.get("arguments", {})
            handler = handlers.get(tool_name)

            if handler:
                try:
                    result_text = handler(tool_args)
                    response = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "content": [{"type": "text", "text": result_text}],
                        },
                    }
                except Exception as e:
                    response = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "content": [{"type": "text", "text": f"Error: {e}"}],
                            "isError": True,
                        },
                    }
            else:
                response = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": f"Unknown tool: {tool_name}"}],
                        "isError": True,
                    },
                }
        elif method == "ping":
            response = {"jsonrpc": "2.0", "id": req_id, "result": {}}

        if response:
            _write(response)
