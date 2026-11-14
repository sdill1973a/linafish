"""Release review 2026-11-14, lane cli_mcp: every verb run as a stranger would, from a scratch HOME.

Five defects, each pinned here through the real CLI (subprocess), the way the other CLI tests
in this directory work:

  1. `converse` without -n served an EMPTY fish named `linafish` beside the one real fish in
     the state dir (parser default). http/serve were fixed in 2.3.2; converse was not.
  2. The MCP server gave NO reply to a request it did not implement (resources/list,
     prompts/list) — a JSON-RPC request with an id must get a response, or the client waits
     until its own timeout.
  3. `eat` on a sealed fish printed "0 crystals added" and a portrait, exit 0.
  4. `live` / `seal` / `compact` / `revectorize` saved without committing, so `history` did
     not show them and `revert` died on "local changes would be overwritten". And the commit
     must not store `<name>_crystals.jsonl.bak-pre-rewrite` (a full copy of every crystal).
  5. `doctor` / `capabilities` printed a PyMuPDF FutureWarning on stderr every run.
"""
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

TEXTS = [
    "I spent the morning fixing the garden fence because the posts had rotted at the base and I like work you can see.",
    "Called my sister about the trip; we keep circling spring or summer and I want to decide by Friday so we can book.",
    "Read two chapters on river ecology; floods rebuild the bank, and damage and repair are one process from two ends.",
]


def _env(home):
    env = {**os.environ, "HOME": str(home), "USERPROFILE": str(home), "PYTHONPATH": str(ROOT)}
    env.pop("LINAFISH_PROTECTED_VOCAB", None)
    return env


def _cli(home, *argv, stdin=None, timeout=300):
    return subprocess.run([sys.executable, "-m", "linafish", *argv], env=_env(home), cwd=str(home),
                          capture_output=True, text=True, timeout=timeout, input=stdin)


def _fish(home, state, name):
    src = home / f"src-{name}"
    src.mkdir(exist_ok=True)
    for i, t in enumerate(TEXTS):
        (src / f"d{i}.txt").write_text(t, encoding="utf-8")
    r = _cli(home, "eat", str(src), "-n", name, "--state-dir", str(state))
    assert r.returncode == 0, r.stdout + r.stderr
    return state


def _free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _git(state, *argv):
    return subprocess.run(["git", "-C", str(state), *argv], capture_output=True, text=True, timeout=60)


# --- 1. converse -n default -------------------------------------------------------------------

def test_converse_without_name_refuses_when_several_fish_live_there(tmp_path):
    state = tmp_path / "state"
    _fish(tmp_path, state, "alpha")
    _fish(tmp_path, state, "beta")
    r = _cli(tmp_path, "converse", "--state-dir", str(state), "-p", str(_free_port()), timeout=120)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "Several fish live here" in r.stdout and "alpha" in r.stdout and "beta" in r.stdout


def test_converse_without_name_serves_the_one_fish(tmp_path):
    state = tmp_path / "state"
    _fish(tmp_path, state, "alpha")
    port = _free_port()
    proc = subprocess.Popen([sys.executable, "-m", "linafish", "converse", "--state-dir", str(state),
                             "-p", str(port)], env=_env(tmp_path), cwd=str(tmp_path),
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        health = None
        for _ in range(100):
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=1) as resp:
                    health = json.loads(resp.read())
                break
            except Exception:
                time.sleep(0.2)
        assert health is not None, "converse never answered /health"
        # Before the fix: name 'linafish', crystals 0 — an empty fish served beside the real one.
        assert health["name"] == "alpha", health
        assert health["crystals"] == len(TEXTS), health
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            proc.kill()
    assert not (state / "linafish_crystals.jsonl").exists(), "converse must not create a stray 'linafish' fish"


# --- 2. MCP server answers every request --------------------------------------------------------

def _mcp(home, state, name, *messages):
    lines = "\n".join(json.dumps(m) for m in messages) + "\n"
    r = _cli(home, "serve", "-n", name, "--state-dir", str(state), stdin=lines, timeout=120)
    assert r.returncode == 0, r.stderr
    out = [l for l in r.stdout.splitlines() if l.strip()]
    parsed = []
    for l in out:
        try:
            parsed.append(json.loads(l))
        except json.JSONDecodeError:
            pytest.fail(f"MCP stdout line is not JSON (the stdio channel is corrupt): {l[:200]}")
    return parsed


def test_mcp_unknown_request_gets_method_not_found_and_notifications_stay_silent(tmp_path):
    state = _fish(tmp_path, tmp_path / "state", "alpha")
    replies = _mcp(tmp_path, state, "alpha",
                   {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
                   {"jsonrpc": "2.0", "method": "notifications/initialized"},
                   {"jsonrpc": "2.0", "method": "notifications/no-such-thing", "params": {}},
                   {"jsonrpc": "2.0", "id": 6, "method": "resources/list"},
                   {"jsonrpc": "2.0", "id": 7, "method": "prompts/list"},
                   {"jsonrpc": "2.0", "id": 8, "method": "ping"})
    by_id = {r.get("id"): r for r in replies}
    assert set(by_id) == {1, 6, 7, 8}, [r.get("id") for r in replies]  # notifications: no reply
    for rid in (6, 7):
        assert by_id[rid]["error"]["code"] == -32601, by_id[rid]
        assert "result" not in by_id[rid]
    assert by_id[8] == {"jsonrpc": "2.0", "id": 8, "result": {}}


def test_mcp_tools_round_trip_and_every_result_is_text(tmp_path):
    state = _fish(tmp_path, tmp_path / "state", "alpha")
    replies = _mcp(tmp_path, state, "alpha",
                   {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
                   {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
                   {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                    "params": {"name": "fish_health", "arguments": {}}},
                   {"jsonrpc": "2.0", "id": 4, "method": "tools/call",
                    "params": {"name": "fish_eat",
                               "arguments": {"text": "The fence held through the storm and I slept.",
                                             "source": "test"}}},
                   {"jsonrpc": "2.0", "id": 5, "method": "tools/call",
                    "params": {"name": "fish_taste", "arguments": {"text": "garden fence", "top": 2}}},
                   {"jsonrpc": "2.0", "id": 9, "method": "tools/call",
                    "params": {"name": "no_such_tool", "arguments": {}}})
    by_id = {r["id"]: r for r in replies}
    names = {t["name"] for t in by_id[2]["result"]["tools"]}
    assert names == {"fish_pfc", "fish_eat", "fish_taste", "fish_match", "fish_health"}
    for rid in (3, 4, 5, 9):
        content = by_id[rid]["result"]["content"]
        assert content[0]["type"] == "text" and isinstance(content[0]["text"], str), by_id[rid]
    assert json.loads(by_id[3]["result"]["content"][0]["text"])["name"] == "alpha"
    assert json.loads(by_id[4]["result"]["content"][0]["text"])["crystals_added"] == 1
    assert by_id[9]["result"]["isError"] is True
    # the eat reached disk
    log = (state / "alpha_crystals.jsonl").read_text(encoding="utf-8")
    assert "fence held through the storm" in log


# --- 3. eat on a sealed fish -------------------------------------------------------------------

def test_eat_on_sealed_fish_says_so_and_exits_nonzero(tmp_path):
    state = _fish(tmp_path, tmp_path / "state", "alpha")
    r = _cli(tmp_path, "seal", "-n", "alpha", "--state-dir", str(state))
    assert r.returncode == 0, r.stdout + r.stderr
    more = tmp_path / "more.txt"
    more.write_text("A new paragraph the sealed fish must refuse, and the owner must be told.", encoding="utf-8")
    r = _cli(tmp_path, "eat", str(more), "-n", "alpha", "--state-dir", str(state))
    assert r.returncode == 1, r.stdout + r.stderr
    assert "sealed" in r.stderr and "nothing eaten" in r.stderr, r.stderr
    assert "crystals added" not in r.stdout, r.stdout
    assert "sealed fish must refuse" not in (state / "alpha_crystals.jsonl").read_text(encoding="utf-8")


# --- 4. maintenance verbs commit; revert works after them ---------------------------------------

def test_live_compact_revectorize_seal_commit_and_revert_works(tmp_path):
    state = _fish(tmp_path, tmp_path / "state", "alpha")
    for verb in ("live", "compact", "revectorize", "seal"):
        r = _cli(tmp_path, verb, "-n", "alpha", "--state-dir", str(state))
        assert r.returncode == 0, verb + "\n" + r.stdout + r.stderr
    assert _git(state, "status", "--porcelain").stdout.strip() == "", _git(state, "status", "--porcelain").stdout
    log = _git(state, "log", "--format=%s").stdout.splitlines()
    assert log[0].startswith("seal: alpha"), log
    assert any(l.startswith("revectorize: alpha") for l in log), log
    assert any(l.startswith("compact: alpha") for l in log), log
    assert any(l.startswith("live: alpha") for l in log), log
    # the crystal-log backup compact/revectorize leave behind is not in the repo
    assert (state / "alpha_crystals.jsonl.bak-pre-rewrite").exists()
    assert ".bak-pre-rewrite" not in _git(state, "ls-files").stdout
    r = _cli(tmp_path, "revert", "-y", "HEAD", "-n", "alpha", "--state-dir", str(state))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "Reverted" in r.stdout


def test_new_fish_repo_ignores_crystal_backups(tmp_path):
    state = _fish(tmp_path, tmp_path / "state", "alpha")
    assert "*.bak-*" in (state / ".gitignore").read_text(encoding="utf-8").splitlines()


# --- 5. doctor / capabilities: clean stderr, no private labels ----------------------------------

def test_doctor_and_capabilities_do_not_warn_on_stderr(tmp_path):
    state = _fish(tmp_path, tmp_path / "state", "alpha")
    for argv in (("doctor", "--state-dir", str(state)), ("capabilities",)):
        r = _cli(tmp_path, *argv)
        assert r.returncode == 0, r.stdout + r.stderr
        assert "Warning" not in r.stderr, argv[0] + " stderr:\n" + r.stderr
    r = _cli(tmp_path, "doctor", "--state-dir", str(state))
    assert "me fish" not in r.stdout and "room fish" not in r.stdout, r.stdout


# --- docs: the -n default the servers actually have ---------------------------------------------

def test_configuration_doc_does_not_claim_a_linafish_name_default():
    text = (ROOT / "docs" / "configuration.md").read_text(encoding="utf-8")
    assert "(default: `linafish`)" not in text
    assert "`serve` uses a fish named `linafish`" not in text


# --- 6. keeper init: the printed next step must feed THIS keeper ---------------------------------

def test_keeper_init_feed_hint_runs_as_printed_on_a_custom_state_dir(tmp_path):
    state = tmp_path / "state"
    state.mkdir()
    r = _cli(tmp_path, "keeper", "init", "notes", "keeps the notes", "--state-dir", str(state))
    assert r.returncode == 0, r.stdout + r.stderr
    hint = next(l for l in r.stdout.splitlines() if l.startswith("Feed:"))
    cmd = hint.split("Feed:", 1)[1].split("<", 1)[0].strip()
    assert "--state-dir" in cmd, hint
    import shlex
    argv = shlex.split(cmd)[1:]  # drop the leading "linafish"
    r = _cli(tmp_path, *argv, stdin="A line fed by the printed hint, and it must reach the keeper itself.")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "fed by the printed hint" in (state / "notes-keeper" / "notes-keeper_crystals.jsonl").read_text(encoding="utf-8")
    # ...and not a brand-new fish of the same name under the default root
    assert not (tmp_path / ".linafish" / "notes-keeper_crystals.jsonl").exists()
    assert not (tmp_path / ".linafish" / "notes-keeper").exists()
