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


# --- doctor's liveness panel: measure the property, not a proxy ---
# Found by adversarial review (Olorina, 2026-07-31): FROZEN aged from
# st_mtime, which answers "when was this file written", not "when was usage
# recorded". Measured divergence on a live store: 2h47m. Any save, reshape or
# migration resets the proxy, so FROZEN goes quiet exactly when it should fire.

import subprocess
import sys
import time


def _doctor(tmp_path) -> str:
    r = subprocess.run(
        [sys.executable, "-m", "linafish", "doctor",
         "--name", "probe", "--state-dir", str(tmp_path)],
        capture_output=True, text=True, timeout=120,
    )
    return r.stdout


def test_frozen_fires_on_fresh_file_with_stale_usage(tmp_path):
    """THE PROXY TRAP: file written seconds ago, usage recorded 40 days ago."""
    store = tmp_path / "probe_feedback.json"
    store.write_text(json.dumps({
        "OLD": {"hits": 12, "helpful": 12, "unhelpful": 3,
                "last_used": time.time() - 40 * 86400, "weight_modifier": 1.4}
    }), encoding="utf-8")
    assert time.time() - store.stat().st_mtime < 60, "file is freshly written"

    out = _doctor(tmp_path)
    assert "FROZEN" in out, (
        "FROZEN did not fire on a 40-day-old usage signal because the file "
        "itself was fresh — the panel is reading the proxy, not the property"
    )
    assert "measured by: last_used" in out


def test_sub_day_age_keeps_its_resolution(tmp_path):
    """10.7 hours must not render as '0d' — that read as 'today' and nearly
    shipped a false all-clear."""
    store = tmp_path / "probe_feedback.json"
    store.write_text(json.dumps({
        "F": {"hits": 5, "helpful": 5, "unhelpful": 1,
              "last_used": time.time() - 10.7 * 3600, "weight_modifier": 1.2}
    }), encoding="utf-8")

    out = _doctor(tmp_path)
    assert "10.7h" in out, "sub-day age lost its resolution"
    assert "FROZEN" not in out


def test_mtime_fallback_names_itself(tmp_path):
    """A store with no timestamps may fall back to mtime — but must say so."""
    store = tmp_path / "probe_feedback.json"
    store.write_text(json.dumps({
        "F": {"hits": 5, "helpful": 5, "unhelpful": 1, "weight_modifier": 1.2}
    }), encoding="utf-8")

    out = _doctor(tmp_path)
    assert "file mtime" in out, "fallback did not name what it measured"


def test_suspect_declines_to_judge_without_timestamps(tmp_path):
    """A store predating first_used has no measurable span. The panel must SAY
    so rather than passing silently — an unmeasurable quantity reported as a
    pass is the whole disease."""
    store = tmp_path / "probe_feedback.json"
    store.write_text(json.dumps({
        "F": {"hits": 90000, "helpful": 90000, "unhelpful": 0,
              "last_used": time.time(), "weight_modifier": 3.0}
    }), encoding="utf-8")

    out = _doctor(tmp_path)
    assert "declines to judge" in out, "panel guessed instead of naming the gap"


def test_suspect_silent_on_deliberate_rate(tmp_path):
    """Deliberate use on a healthy store runs well under 1 hit/day/formation.
    Weight is ignored on purpose: it is a pure function of hits (12 hits pins
    ANY formation at 3.0), so ceiling-pinning is volume, not provenance."""
    now = time.time()
    store = tmp_path / "probe_feedback.json"
    usage = {}
    for i in range(20):
        usage[f"F{i}"] = {"hits": 40, "helpful": 40, "unhelpful": 0,
                          "first_used": now - 120 * 86400,   # over four months
                          "last_used": now, "weight_modifier": 3.0}
    store.write_text(json.dumps(usage), encoding="utf-8")

    out = _doctor(tmp_path)
    assert "[!] SUSPECT" not in out, (
        "SUSPECT fired on ceiling-pinned formations accumulated slowly — it is "
        "reading volume rather than rate"
    )


def test_suspect_fires_on_timer_rate(tmp_path):
    """A ~34s cadence is roughly 2,500 hits/day on one formation."""
    now = time.time()
    store = tmp_path / "probe_feedback.json"
    store.write_text(json.dumps({
        "TIMER": {"hits": 71353, "helpful": 71353, "unhelpful": 0,
                  "first_used": now - 30 * 86400, "last_used": now,
                  "weight_modifier": 3.0}
    }), encoding="utf-8")

    out = _doctor(tmp_path)
    assert "[!] SUSPECT" in out, "SUSPECT missed a timer-rate store"


def test_rate_does_not_false_alarm_on_backfilled_legacy_store(tmp_path):
    """A rate whose numerator and denominator cover different windows is not a
    rate. A healthy store — 55 hits over six months, 0.31/day — backfilled and
    hit once computed 56 hits/day and accused itself of being a timer, in
    confident prose (Olorina, measured on the live panel)."""
    from linafish.feedback import FeedbackLoop
    now = time.time()
    store = tmp_path / "probe_feedback.json"
    store.write_text(json.dumps({
        "SLOW": {"hits": 55, "helpful": 55, "unhelpful": 0,
                 "last_used": now - 86400, "weight_modifier": 3.0}
    }), encoding="utf-8")

    FeedbackLoop(state_path=store).hit("SLOW")   # the one deliberate use

    out = _doctor(tmp_path)
    assert "[!] SUSPECT" not in out, (
        "a 0.31 hits/day store was accused of being a timer — the numerator "
        "counts all of history while the span counts only since backfill"
    )


def test_rate_still_catches_a_timer_after_baselining(tmp_path):
    """Negative control for the fix above: baselining must not blind the check."""
    now = time.time()
    store = tmp_path / "probe_feedback.json"
    store.write_text(json.dumps({
        "TIMER": {"hits": 3000, "helpful": 3000, "unhelpful": 0,
                  "hits_baseline": 0, "first_used": now - 6 * 3600,
                  "last_used": now, "weight_modifier": 3.0}
    }), encoding="utf-8")

    out = _doctor(tmp_path)
    assert "[!] SUSPECT" in out, "baselining the numerator blinded the timer check"


# --- per-request no_heat: the MIXED server (2.0 invariant 1, mandatory) ---
# A resident server can take ambient AND deliberate traffic on one engine.
# A process-wide flag silences both, which is 1(b) in a compliance costume.
# The caller that knows whether it CHOSE is the only one who can answer.

def test_per_request_ambient_is_silent_on_a_deliberate_engine(tmp_path):
    e = _seeded(tmp_path)
    for q in QUERIES:
        e.taste(q, no_heat=True)
        e.recall(q, no_heat=True)
        e.match(q, no_heat=True)
    assert _usage(tmp_path) is None, "per-request no_heat did not silence an ambient call"


def test_per_request_deliberate_records_on_the_same_engine(tmp_path):
    e = _seeded(tmp_path)
    for q in QUERIES:
        e.taste(q, no_heat=True)      # ambient traffic first
    for q in QUERIES:
        e.taste(q)                    # then a deliberate caller, same engine
    assert _usage(tmp_path), "the deliberate half froze on a mixed engine"


def test_per_call_flag_overrides_the_process_setting(tmp_path):
    """The inverse direction: a no_heat PROCESS must still record when the
    caller explicitly declares the read deliberate."""
    _seeded(tmp_path)
    e = _seeded(tmp_path, no_heat=True)
    e.taste(QUERIES[0], no_heat=False)
    assert _usage(tmp_path), "per-call override lost to the process-wide setting"


def test_taste_forwards_the_flag_to_taste_dict(tmp_path):
    """taste() renders taste_dict(); it must not drop the flag on the way.
    It did, on the first implementation — caught only by testing the verbs
    together rather than one at a time."""
    e = _seeded(tmp_path)
    e.taste(QUERIES[0], no_heat=True)
    assert _usage(tmp_path) is None, "taste() dropped no_heat before taste_dict()"
