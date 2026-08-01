"""/moment must not present a truncated assembly as a complete document.

Issue #45. `get_episode_source` was documented as returning "ALL of an
episode's text, unbounded" on the premise that crystals store text
untruncated. They do not: MAX_CRYSTAL_TEXT cuts at 32768 chars and there is
no *_sources.jsonl store to fall back to, so the dropped remainder is gone.
The endpoint returned the first 32KB of a book and reported success.

These tests pin the fidelity report, not a fix for the loss — nothing here
recovers text. They fail against the old behaviour because the old behaviour
had no `complete` field to be False.
"""

import json
import threading
import urllib.request
from http.server import ThreadingHTTPServer

from linafish import crystallizer_v3 as c3
from linafish.engine import FishEngine
from linafish.converse import ConverseHandler


def _engine(tmp_path, texts):
    e = FishEngine(state_dir=tmp_path, name="t", git_autocommit=False,
                   save_state_every_n_eats=1)
    for i, t in enumerate(texts):
        e.eat(t, episode_id="ep-1", episode_seq=i, episode_kind="session")
    return e


def _oversized():
    """A document past the cap, in prose so it crystallizes like real input."""
    para = ("The river road at dawn, fog over the water, gravel under the "
            "tires, the long quiet drive home through the bottoms. ")
    return para * (c3.MAX_CRYSTAL_TEXT // len(para) + 40)


SHORT = ("At the county fair the third corndog was the best one, hot mustard "
         "and a paper tray, fried batter still steaming.")


def test_whole_episode_reports_complete(tmp_path):
    src = _engine(tmp_path, [SHORT]).get_episode_source("ep-1")
    assert src.metadata["complete"] is True
    assert src.metadata["at_cap_crystal_count"] == 0
    assert "fidelity_warning" not in src.metadata


def test_at_cap_crystal_makes_the_episode_incomplete(tmp_path):
    """The case that mattered: a 70KB novel arriving as one capped crystal."""
    e = _engine(tmp_path, [_oversized()])
    src = e.get_episode_source("ep-1")

    capped = [c for c in e.fish.crystals if len(c.text) >= c3.MAX_CRYSTAL_TEXT]
    assert capped, "fixture failed to produce a crystal at the cap"

    assert src.metadata["complete"] is False
    assert src.metadata["at_cap_crystal_count"] == len(capped)
    assert src.metadata["max_crystal_text"] == c3.MAX_CRYSTAL_TEXT
    warning = src.metadata["fidelity_warning"]
    assert "truncated at ingest" in warning
    assert "#45" in warning


def test_partial_truncation_is_not_rounded_to_whole(tmp_path):
    """One capped crystal among intact ones still marks the episode incomplete.

    The old surface would have returned this assembly as authoritative
    because most of it was fine.
    """
    src = _engine(tmp_path, [SHORT, _oversized(), SHORT]).get_episode_source("ep-1")
    assert src.metadata["complete"] is False
    assert src.metadata["at_cap_crystal_count"] >= 1
    assert src.metadata["crystal_count"] > src.metadata["at_cap_crystal_count"]


def test_moment_http_response_carries_the_warning(tmp_path):
    """A federation peer reading /moment over the wire must see it too —
    the metadata is the only signal, since the body still looks like prose."""
    ConverseHandler.engine = _engine(tmp_path, [_oversized()])
    ConverseHandler.mind_name = "test"
    ConverseHandler.auth_token = None
    ConverseHandler.expose_full_sources = True
    srv = ThreadingHTTPServer(("127.0.0.1", 0), ConverseHandler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        url = f"http://127.0.0.1:{srv.server_address[1]}/moment/ep-1"
        with urllib.request.urlopen(url, timeout=5) as r:
            assert r.status == 200
            data = json.loads(r.read())
        assert data["metadata"]["complete"] is False
        assert "fidelity_warning" in data["metadata"]
    finally:
        srv.shutdown()
        srv.server_close()
