"""The flagship loop must feed the fish it built (2.1.0 induction audit).

Before this fix, `linafish eat note.txt` bare created a NEW fish named after
the file stem, and `ask`/`check`/`whisper` bare queried a fish literally
named 'linafish' that `go` never creates — so the README's own sequence told
every new user their fish was empty while a stray baby fish grew beside it.

Proven both ways: the discovery path feeds/finds the existing fish, AND the
guarded path (several fish) refuses loudly instead of guessing a write target.
"""

import argparse
from pathlib import Path

import pytest

from linafish.__main__ import _discover_fish_names, _resolve_engine, cmd_eat
from linafish.engine import FishEngine


def _mk_fish(root: Path, name: str, text: str) -> FishEngine:
    eng = FishEngine(state_dir=root, name=name)
    eng.eat(text, source="seed")
    return eng


def _eat_args(source: Path, state_dir: Path, name=None):
    return argparse.Namespace(
        source=str(source), name=name, description=None, output=None,
        hint=None, vocab=None, state_dir=str(state_dir),
    )


def test_discover_names_orders_by_recency(tmp_path):
    _mk_fish(tmp_path, "older", "the first fish here")
    import time
    time.sleep(0.05)
    _mk_fish(tmp_path, "newer", "the second fish here")
    names = _discover_fish_names(tmp_path)
    assert set(names) == {"older", "newer"}
    assert names[0] == "newer"


def test_bare_eat_feeds_the_single_existing_fish(tmp_path, capsys):
    _mk_fish(tmp_path, "corpus", "structure carries the reader")
    before = len(FishEngine(state_dir=tmp_path, name="corpus").fish.crystals)

    note = tmp_path / "observation.txt"
    note.write_text("a genuinely new observation about paragraph rhythm "
                    "and how the reader breathes with it")
    cmd_eat(_eat_args(note, tmp_path))

    out = capsys.readouterr().out
    assert "Feeding fish 'corpus'" in out
    after = len(FishEngine(state_dir=tmp_path, name="corpus").fish.crystals)
    assert after > before, "the existing fish must grow"
    # and no baby fish named after the file
    assert not (tmp_path / "observation_crystals.jsonl").exists()


def test_bare_eat_with_several_fish_refuses_loudly(tmp_path, capsys):
    _mk_fish(tmp_path, "one", "first fish text")
    _mk_fish(tmp_path, "two", "second fish text")
    note = tmp_path / "note.txt"
    note.write_text("which fish should this feed? neither, silently.")
    with pytest.raises(SystemExit) as exc:
        cmd_eat(_eat_args(note, tmp_path))
    assert exc.value.code == 1
    out = capsys.readouterr().out
    assert "one" in out and "two" in out
    assert "-n" in out


def test_bare_eat_with_no_fish_creates_from_stem_and_says_so(tmp_path, capsys):
    note = tmp_path / "standalone.txt"
    note.write_text("a first file with no fish anywhere in sight yet")
    cmd_eat(_eat_args(note, tmp_path))
    out = capsys.readouterr().out
    assert "creating 'standalone'" in out
    assert (tmp_path / "standalone_crystals.jsonl").exists()


def test_resolve_engine_bare_discovers_the_go_fish(tmp_path):
    _mk_fish(tmp_path, "myproject", "the fish go built from a folder")
    args = argparse.Namespace(name=None, state_dir=str(tmp_path))
    eng = _resolve_engine(args)
    assert eng.name == "myproject"
    assert eng.fish.crystals, "ask/check/whisper must see the go-fish's content"


def test_resolve_engine_bare_with_no_fish_keeps_historical_default(tmp_path):
    args = argparse.Namespace(name=None, state_dir=str(tmp_path))
    eng = _resolve_engine(args)
    assert eng.name == "linafish"
    assert not eng.fish.crystals
