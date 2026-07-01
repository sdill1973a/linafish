"""Tests for FishEngine origin / "crystal zero" provenance.

v1.2 seed #6 (docs/v12-seeds.md #6): every fish should carry a crystal
recording who built it, when, why, and what it holds — so it never gets
mistaken for disused and pruned/deprecated by accident. Implemented as an
ordinary ``Crystal`` marked ``protected=True``, persisted through the same
JSONL path as every other crystal.

Backward compatibility is the load-bearing property here: a fish built
without ever touching origin must load and behave exactly as before.
"""
from pathlib import Path

from linafish.engine import FishEngine, ORIGIN_SOURCE, ORIGIN_FORMATION


def _engine(tmp_path, name="testfish", **kwargs):
    return FishEngine(
        state_dir=tmp_path, name=name,
        seed_grammar=False, git_autocommit=False,
        **kwargs,
    )


def test_fish_with_no_origin_call_is_unaffected(tmp_path: Path):
    """Backward compatibility: an engine that never calls set_origin()
    loads and works exactly as before — origin is optional, defaults
    to absent."""
    engine = _engine(tmp_path)
    assert engine.get_origin() is None
    assert engine.fish.crystals == []


def test_set_origin_creates_a_protected_crystal(tmp_path: Path):
    engine = _engine(tmp_path)
    crystal = engine.set_origin(
        built_by="Anchor", why="prevent accidental deletion",
        holds="a tiny test corpus",
    )
    assert crystal.protected is True
    assert crystal.source == ORIGIN_SOURCE
    assert crystal.formation == ORIGIN_FORMATION
    assert "Anchor" in crystal.text
    assert "DO NOT DEPRECATE" in crystal.text
    assert engine.get_origin() is crystal
    assert crystal in engine.fish.crystals


def test_set_origin_is_idempotent(tmp_path: Path):
    """Calling set_origin() twice must not create a second crystal zero —
    a fish carries at most one origin record."""
    engine = _engine(tmp_path)
    first = engine.set_origin(built_by="Anchor", why="first call")
    second = engine.set_origin(built_by="someone else", why="should be ignored")

    assert second is first
    assert second.text == first.text
    origin_crystals = [c for c in engine.fish.crystals if c.source == ORIGIN_SOURCE]
    assert len(origin_crystals) == 1


def test_origin_persists_across_reload(tmp_path: Path):
    """The origin crystal round-trips through the normal crystal JSONL
    log — a fresh FishEngine pointed at the same state dir sees it."""
    engine1 = _engine(tmp_path)
    engine1.set_origin(built_by="Anchor", why="persistence check", holds="stuff")

    engine2 = _engine(tmp_path)
    reloaded = engine2.get_origin()
    assert reloaded is not None
    assert reloaded.protected is True
    assert reloaded.source == ORIGIN_SOURCE
    assert "persistence check" in reloaded.text


def test_origin_kwarg_at_construction(tmp_path: Path):
    """FishEngine(origin={...}) sets crystal zero at creation time —
    the school.add_member-friendly path from the seed spec."""
    engine = _engine(
        tmp_path,
        origin={"built_by": "Anchor", "why": "kwarg path", "holds": "stuff"},
    )
    origin = engine.get_origin()
    assert origin is not None
    assert "kwarg path" in origin.text


def test_ordinary_crystals_default_unprotected(tmp_path: Path):
    """Every other crystal defaults to protected=False — the new field
    does not change behavior for the existing eat() path."""
    engine = _engine(tmp_path, d=2.0)
    engine.eat(
        "a plain sentence that is definitely long enough to crystallize",
        source="test",
    )
    assert len(engine.fish.crystals) == 1
    assert engine.fish.crystals[0].protected is False
