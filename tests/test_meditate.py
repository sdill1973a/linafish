"""`meditate` — the superthink verb (docs/session-instrument/meditate.md).

meditate bubbles up REAL material from the fish on a theme, mechanically (no
performed reflection, no confabulation — the fish either surfaces material or it
doesn't). Three modifiers: content (theme), time (window / dormancy), and model
scaling (fast / balanced / deep). linafish stays model-agnostic — prose framing
is a pluggable summarizer the caller supplies.

These tests assert the mechanical surfacing + the depth/time/dormancy knobs +
the summarizer hook. They do NOT assert any particular prose.
"""

from datetime import datetime, timezone, timedelta

from linafish.engine import FishEngine


def _engine(tmp_path):
    return FishEngine(state_dir=tmp_path, name="t", git_autocommit=False,
                      save_state_every_n_eats=1)


DOCS = {
    "harness": "We wired the playtest harness for the arena combat engine, "
               "logging every spawn and router decision to the registry seam.",
    "corndog": "At the county fair the third corndog was the best one, hot "
               "mustard and a paper tray, fried batter still steaming.",
    "river":   "The river road at dawn, fog over the water, gravel under the "
               "tires, the long quiet drive home through the bottoms.",
    "seam":    "The registry seam routes every spawn through one default path; "
               "the playtest harness logs that arena decision for replay.",
}


def _iso_days_ago(n):
    return (datetime.now(timezone.utc) - timedelta(days=n)).isoformat()


def test_meditate_fast_surfaces_theme(tmp_path):
    e = _engine(tmp_path)
    for k, v in DOCS.items():
        e.eat(v)
    out = e.meditate("playtest harness registry seam", depth="fast", top=3)
    assert out["theme"]
    assert out["depth"] == "fast"
    assert out["surfaced"], "fast meditate must bubble up matching crystals"
    # Each surfaced item carries why-it-surfaced metadata (mechanical, not faith).
    top = out["surfaced"][0]
    assert "gamma" in top and "why" in top and "text" in top
    # fast depth does not run the deeper passes.
    assert out.get("whisper") is None
    assert "co_access" not in out


def test_meditate_balanced_adds_whisper_and_emergence(tmp_path):
    e = _engine(tmp_path)
    for v in DOCS.values():
        e.eat(v)
    out = e.meditate("the arena harness", depth="balanced", top=3)
    assert out["depth"] == "balanced"
    assert "whisper" in out        # surprising-not-obvious formation (may be None on tiny fish)
    assert "emergence" in out      # phase classification key present


def test_meditate_deep_adds_co_access_and_load_bearing(tmp_path):
    e = _engine(tmp_path)
    for v in DOCS.values():
        e.eat(v)
    out = e.meditate("the arena harness", depth="deep", top=3)
    assert out["depth"] == "deep"
    assert "whisper" in out and "emergence" in out
    assert isinstance(out["co_access"], list)
    assert isinstance(out["load_bearing"], list)


def _seed_dated_corpus(e):
    """Eat each doc twice — an OLD copy (~400d) and a RECENT copy (~2d) —
    via chain_created_at. A richer corpus so the gamma pivot finder has
    real overlap to score (a 2-crystal fish is too sparse for gamma)."""
    for v in DOCS.values():
        e.eat(v, chain_created_at=_iso_days_ago(400))
    for v in DOCS.values():
        e.eat(v + " (revisited).", chain_created_at=_iso_days_ago(2))


def test_meditate_time_window_keeps_recent(tmp_path):
    e = _engine(tmp_path)
    _seed_dated_corpus(e)
    out = e.meditate("playtest harness registry seam arena", depth="fast",
                     top=8, time_window_days=30)
    ages = [s["age_days"] for s in out["surfaced"]]
    assert ages, "time-windowed meditate should surface the recent material"
    assert all(a <= 30 for a in ages), f"window leaked old crystals: {ages}"


def test_meditate_dormancy_surfaces_quiet(tmp_path):
    e = _engine(tmp_path)
    _seed_dated_corpus(e)
    out = e.meditate("playtest harness registry seam arena", depth="fast",
                     top=8, dormancy=True, dormancy_threshold_days=30)
    ages = [s["age_days"] for s in out["surfaced"]]
    assert ages, "dormancy meditate should surface the quiet/old material"
    assert all(a >= 30 for a in ages), f"dormancy surfaced recent crystals: {ages}"


def test_meditate_summarizer_hook(tmp_path):
    """linafish stays model-agnostic: a caller-supplied summarizer turns the
    surfaced material into prose. Without one, meditate returns structure only."""
    e = _engine(tmp_path)
    for v in DOCS.values():
        e.eat(v)

    seen = {}

    def summarizer(result):
        seen["called"] = True
        return f"meditation on {result['theme']} ({len(result['surfaced'])} surfaced)"

    out = e.meditate("the arena harness", depth="fast", top=3, summarizer=summarizer)
    assert seen.get("called") is True
    assert out["meditation"].startswith("meditation on")

    out2 = e.meditate("the arena harness", depth="fast", top=3)
    assert "meditation" not in out2  # no hook -> structure only, no prose


def test_meditate_empty_theme_or_fish(tmp_path):
    e = _engine(tmp_path)
    # Empty fish — no crash, empty surfaced.
    out = e.meditate("anything", depth="balanced")
    assert out["surfaced"] == []
