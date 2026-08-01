"""The daemon's maintenance thread must actually maintain something.

Issue #48. _maintenance_loop called engine.re_eat() every re_eat_interval_hours.
re_eat bails on nothing_pending, and nothing on any engine path writes
pending — eat() freezes before crystallizing, and crystallize_text appends to
pending only on its pre-freeze branch. So the loop's
`if result["re_eat"] is False: continue` was the only branch ever taken, and
the gardener, the formative assessment and the GrowthTracker — which are
called from re_eat and nowhere else — had never run.

The observable that proves it either way is {name}_growth.json: written only
by GrowthTracker.save, called only from the re-eat tail, and loaded at every
engine init. No live fish in the federation has one.
"""

import json
import threading

from linafish.engine import FishEngine

TEXT = ("The river road at dawn, fog over the water, gravel under the tires, "
        "the long quiet drive home through the bottoms. ")


def _engine(tmp_path):
    e = FishEngine(state_dir=tmp_path, name="t", git_autocommit=False,
                   save_state_every_n_eats=1)
    for i in range(6):
        e.eat(f"{TEXT} Run {i} of the fixture, with enough words to crystallize.")
    return e


def test_re_eat_still_does_nothing_without_pending(tmp_path):
    """Pinning the behaviour this exists to route around, so the diagnosis in
    #48 is checkable and not just asserted in a commit message."""
    e = _engine(tmp_path)
    assert e.re_eat() == {"re_eat": False, "reason": "nothing_pending"}
    assert not (tmp_path / "t_growth.json").exists()


def test_maintain_runs_with_nothing_pending(tmp_path):
    e = _engine(tmp_path)
    result = e.maintain()

    assert result["maintained"] is True
    assert result["re_eat"] is False
    assert result["relearned"] is False


def test_maintain_writes_the_growth_file(tmp_path):
    """The observable. Absent on every live fish; present after one cycle."""
    e = _engine(tmp_path)
    growth_path = tmp_path / "t_growth.json"
    assert not growth_path.exists()

    e.maintain()

    assert growth_path.exists(), "GrowthTracker still never ran"
    assert json.loads(growth_path.read_text())


def test_first_cycle_reports_growth_levels_without_deltas(tmp_path):
    """GrowthTracker.record() returns None on the first snapshot — nothing to
    delta against. Every cycle on a fish where this has never run IS the first
    cycle, which is every fish. Caught against the live mimipc corpus, not in
    the unit tests, which is why this one exists."""
    e = _engine(tmp_path)
    result = e.maintain()

    assert "tracker_error" not in result, result.get("tracker_error")
    growth = result["growth"]
    assert "r_n" in growth and "coupling_density" in growth
    assert "crystal_delta" not in growth

    second = e.maintain()
    assert "crystal_delta" in second["growth"], "deltas never start reporting"


def test_maintain_runs_the_gardener(tmp_path):
    e = _engine(tmp_path)
    result = e.maintain()
    assert "garden" in result, "gardener pass did not run"
    assert "garden_error" not in result


def test_maintain_does_not_refreeze_the_vocabulary(tmp_path):
    """Deliberate. Re-freezing on a 6-hourly thread would churn the vector
    space under crystals that keep their old vectors (§THE.DIGEST.GAP).
    Assessment's seed-weight recommendations wait for a real freeze."""
    e = _engine(tmp_path)
    epoch_before = e.fish.epoch
    vocab_before = list(e.fish.vocab)

    result = e.maintain()

    assert result["refroze"] is False
    assert e.fish.epoch == epoch_before
    assert list(e.fish.vocab) == vocab_before


def test_maintain_delegates_to_re_eat_when_pending_exists(tmp_path):
    """A fish driven by the crystallizer's own ingest path keeps today's
    behaviour: the full cycle, relearn and re-freeze included."""
    e = _engine(tmp_path)
    with open(e.fish.pending_path, "w") as f:
        for i in range(4):
            f.write(json.dumps(
                {"text": f"{TEXT} Pending deposit {i}, awaiting the next cycle."}
            ) + "\n")
    epoch_before = e.fish.epoch

    result = e.maintain()

    assert result["re_eat"] is True
    assert result["maintained"] is True
    assert result["pending_consumed"] == 4
    assert e.fish.epoch == epoch_before + 1


def test_maintenance_loop_calls_maintain_not_re_eat(tmp_path):
    """The loop is the whole point: it was wired to the dead path."""
    from linafish.http_server import _maintenance_loop

    e = _engine(tmp_path)
    called = []
    e.maintain = lambda: (called.append("maintain") or
                          {"maintained": True, "growth": {}})
    e.re_eat = lambda: called.append("re_eat") or {"re_eat": False}

    stop = threading.Event()
    t = threading.Thread(
        target=_maintenance_loop,
        args=(e, stop, 0.5 / 3600),  # half-second interval
        daemon=True,
    )
    t.start()
    try:
        deadline = threading.Event()
        deadline.wait(2.0)
    finally:
        stop.set()
        t.join(timeout=5)

    assert "maintain" in called, "loop never called maintain()"
    assert "re_eat" not in called, "loop still calls the dead path directly"
