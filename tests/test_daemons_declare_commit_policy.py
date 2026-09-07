"""Every daemon entry point must SAY what its git commit policy is.

Olorina, reviewing linafish#76 (2026-09-07): flipping FishEngine's git_autocommit default
to False is right — but a long-running daemon never closes its stream, so the
flush_commit()/session_end() escape hatch never reaches it. A daemon constructed with no
policy does not go from many rollback points to few; it goes to ZERO, forever, silently —
the JSONL keeps growing and the git history simply stops, which looks exactly like a
healthy quiet fish until someone needs to roll back. 558 green could not see it: no test
asserted a daemon ever commits at all.

This is the test she asked for instead of four one-line fixes. It keeps the NEXT daemon
honest too. Source-level on purpose: constructing the real entry points would start loops.
The rule is uniform and checkable — no FishEngine( in a daemon module without an explicit
commit_every_n_eats= or git_autocommit= keyword. A one-shot seeder (keeper, daily) passes
git_autocommit=False and flushes at the end of its stream; that is a declared policy too.
"""
import ast
from pathlib import Path

PKG = Path(__file__).resolve().parent.parent / "linafish"

# Modules that construct an engine and then eat over time (daemons) or eat a whole
# stream at once (seeders). Add a module here when it grows a FishEngine( call.
DAEMON_MODULES = ["converse", "http_server", "daemon", "school", "guppy", "keeper", "daily"]
POLICY_KWARGS = {"commit_every_n_eats", "git_autocommit"}


def _engine_calls(src: str):
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Call):
            f = node.func
            name = f.id if isinstance(f, ast.Name) else (f.attr if isinstance(f, ast.Attribute) else None)
            if name == "FishEngine":
                yield node


def test_every_daemon_engine_declares_a_commit_policy():
    missing = []
    for mod in DAEMON_MODULES:
        path = PKG / f"{mod}.py"
        src = path.read_text(encoding="utf-8")
        for call in _engine_calls(src):
            kws = {k.arg for k in call.keywords}
            if "**" in {k.arg for k in call.keywords if k.arg is None} or any(k.arg is None for k in call.keywords):
                continue  # explicit passthrough — the caller owns the policy
            if not (kws & POLICY_KWARGS):
                missing.append(f"{mod}.py:{call.lineno}")
    assert not missing, (
        "FishEngine constructed in a daemon/seeder module with NO commit policy — with the "
        "library default now False these would never commit, forever, silently: "
        + ", ".join(missing))


def test_the_check_itself_can_fail():
    """The organ must be seen to fail: a bare construction must be caught."""
    bare = "from .engine import FishEngine\nengine = FishEngine(state_dir=d, name='x')\n"
    calls = list(_engine_calls(bare))
    assert len(calls) == 1
    assert not ({k.arg for k in calls[0].keywords} & POLICY_KWARGS)
