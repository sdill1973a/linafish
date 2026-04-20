"""Regression test for issue #2: _git_run must handle non-ASCII bytes
in git output without crashing on Windows (cp1252) or anywhere else.
"""
import subprocess
import tempfile
from pathlib import Path

from linafish.engine import FishEngine


def _git(cwd, *args):
    subprocess.run(["git"] + list(args), cwd=str(cwd), check=True,
                   capture_output=True)


def test_git_run_handles_non_ascii_output():
    """_git_run must not crash on git output containing bytes outside
    the platform default encoding. Regression for issue #2."""
    with tempfile.TemporaryDirectory() as tmp:
        state = Path(tmp) / "fish_state"
        state.mkdir()
        _git(state, "init", "--initial-branch=master")
        _git(state, "config", "user.email", "test@example.com")
        _git(state, "config", "user.name", "test")

        fish_md = state / "testfish.fish.md"
        fish_md.write_text(
            "# testfish\n\nWarm crystal with non-ASCII: "
            "\u2014 \u2013 \u2026 \u201c\u201d \u00e9\u00e8\u00ea "
            "\u4e2d\u6587 \U0001f41f\n",
            encoding="utf-8",
        )
        _git(state, "add", "testfish.fish.md")
        _git(state, "commit", "-m", "seed")

        fish_md.write_text(
            "# testfish\n\nUpdated with more non-ASCII: "
            "\u2192 \u2190 \U0001f52e \u0394\u03b1\u03c7\u03b5\n",
            encoding="utf-8",
        )
        _git(state, "add", "testfish.fish.md")
        _git(state, "commit", "-m", "update")

        engine = FishEngine(state_dir=state, name="testfish",
                            seed_grammar=False, git_autocommit=False)

        rc, out, err = engine._git_run("diff", "HEAD~1", "HEAD", "--",
                                       "testfish.fish.md")
        assert rc == 0, f"git diff failed: rc={rc}, err={err!r}"
        assert isinstance(out, str)
        assert isinstance(err, str)
        assert "\u2192" in out or "\u0394" in out or "\ufffd" in out, \
            "expected some non-ASCII or replacement char in diff output"


def test_git_run_returns_tuple_when_git_missing():
    """_git_run must degrade gracefully when git output is empty — no
    None.strip() AttributeError."""
    with tempfile.TemporaryDirectory() as tmp:
        state = Path(tmp) / "fish_state"
        state.mkdir()
        _git(state, "init", "--initial-branch=master")
        _git(state, "config", "user.email", "test@example.com")
        _git(state, "config", "user.name", "test")

        engine = FishEngine(state_dir=state, name="testfish",
                            seed_grammar=False, git_autocommit=False)

        rc, out, err = engine._git_run("status", "--porcelain")
        assert isinstance(out, str)
        assert isinstance(err, str)
