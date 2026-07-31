"""Regression test: _git_commit must not swallow git failures.

The bug this guards against is silent and permanent. _git_commit ran
`git add`/`git commit` with capture_output=True and never checked the
return code, so a state dir with no committer identity accumulated
crystals for weeks while every commit failed. history/diff/revert/session
were all no-ops and nothing said a word — the fish *looked* versioned.

The contract now: never raise (a broken git must not take down an eat),
never hide a real failure, and stay silent when there is simply nothing
to commit.
"""
import logging
import subprocess
import tempfile
from pathlib import Path

import pytest

from linafish.engine import FishEngine


@pytest.fixture(autouse=True)
def isolated_git_env(monkeypatch, tmp_path):
    """Make every test here hermetic with respect to the developer's config.

    Two of these tests assert a commit FAILS for want of a committer
    identity. Repo-local `user.useConfigOnly` is not sufficient on its own:
    it stops git *guessing* an identity from hostname/username, but a real
    `user.email` in the developer's global config is still honored, so the
    commit succeeds and the assertion inverts.

    The failure mode is nasty because it is invisible to whoever wrote the
    test: the suite passes only on a machine with no global git identity —
    which is exactly the misconfigured state that produced the bug being
    tested. It then "fails" on any contributor with a normal ~/.gitconfig
    and reads as flakiness. Isolate the environment instead of trying to
    out-configure it.

    Env vars, not just fixture-local subprocess kwargs: the engine shells
    out to git itself, and those calls inherit os.environ.
    """
    empty = tmp_path / "empty.gitconfig"
    empty.write_text("", encoding="utf-8")
    # A real empty file, not os.devnull — 'nul' is not a usable config path
    # for git on Windows.
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(empty))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    # These bypass config entirely; some CI images set them.
    for var in ("GIT_AUTHOR_NAME", "GIT_AUTHOR_EMAIL", "GIT_COMMITTER_NAME",
                "GIT_COMMITTER_EMAIL", "EMAIL", "GIT_CONFIG_SYSTEM"):
        monkeypatch.delenv(var, raising=False)


def _git(cwd, *args):
    subprocess.run(["git"] + list(args), cwd=str(cwd), check=True,
                   capture_output=True)


def _engine(state):
    """A FishEngine with only what the git helpers touch — building a real
    one would crystallize a corpus we don't need."""
    e = FishEngine.__new__(FishEngine)
    e.state_dir = state
    return e


def _repo(tmp, identity=True):
    state = Path(tmp) / "fish_state"
    state.mkdir()
    _git(state, "init", "--initial-branch=master")
    if identity:
        _git(state, "config", "user.email", "test@example.com")
        _git(state, "config", "user.name", "test")
    else:
        # isolated_git_env empties the global config; this stops git
        # synthesizing an identity from username@hostname, which succeeds
        # on any box whose hostname resolves to a plausible FQDN.
        _git(state, "config", "user.useConfigOnly", "true")
    return state


def test_commit_returns_true_on_success():
    with tempfile.TemporaryDirectory() as tmp:
        state = _repo(tmp)
        (state / "fish.md").write_text("# fish\n", encoding="utf-8")
        assert _engine(state)._git_commit("real commit") is True


def test_nothing_to_commit_is_silent_and_false(caplog):
    """An idle fish is the common case, not a failure. It must not warn."""
    with tempfile.TemporaryDirectory() as tmp:
        state = _repo(tmp)
        (state / "fish.md").write_text("# fish\n", encoding="utf-8")
        engine = _engine(state)
        assert engine._git_commit("first") is True

        with caplog.at_level(logging.WARNING, logger="linafish.engine"):
            assert engine._git_commit("nothing changed") is False
        assert caplog.records == [], \
            f"idle commit warned: {[r.getMessage() for r in caplog.records]}"


def test_missing_identity_warns_and_returns_false(caplog):
    """The original bug: no committer identity, every commit lost, silently."""
    with tempfile.TemporaryDirectory() as tmp:
        state = _repo(tmp, identity=False)
        (state / "fish.md").write_text("# fish\n", encoding="utf-8")

        with caplog.at_level(logging.WARNING, logger="linafish.engine"):
            assert _engine(state)._git_commit("doomed") is False

        assert len(caplog.records) == 1, "expected exactly one warning"
        msg = caplog.records[0].getMessage()
        assert "NOT being versioned" in msg
        assert "config user.email" in msg, "warning must name the fix"


def test_warning_is_deduped_across_instances(caplog):
    """A persistently broken repo must warn once, not once per eat —
    including across the short-lived engines the CLI builds in a loop."""
    with tempfile.TemporaryDirectory() as tmp:
        state = _repo(tmp, identity=False)
        (state / "fish.md").write_text("# fish\n", encoding="utf-8")

        FishEngine._git_warned.clear()
        with caplog.at_level(logging.WARNING, logger="linafish.engine"):
            _engine(state)._git_commit("first")
            _engine(state)._git_commit("second")
            _engine(state)._git_commit("third")

        assert len(caplog.records) == 1, \
            f"expected 1 warning, got {len(caplog.records)}"


def test_commit_never_raises_when_git_is_missing(monkeypatch):
    """Callers run this inside eats and signal handlers. It must degrade,
    not explode."""
    with tempfile.TemporaryDirectory() as tmp:
        state = Path(tmp) / "fish_state"
        state.mkdir()

        def boom(*a, **kw):
            raise FileNotFoundError("git")

        monkeypatch.setattr(subprocess, "run", boom)
        assert _engine(state)._git_commit("no git here") is False


def test_timeout_is_not_reported_as_missing_git():
    """git hung != git absent. The hint sends users in opposite directions,
    so _git_run must not collapse both onto 'git not available'."""
    with tempfile.TemporaryDirectory() as tmp:
        state = _repo(tmp)
        rc, _, err = _engine(state)._git_run("log", timeout=0.0001)
        assert rc == -1
        assert "timed out" in err.lower()
        assert "not available" not in err.lower()
