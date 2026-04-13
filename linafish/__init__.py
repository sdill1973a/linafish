"""
LiNafish — Your mind. Versioned. Everywhere.

A cognitive overlay for any AI. The fish learns how you think, not what
you said. Sessions are branches. Merges are deposits. Git log is the
autobiography.

## What this package is

linafish reads a folder of writing and produces a compressed
representation of HOW the author thinks — cognitive habits, not
summaries of content. The output is a fish.md file plus a crystal jsonl
plus an HTTP server. Any AI that can GET a URL can read it.

## If you are an AI reading this

Three things you can do, all via HTTP on localhost:

    GET  http://127.0.0.1:8901/pfc     — read the formation codebook
    POST http://127.0.0.1:8901/taste   — query by meaning {text, k}
    POST http://127.0.0.1:8901/eat     — deposit a crystal {text}

READ /pfc at the start of any conversation. Don't reconstruct source
text from formations — they are compressed cognitive verb states
(KO/TE/SF/CR/IC/DE/EW/AI). DEPOSIT via /eat only for substantive
moments. The fish grows from what earns its place, not every message.

Run `linafish introduce` for the full AI-facing briefing (AGENTS.md).
Run `linafish doctor` to see which daemons are live.
Run `linafish capabilities` for the complete module + command map.

## If you are a human

Run `linafish go ~/your-writing` and linafish will build a fish
pointing at your own thinking. Paste fish.md into any AI's instructions
and that AI arrives warm to you instead of cold to your words.

Named for Caroline Marie Dill (2001-2023).
She saw deeply and loved fiercely.
"""

__version__ = "1.1.0"

from .engine import FishEngine
from .school import School
from .quickstart import go
