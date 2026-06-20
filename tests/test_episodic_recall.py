"""Episodic recall layer — Cal's SPEC_v0.2 (arena-engine#21).

Covers the v1 core: new Crystal episode fields (round-trip), the engine
episode index built on eat, load_episode/walk/scoring, recall_episodic with
dedup + orphan handling, and backward compatibility on legacy fish.
"""

from datetime import datetime, timezone
from pathlib import Path

from linafish.engine import FishEngine
from linafish import episodic
from linafish.episodic import EpisodicMoment, load_episode, walk, score_moment


def _engine(tmp_path):
    return FishEngine(state_dir=tmp_path, name="t", git_autocommit=False,
                      save_state_every_n_eats=1)


# Distinct passages so gamma matching can separate them.
DOCS = {
    "harness": "We wired the playtest harness for the arena combat engine, "
               "logging every spawn and router decision to the registry seam.",
    "corndog": "At the county fair the third corndog was the best one, hot "
               "mustard and a paper tray, fried batter still steaming.",
    "river":   "The river road at dawn, fog over the water, gravel under the "
               "tires, the long quiet drive home through the bottoms.",
}


def test_episode_fields_roundtrip(tmp_path):
    """episode_id/episode_seq/episode_kind persist to JSONL and reload."""
    e = _engine(tmp_path)
    e.eat(DOCS["harness"], source="s", episode_id="ep-1", episode_seq=0,
          episode_kind="session")
    c = e.fish.crystals[-1]
    assert c.episode_id == "ep-1"
    assert c.episode_seq == 0
    assert c.episode_kind == "session"
    # Cold reload — fields survive the JSONL round-trip.
    e2 = FishEngine(state_dir=tmp_path, name="t", git_autocommit=False)
    c2 = e2.fish.crystals[-1]
    assert c2.episode_id == "ep-1"
    assert c2.episode_seq == 0
    assert c2.episode_kind == "session"


def test_index_built_on_eat_and_load_episode(tmp_path):
    """Eating with episode_id grows the index; load_episode returns the
    crystals in episode_seq order."""
    e = _engine(tmp_path)
    e.eat(DOCS["harness"], episode_id="ep-1", episode_seq=0, episode_kind="session")
    e.eat(DOCS["corndog"], episode_id="ep-1", episode_seq=1, episode_kind="session")
    e.eat(DOCS["river"],   episode_id="ep-1", episode_seq=2, episode_kind="session")
    assert "ep-1" in e.episode_index
    assert len(e.episode_index["ep-1"]["ordered_crystal_ids"]) == 3
    by_id = {c.id: c for c in e.fish.crystals}
    ep = load_episode("ep-1", e.episode_index, by_id)
    assert [c.episode_seq for c in ep] == [0, 1, 2]


def test_index_rebuilds_from_scan_on_reload(tmp_path):
    """A fresh engine rebuilds the episode index from the crystal scan
    (crystals are authoritative; the index file is a cache)."""
    e = _engine(tmp_path)
    e.eat(DOCS["harness"], episode_id="ep-A", episode_seq=0, episode_kind="session")
    e.eat(DOCS["corndog"], episode_id="ep-B", episode_seq=0, episode_kind="session")
    e.eat(DOCS["river"],   episode_id="ep-A", episode_seq=1, episode_kind="session")
    e2 = FishEngine(state_dir=tmp_path, name="t", git_autocommit=False)
    assert set(e2.episode_index.keys()) == {"ep-A", "ep-B"}
    assert len(e2.episode_index["ep-A"]["ordered_crystal_ids"]) == 2


def test_walk_before_after_and_radius():
    """walk() returns ordered neighbors bounded by max_before/max_after."""
    class C:
        def __init__(self, i):
            self.id = f"c{i}"
            self.episode_id = "ep"
            self.episode_seq = i
            self.episode_kind = "session"
            self.chain_created_at = None
            self.ts = f"2026-06-20T00:00:{i:02d}+00:00"
            self.text = f"crystal {i}"
    episode = [C(i) for i in range(7)]
    pivot = episode[3]
    m = walk(pivot, episode, max_before=2, max_after=2, time_horizon_sec=10**9)
    assert [c.id for c in m.before] == ["c1", "c2"]
    assert [c.id for c in m.after] == ["c4", "c5"]
    assert m.pivots[0].id == "c3"
    assert m.episode_id == "ep"


def test_walk_orphan_when_no_episode():
    class C:
        id = "x"
        episode_id = None
        episode_kind = None
        chain_created_at = None
        ts = "2026-06-20T00:00:00+00:00"
        text = "lonely crystal"
    m = walk(C(), None)
    assert m.episode_id == episodic.ORPHAN
    assert m.before == [] and m.after == []


def test_score_orphan_penalized_vs_dense():
    now = datetime(2026, 6, 20, tzinfo=timezone.utc)
    dense = EpisodicMoment(episode_id="ep", episode_kind="session", pivots=[1],
                           before=[1, 2, 3], after=[1, 2],
                           created_at="2026-06-20T00:00:00+00:00")
    orphan = EpisodicMoment(episode_id=episodic.ORPHAN, episode_kind="unknown",
                            pivots=[1], created_at="2026-06-20T00:00:00+00:00")
    s_dense = score_moment(dense, pivot_gamma=0.8, now=now)
    s_orphan = score_moment(orphan, pivot_gamma=0.8, now=now)
    assert s_dense > s_orphan  # density bonus + no orphan penalty


def test_recall_episodic_returns_moment_with_context(tmp_path):
    """End-to-end: a query matching the middle crystal of an episode returns
    a moment with before/after neighbors."""
    e = _engine(tmp_path)
    e.eat(DOCS["harness"], episode_id="ep-1", episode_seq=0, episode_kind="session")
    e.eat(DOCS["corndog"], episode_id="ep-1", episode_seq=1, episode_kind="session")
    e.eat(DOCS["river"],   episode_id="ep-1", episode_seq=2, episode_kind="session")
    moments = e.recall_episodic("the third corndog at the fair, hot mustard", k=3)
    assert moments
    top = moments[0]
    assert isinstance(top, EpisodicMoment)
    # The corndog crystal is seq 1 — it has one before and one after.
    all_ids = [c.id for c in (top.before + top.pivots + top.after)]
    assert len(all_ids) >= 2
    assert top.episode_id == "ep-1"


def test_recall_episodic_dedups_same_episode(tmp_path):
    """Multiple pivots in one episode collapse to a single moment whose
    pivots list holds them all (walked from the earliest)."""
    e = _engine(tmp_path)
    # Two near-identical harness crystals in the same episode → both match.
    e.eat(DOCS["harness"], episode_id="ep-1", episode_seq=0, episode_kind="session")
    e.eat(DOCS["river"],   episode_id="ep-1", episode_seq=1, episode_kind="session")
    e.eat(DOCS["harness"] + " And again the same registry seam.",
          episode_id="ep-1", episode_seq=2, episode_kind="session")
    moments = e.recall_episodic("playtest harness registry seam spawn router", k=5)
    ep1 = [m for m in moments if m.episode_id == "ep-1"]
    assert len(ep1) == 1, "same-episode pivots must collapse into one moment"


def test_recall_episodic_orphan_on_legacy_fish(tmp_path):
    """A fish with no episode metadata still answers — orphan moments, no
    crash (backward compatibility, spec §10)."""
    e = _engine(tmp_path)
    e.eat(DOCS["harness"])   # no episode_id
    e.eat(DOCS["corndog"])
    moments = e.recall_episodic("playtest harness registry seam", k=3)
    assert moments
    assert all(m.episode_id == episodic.ORPHAN for m in moments)


def test_recall_episodic_include_source(tmp_path):
    """include_source=True assembles a source_excerpt from crystal text."""
    e = _engine(tmp_path)
    e.eat(DOCS["harness"], episode_id="ep-1", episode_seq=0, episode_kind="session")
    e.eat(DOCS["corndog"], episode_id="ep-1", episode_seq=1, episode_kind="session")
    moments = e.recall_episodic("playtest harness registry seam", k=3,
                                include_source=True)
    top = moments[0]
    assert top.source_excerpt
    assert top.source_total_chars == len(top.source_excerpt)
