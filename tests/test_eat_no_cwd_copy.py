"""`eat` without --state-dir must not leave `<name>.fish.md` in the working directory.

Found 2026-11-07 (THX, Windows; Anchor, Linux) in a new-user audit: the fish lives in
~/.linafish, but every `eat` also dropped a duplicate render wherever it was run. Review R1
(2026-09-07) removed that copy for an explicit --state-dir and left it for the default.
`-o` must still write where it is pointed.
"""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

TEXT = ("I keep returning to the garden in the evening. The work there taught me patience, and "
        "patience taught me to wait for what grows slowly. I want to understand why it holds me.")


def _eat(home, cwd, *extra):
    env = {**os.environ, "HOME": str(home), "USERPROFILE": str(home), "PYTHONPATH": str(ROOT)}
    env.pop("LINAFISH_PROTECTED_VOCAB", None)
    return subprocess.run([sys.executable, "-m", "linafish", "eat", "entry.txt", "-n", "notes", *extra],
                          env=env, cwd=cwd, capture_output=True, text=True, timeout=300)


def _setup(tmp_path):
    home, work = tmp_path / "home", tmp_path / "work"
    home.mkdir()
    work.mkdir()
    (work / "entry.txt").write_text(TEXT, encoding="utf-8")
    return home, work


def test_eat_default_state_dir_leaves_no_copy_in_cwd(tmp_path):
    home, work = _setup(tmp_path)
    r = _eat(home, work)
    assert r.returncode == 0, r.stdout + r.stderr
    assert (home / ".linafish" / "notes.fish.md").exists(), "the persisted fish must still be written"
    assert not (work / "notes.fish.md").exists(), "eat dropped a stray copy in the working directory"


def test_eat_reports_the_persisted_path(tmp_path):
    home, work = _setup(tmp_path)
    r = _eat(home, work)
    fish_line = next(l for l in r.stdout.splitlines() if l.startswith("Fish: "))
    assert str(home / ".linafish" / "notes.fish.md") in fish_line, fish_line


def test_eat_output_flag_still_writes_where_pointed(tmp_path):
    home, work = _setup(tmp_path)
    r = _eat(home, work, "-o", "portrait.md")
    assert r.returncode == 0, r.stdout + r.stderr
    assert (work / "portrait.md").exists()
    assert not (work / "notes.fish.md").exists()
