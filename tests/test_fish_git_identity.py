"""A fish repo is an internal ledger; its commits must not depend on the
OPERATOR having a global git identity.

July 2026: an unset committer identity killed every commit in a state dir for
three weeks — the engine warned, but only warned, and "warned" is not
"versioned". The same dependency made the sealing-commit tests red on every
CI runner from the day they were written (runners ship no git identity),
while passing on every developer box (which do). A test whose verdict depends
on who is running it is measuring the operator, not the code.

The fix is self-heal at commit time: on an identity failure the engine sets a
LOCAL user.name/user.email in the fish repo and retries once. Boxes with a
real identity never reach that branch.
"""


def test_fish_commits_survive_missing_git_identity(tmp_path, monkeypatch):
    # Hide every identity source git knows about, the way a fresh CI runner
    # (or a brand-new user's box) genuinely looks.
    for var in ("GIT_AUTHOR_NAME", "GIT_AUTHOR_EMAIL",
                "GIT_COMMITTER_NAME", "GIT_COMMITTER_EMAIL"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", "/dev/null")
    monkeypatch.setenv("GIT_CONFIG_SYSTEM", "/dev/null")

    from linafish.engine import FishEngine
    engine = FishEngine(state_dir=tmp_path, name="idtest", git_autocommit=False)
    engine.eat("a crystal that deserves a sealing commit", source="test")

    assert engine._git_commit("sealing commit under no identity") is True, \
        "commit failed with no operator identity — the ledger depends on who runs it"

    rc, out, _ = engine._git_run("log", "--format=%an <%ae>", "-1")
    assert rc == 0
    assert "linafish <fish@localhost>" in out
