"""2.0 invariant 1 — THE SPLIT IS TWO-SIDED.

NO-HEAT silences ambient readers. That is necessary and not sufficient: a build
that silences ambient and never records on deliberate views leaves the usage
store permanently empty while the invariant reads green. An empty signal and a
clean signal are indistinguishable from outside, so both halves get a test.

Two real builds failed here for opposite reasons — a resident server loop that
recorded on a timer (noise pinned at the weight ceiling, zero unhelpful marks),
and a heartbeat built on `recall`, which had no write path at all and so
recorded nothing even when the view was chosen. These tests fail if either
regresses.
"""
from pathlib import Path
import json

import pytest

from linafish.engine import FishEngine


SEED = [
    "The tide came in slow and the harbor lights held steady through the fog.",
    "Compression is understanding, not storage.",
    "A heart must be distinguishable from a corpse; quiet is valid.",
    "Ache conserves. It only redistributes.",
    "Memory that never records what it reached for cannot learn from use.",
]

QUERIES = ["heart corpse quiet", "compression understanding", "ache conserves"]


def _seeded(tmp_path: Path, **kwargs) -> FishEngine:
    e = FishEngine(name="probe", state_dir=tmp_path, **kwargs)
    if not e.fish.crystals:
        for line in SEED:
            e.eat(line, source="seed")
        form = getattr(e, "form", None)
        if form:
            form()
    return e


def _usage(tmp_path: Path):
    """Read the usage store off disk. Top-level map in current format;
    tolerate a nested {"usage": ...} shape so the test survives a reshape."""
    fb = tmp_path / "probe_feedback.json"
    if not fb.exists():
        return None
    data = json.loads(fb.read_text(encoding="utf-8") or "{}")
    return data.get("usage", data)


def test_ambient_recall_never_records(tmp_path):
    """The heartbeat half: no_heat=True must leave no trace at all."""
    _seeded(tmp_path)
    assert _usage(tmp_path) is None, "precondition: store starts empty"

    ambient = _seeded(tmp_path, no_heat=True)
    for q in QUERIES:
        ambient.recall(q, top=5)

    assert _usage(tmp_path) is None, (
        "an ambient reader wrote to the usage store — invariant 1 violated"
    )


def test_deliberate_recall_does_record(tmp_path):
    """The other half: a chosen view must move the store, or the signal is dead."""
    _seeded(tmp_path)
    deliberate = _seeded(tmp_path)
    for q in QUERIES:
        deliberate.recall(q, top=5)

    usage = _usage(tmp_path)
    assert usage, (
        "deliberate recall recorded nothing — the usage store is frozen by "
        "construction and `doctor` cannot tell that from a clean one"
    )
    assert sum(e.get("hits", 0) for e in usage.values()) > 0


def test_env_var_silences_deliberate_path_too(tmp_path):
    """LINAFISH_NO_HEAT is how a resident server is neutered without code changes.
    It must govern the recall path as well as taste/match."""
    _seeded(tmp_path)
    before = _usage(tmp_path)

    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("LINAFISH_NO_HEAT", "1")
        engine = _seeded(tmp_path)
        for q in QUERIES:
            engine.recall(q, top=5)

    assert _usage(tmp_path) == before, "LINAFISH_NO_HEAT did not gate recall()"


def test_taste_still_records(tmp_path):
    """Regression guard on the pre-existing half — recall's new write path must
    not have disturbed taste/match."""
    _seeded(tmp_path)
    engine = _seeded(tmp_path)
    engine.taste("quiet silence heart")

    usage = _usage(tmp_path)
    assert usage, "taste() stopped recording — the original feedback path broke"
