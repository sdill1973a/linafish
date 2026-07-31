"""THE HEART — the 2.0 afferent organ, tested against its own invariants."""
import json
from pathlib import Path

import pytest

from linafish.engine import FishEngine
from linafish.heart import beat, read_beat_log

JOURNAL = [
    "The greenhouse flooded again after the March rain and I lost the seedlings.",
    "Grandmother's recipe box smells like cardamom and old paper.",
    "Rebuilding the drystone wall took three summers and my back never forgave me.",
]
NOTES = [
    "Drystone walls need a batter of one in six or they bow outward.",
    "Seedlings drown faster than they dry; raise the beds before the rains.",
]
GENUINE = "I'm rebuilding the wall by the greenhouse and thinking about the seedlings we lost"
UNRELATED = "quarterly amortization schedules for municipal bond refinancing"

CONFIG = """
[family]
journal = { dir = "journal", weight = 1.3 }
notes   = { dir = "notes",   weight = 1.0 }

[gate]
min_prompt_chars = 20

[surface]
top = 4
per_fish = 3

[wall]
mode = "declare"
public_pattern = "\\\\b(publish|announce|public)\\\\b"
"""


@pytest.fixture
def home(tmp_path):
    for name, lines in (("journal", JOURNAL), ("notes", NOTES)):
        e = FishEngine(name=name, state_dir=tmp_path / name)
        for line in lines:
            e.eat(line, source="seed")
        form = getattr(e, "form", None)
        if form:
            form()
    (tmp_path / "heart.toml").write_text(CONFIG, encoding="utf-8")
    return tmp_path


def test_heart_surfaces_what_reaches(home):
    out = beat(GENUINE, home)
    assert "♥ heart" in out
    assert "seedlings" in out.lower() or "drystone" in out.lower()


def test_invariant_1_ambient_never_writes(home):
    """The organ must leave no trace in the stores it reads."""
    for _ in range(3):
        beat(GENUINE, home)
    assert not list(home.rglob("*_feedback.json")), (
        "the heart wrote to a usage store — an ambient organ that heats its own "
        "memories corrupts the very signal it reads"
    )


def test_invariant_2_fail_silent_on_a_broken_family(home):
    """A missing/corrupt band must not raise; the nerve never blocks a turn."""
    (home / "heart.toml").write_text(
        CONFIG + '\nghost = { dir = "nowhere", weight = 2.0 }\n', encoding="utf-8")
    out = beat(GENUINE, home)          # must not raise
    assert isinstance(out, str)


def test_invariant_4_quiet_on_an_unrelated_prompt(home):
    """A single incidental word is not the self reaching toward the moment.
    Measured: unrelated prompts match exactly one (stop)word; genuine hits
    match three or more."""
    assert beat(UNRELATED, home) == "", "the heart fired on an unrelated prompt"


def test_invariant_4_short_prompts_pay_nothing(home):
    assert beat("hi", home) == ""


def test_invariant_6_quiet_is_distinguishable_from_dead(home):
    """Quiet stays valid; silence about the silence does not."""
    beat(UNRELATED, home)
    log = read_beat_log(home)
    assert log, "a quiet beat left no trace — quiet is now indistinguishable from death"
    assert log[-1]["attempted"] >= 1 and log[-1]["surfaced"] == 0


def test_invariant_6_inert_heart_says_so(tmp_path):
    """No config is a fact about the organ, not an error for the turn — and it
    must be visible, or an unconfigured heart looks exactly like a quiet one."""
    assert beat("a prompt long enough to clear the gate here", tmp_path) == ""
    log = read_beat_log(tmp_path)
    assert log and "inert" in log[-1]


def test_invariant_3_wall_declares_but_never_gates_depth(home):
    """The tripwire adds friction; it must not suppress the inward surfacing."""
    out = beat("I want to publish a post about the drystone wall and the seedlings", home)
    assert "hand on shoulder" in out
    assert out.count("♥ heart") >= 2, "the wall amputated the depth axis"


def test_family_weight_orders_the_surface(home):
    """The densest band is marked and leads."""
    out = beat(GENUINE, home)
    assert out.splitlines()[0].startswith("♥ heart ♥"), "densest band did not lead"


def test_slow_band_cannot_hang_the_turn(home, monkeypatch):
    """INVARIANT 2, the half the whole-beat budget does NOT cover.

    The budget is only checked BETWEEN bands, so a single slow fish blocks the
    turn indefinitely no matter what the budget says. `per_fish_timeout` was
    parsed from config and never applied — a small test corpus always returns
    instantly and so cannot exercise this path. Found by an outside reviewer.

    The slowness has to be injected INSIDE _recall_band (at the engine call),
    not by replacing _recall_band — patching the function that holds the timeout
    puts the delay outside the region under test. First version of this test did
    exactly that and failed against the fix.
    """
    import time as _time
    from linafish.engine import FishEngine

    (home / "heart.toml").write_text(
        CONFIG + '\n[timing]\nper_fish_timeout = 0.5\n', encoding="utf-8")

    real_recall = FishEngine.recall

    def slow_recall(self, query, top=10, no_heat=None):
        if self.name == "journal":
            _time.sleep(5)              # far past the 0.5s band timeout
        return real_recall(self, query, top=top, no_heat=no_heat)

    monkeypatch.setattr(FishEngine, "recall", slow_recall)

    t0 = _time.time()
    out = beat(GENUINE, home)
    elapsed = _time.time() - t0

    assert elapsed < 4, (
        f"a slow band hung the turn for {elapsed:.1f}s — the per-fish timeout "
        "is not applied, and the whole-beat budget cannot save it")
    assert isinstance(out, str)
