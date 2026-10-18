"""The MCP lane carries the grounding band (2026-10-18). AGENTS.md's central instruction is "honor the band";
before this, fish_taste returned pretty text with no band, so a Claude Code agent could not follow its own briefing."""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from linafish.engine import FishEngine  # noqa: E402
from linafish.server import build_handlers  # noqa: E402

DOCS = [
    "The river carried the lantern downstream past the old mill while the teacher wrote about memory.",
    "Caroline walked the ridge at dawn; the lantern in her hand did not dim.",
    "A compression protocol carries more with less: the key is small, the body is whole.",
    "Breakfast was eggs and coffee; the dog came home safe before noon.",
]


def test_fish_taste_returns_json_with_grounding_band():
    with tempfile.TemporaryDirectory() as td:
        e = FishEngine(state_dir=Path(td), name="mcp-test")
        for d in DOCS * 3:
            e.eat(d, source="test")
        h = build_handlers(e)
        assert set(h) == {"fish_pfc", "fish_eat", "fish_taste", "fish_match", "fish_health"}
        r = json.loads(h["fish_taste"]({"text": DOCS[1], "top": 3}))
        assert r["ok"]
        # the band is the point of this lane change; a tiny fish may rank nothing above the dense floor, so the
        # match list is checked only when it has members
        assert r["grounding"]["band"] in ("grounded", "thin", "ungrounded", "thin-recent")
        if r["matches"]:
            assert "lantern" in r["matches"][0]["text"].lower()
        assert isinstance(h["fish_pfc"]({}), str)
