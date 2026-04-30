"""Regression tests for the 1.2.1 patch release.

Two fixes pinned here:

1. ``FishEngine.taste_dict`` returns the structured shape consumers
   (federation guppies, agents) expect, and ``/taste`` honors a
   ``format=json`` body field. The 1.2.0 bug: ``linafish.guppy.hunt_room``
   posted to ``/taste`` and looked for ``data["matches"]``, but the
   endpoint returned plain text — ``_post_json`` failed parse, hunt_room
   silently returned 0 every cycle. THX caught this on .67 reattach.

2. ``paho-mqtt 2.x`` compatibility — paho 2.0 made
   ``callback_api_version`` a required ``mqtt.Client(...)`` argument.
   Code targeting 1.x raised ``ValueError`` on 2.x. Both
   ``linafish.daemon`` and ``linafish.listener`` use a version-shim
   that detects ``mqtt.CallbackAPIVersion`` at runtime.
"""

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from linafish.engine import FishEngine


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_engine(state_dir):
    return FishEngine(
        state_dir=Path(state_dir),
        name="v121_taste_test",
        git_autocommit=False,
    )


def _seed(engine, n=20):
    """Seed the engine with enough varied content to freeze + return matches."""
    patterns = [
        "The federation room is alive and the fish keeps eating crystals from MQTT.",
        "Captain held the substrate this morning while the cut-over landed cleanly.",
        "Olorina noticed that the vocabulary had grown beyond the seed planting.",
        "Anchor wrote down the three real follow-ups before they could evaporate.",
        "The room learned to notice its own shape under the gardener.",
        "A formation grew out of repeated attention to the same conversational shape.",
        "Crystals carried cognitive vectors and MI vectors in parallel as v3 design.",
        "The seed era of fifty tokens preceded the grown era of two hundred tokens.",
        "Each eat phase one is learn co-occurrence, phase two is freeze and crystallize.",
        "Federation messaging endpoints land in master so guppies can find each other.",
    ]
    for i in range(n):
        engine.eat(patterns[i % len(patterns)] + f" iteration {i}.",
                   source=f"v121test/seed_{i}")


# ---------------------------------------------------------------------------
# taste_dict — structured response
# ---------------------------------------------------------------------------

def test_taste_dict_empty_fish_returns_ok_false():
    with tempfile.TemporaryDirectory() as tmp:
        engine = _make_engine(tmp)
        result = engine.taste_dict("anything")
        assert result["ok"] is False
        assert result["reason"] == "empty_fish"
        assert result["matches"] == []
        assert result["total_crystals"] == 0


def test_taste_dict_returns_structured_matches():
    with tempfile.TemporaryDirectory() as tmp:
        engine = _make_engine(tmp)
        _seed(engine, n=30)

        result = engine.taste_dict("federation room crystals", top=5)

        # Shape pin
        assert "ok" in result
        assert "query_keywords" in result
        assert "match_count" in result
        assert "total_crystals" in result
        assert "matches" in result

        # When ok=True, matches should be a list of dicts with the
        # contract guppies depend on.
        if result["ok"] and result["matches"]:
            m = result["matches"][0]
            assert "id" in m
            assert "text" in m
            assert "source" in m
            assert "ts" in m
            assert "relevance" in m
            assert "keywords" in m
            # relevance is a number, not a string — important for guppy
            # which sorts by it.
            assert isinstance(m["relevance"], (int, float))


def test_taste_text_still_works():
    """Backward-compat: existing text-rendering callers see the same shape."""
    with tempfile.TemporaryDirectory() as tmp:
        engine = _make_engine(tmp)
        _seed(engine, n=30)

        text = engine.taste("federation room", top=3)

        assert isinstance(text, str)
        # Either we got a "Query keywords:" intro (matches found) or
        # one of the documented terminal messages. Either way, the
        # text path returns a str — never a dict.
        terminal_phrases = [
            "Query keywords:",
            "Fish is empty",
            "Fish hasn't learned",
            "No resonance found",
            "Text too short",
        ]
        assert any(phrase in text for phrase in terminal_phrases), (
            f"taste() returned unexpected text: {text[:200]}"
        )


def test_taste_dict_match_count_is_total_resonance():
    """match_count is total resonance hits, not just the top-N returned."""
    with tempfile.TemporaryDirectory() as tmp:
        engine = _make_engine(tmp)
        _seed(engine, n=30)

        result_top3 = engine.taste_dict("federation room crystals", top=3)
        result_top10 = engine.taste_dict("federation room crystals", top=10)

        # Same query, same corpus → same match_count regardless of top.
        # matches list length capped at top.
        assert result_top3["match_count"] == result_top10["match_count"]
        assert len(result_top3["matches"]) <= 3
        assert len(result_top10["matches"]) <= 10


def test_taste_dict_is_json_serializable():
    """The return value must round-trip through json.dumps cleanly."""
    with tempfile.TemporaryDirectory() as tmp:
        engine = _make_engine(tmp)
        _seed(engine, n=20)
        result = engine.taste_dict("federation", top=5)
        # If this raises, something non-serializable leaked in.
        encoded = json.dumps(result)
        decoded = json.loads(encoded)
        assert decoded["ok"] == result["ok"]


# ---------------------------------------------------------------------------
# paho-mqtt version shim — static guard
# ---------------------------------------------------------------------------

def test_daemon_has_paho_callback_api_shim():
    """linafish.daemon must use the version-detect shim, not bare 1.x init."""
    src = (
        Path(__file__).resolve().parent.parent
        / "linafish" / "daemon.py"
    ).read_text(encoding="utf-8")
    assert 'hasattr(mqtt, "CallbackAPIVersion")' in src, (
        "daemon.py is missing the paho 2.x compat shim. "
        "Re-add it after `import paho.mqtt.client as mqtt`."
    )
    assert "callback_api_version" in src, (
        "daemon.py shim must pass callback_api_version to mqtt.Client()"
    )


def test_listener_has_paho_callback_api_shim():
    """linafish.listener must use the version-detect shim, not bare 1.x init."""
    src = (
        Path(__file__).resolve().parent.parent
        / "linafish" / "listener.py"
    ).read_text(encoding="utf-8")
    assert 'hasattr(mqtt, "CallbackAPIVersion")' in src, (
        "listener.py is missing the paho 2.x compat shim."
    )
    assert "callback_api_version" in src, (
        "listener.py shim must pass callback_api_version to mqtt.Client()"
    )


# ---------------------------------------------------------------------------
# guppy — uses format=json
# ---------------------------------------------------------------------------

def test_guppy_hunt_room_requests_json_format():
    """guppy.hunt_room must POST format=json so the response is parseable."""
    src = (
        Path(__file__).resolve().parent.parent
        / "linafish" / "guppy.py"
    ).read_text(encoding="utf-8")
    # Look for the format=json kwarg in the hunt_room POST body.
    assert '"format": "json"' in src, (
        "guppy.hunt_room must POST format=json — the 1.2.0 bug was that "
        "/taste returned text but hunt_room expected JSON."
    )
