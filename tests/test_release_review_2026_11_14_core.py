"""Three defects a user could hit, found reading the core top to bottom for the
2.4.2 release review (2026-11-14). Each test fails on 2.4.1 and passes with the fix.

1. ``logging`` at DEBUG crashed ``eat_path`` / ``_formative_assess`` with
   ``TypeError: Logger._log() got an unexpected keyword argument 'file'`` —
   nine ``logger.debug(..., file=sys.stderr)`` calls left over from ``print``.
2. ``UniversalFish._load_state`` skipped unparseable crystal lines silently, so a
   fish that lost crystals to a torn log reported itself whole.
3. A fish fed one document is frozen with an empty vocabulary (stranger mode,
   idf 0 everywhere); ``taste`` then said "Text too short or no signal detected"
   about a query that was neither. The reason is now ``no_vocab``.
"""
import json
import logging
from pathlib import Path

from linafish.engine import FishEngine

NOTE = ("I keep coming back to the same shape: the garden only grows after the "
        "trellis is set, and the team only ships after the queue owns its retries. "
        "Patient structure first, then growth. That is the lesson I relearn every spring.")


def _corpus(tmp_path: Path, n: int = 5) -> Path:
    d = tmp_path / "corpus"
    d.mkdir()
    for i in range(n):
        (d / f"n{i}.txt").write_text(f"Note {i}. {NOTE}", encoding="utf-8")
    return d


# 1 ---------------------------------------------------------------------------

def test_eat_path_survives_debug_logging(tmp_path, caplog):
    """A library user who turns on DEBUG logging must not lose eat_path to a TypeError."""
    corpus = _corpus(tmp_path)
    engine = FishEngine(state_dir=tmp_path / "state", name="dbg")
    with caplog.at_level(logging.DEBUG, logger="linafish.engine"):
        result = engine.eat_path(corpus)        # raised TypeError on 2.4.1
    assert result["crystals_added"] == 5


def test_formative_assess_survives_debug_logging(tmp_path, caplog):
    corpus = _corpus(tmp_path)
    engine = FishEngine(state_dir=tmp_path / "state", name="dbg")
    engine.eat_path(corpus)
    with caplog.at_level(logging.DEBUG, logger="linafish.engine"):
        result = engine.maintain()              # runs _formative_assess
    assert result["maintained"] is True


def test_no_logger_call_passes_a_file_kwarg():
    """The whole module, not just the two paths above: ``file=`` is a print kwarg."""
    import inspect
    import re
    from linafish import engine as mod
    src = inspect.getsource(mod)
    # a logger call whose argument list, possibly spanning lines, ends with file=...
    bad = re.findall(r"getLogger\(__name__\)\.\w+\((?:[^()]|\([^()]*\))*file=", src)
    assert bad == [], f"{len(bad)} logger call(s) still pass file="


# 2 ---------------------------------------------------------------------------

def test_load_state_warns_with_the_count_of_skipped_lines(tmp_path, caplog):
    corpus = _corpus(tmp_path, n=3)
    state = tmp_path / "state"
    FishEngine(state_dir=state, name="torn").eat_path(corpus)
    log = state / "torn_crystals.jsonl"
    lines = log.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3
    # damage two lines the way a torn write and a stray edit would
    lines[0] = lines[0][: len(lines[0]) // 2]
    lines[1] = "not json at all"
    log.write_text("\n".join(lines) + "\n", encoding="utf-8")

    with caplog.at_level(logging.WARNING, logger="linafish.crystallizer_v3"):
        reloaded = FishEngine(state_dir=state, name="torn")
    assert len(reloaded.fish.crystals) == 1
    msgs = [r.getMessage() for r in caplog.records if "did not parse" in r.getMessage()]
    assert len(msgs) == 1, "exactly one warning, carrying the count"
    assert "2 line(s)" in msgs[0] and "1 loaded" in msgs[0]
    assert "nothing was deleted" in msgs[0].lower()


def test_load_state_is_silent_on_a_clean_log(tmp_path, caplog):
    corpus = _corpus(tmp_path, n=3)
    state = tmp_path / "state"
    FishEngine(state_dir=state, name="clean").eat_path(corpus)
    with caplog.at_level(logging.WARNING, logger="linafish.crystallizer_v3"):
        reloaded = FishEngine(state_dir=state, name="clean")
    assert len(reloaded.fish.crystals) == 3
    assert not [r for r in caplog.records if "did not parse" in r.getMessage()]


def test_load_state_blank_lines_are_not_counted_as_losses(tmp_path, caplog):
    corpus = _corpus(tmp_path, n=2)
    state = tmp_path / "state"
    FishEngine(state_dir=state, name="blank").eat_path(corpus)
    log = state / "blank_crystals.jsonl"
    log.write_text(log.read_text(encoding="utf-8") + "\n\n", encoding="utf-8")
    with caplog.at_level(logging.WARNING, logger="linafish.crystallizer_v3"):
        reloaded = FishEngine(state_dir=state, name="blank")
    assert len(reloaded.fish.crystals) == 2
    assert not [r for r in caplog.records if "did not parse" in r.getMessage()]


# 3 ---------------------------------------------------------------------------

def test_one_document_fish_says_no_vocab_not_too_short(tmp_path):
    engine = FishEngine(state_dir=tmp_path / "state", name="solo")
    r = engine.eat(NOTE, source="note.txt")
    assert r["crystals_added"] == 1
    assert engine.fish.frozen and engine.fish.vocab == [], "the precondition this test is about"

    d = engine.taste_dict("patient structure before growth", no_heat=True)
    assert d["ok"] is False
    assert d["reason"] == "no_vocab"           # was "no_signal" on 2.4.1
    assert d["total_crystals"] == 1

    text = engine.taste("patient structure before growth", no_heat=True)
    assert "too short" not in text.lower()
    assert "no vocabulary" in text.lower()
    assert "1 crystal" in text


def test_no_vocab_clears_at_the_second_document(tmp_path):
    """The reason is about the fish's state, not the query: a second eat gives it axes."""
    engine = FishEngine(state_dir=tmp_path / "state", name="duo")
    engine.eat(NOTE, source="a")
    engine.eat("On the architecture call we argued about whether the queue should own "
               "retries or the worker should, and nobody wrote the decision down.", source="b")
    assert engine.fish.vocab
    d = engine.taste_dict("the queue should own retries", no_heat=True)
    assert d["reason" if not d["ok"] else "ok"] != "no_vocab"
