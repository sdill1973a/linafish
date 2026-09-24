"""Bare read verbs find the fish `go` built — tested THROUGH THE PARSER (2.3.2).

tests/test_bare_verbs_feed_the_fish.py builds its args with name=None and never touches argparse, so it
passed while the parser defaulted -n to "linafish" for ask/check/whisper/history/diff and a bare
`linafish check` after `go ~/my-writing` reported an empty fish (found by the 2.3.1 doc review, reproduced
on a clean install). These run the real CLI.
"""
import os
import subprocess
import sys
from argparse import Namespace
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

TEXTS = [
    "I spent the morning fixing the garden fence because the posts had rotted at the base and I like work you can see.",
    "Called my sister about the trip; we keep circling spring or summer and I want to decide by Friday so we can book.",
    "Read two chapters on river ecology; floods rebuild the bank, and damage and repair are one process from two ends.",
    "Long day at work; the schedule did not land with the team, so next time I will draw it first and talk second.",
]


def _cli(home, *argv):
    env = {**os.environ, "HOME": str(home), "PYTHONPATH": str(ROOT)}
    env.pop("LINAFISH_PROTECTED_VOCAB", None)
    return subprocess.run([sys.executable, "-m", "linafish", *argv], env=env, capture_output=True,
                          text=True, timeout=300)


@pytest.fixture(scope="module")
def one_fish(tmp_path_factory):
    home = tmp_path_factory.mktemp("home")
    src = home / "my-writing"
    src.mkdir()
    for i, t in enumerate(TEXTS):
        (src / f"d{i}.txt").write_text(t)
    r = _cli(home, "go", str(src), "--no-serve")
    assert r.returncode == 0, r.stdout + r.stderr
    return home


def test_bare_check_reports_the_fish_go_built(one_fish):
    r = _cli(one_fish, "check")
    assert "my-writing" in r.stdout, r.stdout
    assert "fed me 0 entries" not in r.stdout


def test_explicit_wrong_name_still_reports_empty(one_fish):
    # The control: the finder must not paper over a name the user actually typed.
    r = _cli(one_fish, "check", "-n", "nosuch")
    assert "fed me 0 entries" in r.stdout or "empty" in r.stdout.lower(), r.stdout


def _args(state_dir, name=None, feed=None):
    return Namespace(name=name, feed=feed, state_dir=str(state_dir))


def test_serve_name_one_fish_is_served(tmp_path):
    from linafish.__main__ import _serve_name
    (tmp_path / "alpha_crystals.jsonl").write_text("")
    assert _serve_name(_args(tmp_path)) == "alpha"


def test_serve_name_several_fish_refuses(tmp_path):
    from linafish.__main__ import _serve_name
    (tmp_path / "alpha_crystals.jsonl").write_text("")
    (tmp_path / "beta_crystals.jsonl").write_text("")
    with pytest.raises(SystemExit):
        _serve_name(_args(tmp_path))


def test_serve_name_explicit_and_feed_unchanged(tmp_path):
    from linafish.__main__ import _serve_name
    (tmp_path / "alpha_crystals.jsonl").write_text("")
    assert _serve_name(_args(tmp_path, name="beta")) == "beta"
    assert _serve_name(_args(tmp_path, feed="/x")) == "linafish"
