"""The docs are an inventory, and an inventory needs to be able to be wrong.

Born 2026-08-31, the same day `capabilities` was caught printing a hardcoded
list of 26 commands while the dispatch table held 43. It had been drifting for
as long as anyone had been adding verbs, and nothing noticed, because a list
maintained by hand cannot notice a missing entry — it always reads as complete.

The README's CLI reference is the same kind of object, one layer up, and it had
drifted further: 13 of 43. So it gets a test. Not a test that the docs are
COMPLETE — that would fail forever and get muted, and a muted test is worse
than no test. A test that every command the docs *promise* actually exists.

The asymmetry is deliberate:

  - A verb in the docs that is NOT in the code is a LIE to a reader who will
    type it and get an error. That fails here, loudly.
  - A verb in the code that is not in the docs is an omission. It's caught by
    `linafish capabilities`, which derives from the dispatch table and cannot
    drift, so the reader always has a truthful way to see everything.
"""

import re
from pathlib import Path

import pytest

from linafish.__main__ import _COMMAND_TABLE

REPO = Path(__file__).resolve().parent.parent


def _code_regions(text: str) -> list:
    """Fenced blocks and inline code spans only.

    Prose is excluded on purpose. "the linafish fish grows" is English, not an
    invocation, and a test that flags it teaches people to mute the test.
    """
    regions = re.findall(r"```.*?```", text, re.S)
    regions += re.findall(r"`[^`\n]+`", text)
    return regions


def _documented_commands(text: str) -> set:
    """Every `linafish <verb>` invocation a reader could actually type."""
    found = set()
    for region in _code_regions(text):
        for line in region.splitlines():
            line = line.strip().lstrip("`$ ")
            # Only a line that STARTS with the invocation is a promise.
            m = re.match(r"^linafish\s+([a-z][a-z0-9_-]*)", line)
            if m:
                found.add(m.group(1))
    return found


# Words that follow "linafish" in prose without being commands.
_NOT_COMMANDS = {
    "is",
    "can",
    "as",
    "the",
    "and",
    "on",
    "in",
    "to",
    "it",
    "reads",
    "if",
    "for",
    "a",
    "you",
    "your",
    "does",
    "was",
    "has",
    "with",
    "from",
    "that",
    "this",
    "or",
    "but",
    "so",
    "at",
    "by",
    "of",
    "not",
    "no",
    "python",
    "pip",
    "clean",
}


@pytest.mark.parametrize("doc", ["README.md", "AGENTS.md"])
def test_every_command_the_docs_promise_actually_exists(doc):
    path = REPO / doc
    if not path.is_file():
        pytest.skip(f"{doc} not present")
    documented = _documented_commands(path.read_text(encoding="utf-8"))
    claimed = {c for c in documented if c not in _NOT_COMMANDS}
    missing = sorted(c for c in claimed if c not in _COMMAND_TABLE)
    assert not missing, (
        f"{doc} tells the reader to run commands that do not exist: {missing}. "
        f"Either add them to the dispatch table or stop promising them."
    )


def test_the_fish_header_only_advertises_commands_that_exist():
    """The fish announces its own query surface. That announce is an inventory.

    Added with the announce block itself, 2026-08-31. The fish.md is the artifact
    that TRAVELS — it is pasted into other people's AIs, on machines we will never
    see. A stale verb here does not produce a stale document; it produces a reader
    that runs a command that does not exist and concludes the fish is broken.
    That is precisely what happened to a mind reading `capabilities` this morning.
    """
    import subprocess
    import sys
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as td:
        src = Path(td) / "src"
        src.mkdir()
        (src / "a.md").write_text(
            "I keep starting things at night and abandoning them by Thursday, "
            "losing interest the moment it turns into maintenance.\n",
            encoding="utf-8",
        )
        state = Path(td) / "state"
        subprocess.run(
            [
                sys.executable, "-m", "linafish", "eat", str(src),
                "-n", "probe", "--state-dir", str(state),
            ],
            capture_output=True,
            cwd=str(REPO),
        )
        fish = state / "probe.fish.md"
        if not fish.is_file():
            pytest.skip("fish did not render in this environment")
        advertised = _documented_commands(fish.read_text(encoding="utf-8"))
        missing = sorted(c for c in advertised if c not in _COMMAND_TABLE)
        assert not missing, (
            f"the fish header advertises commands that do not exist: {missing}. "
            f"This file gets pasted into strangers' AIs — it must not lie to them."
        )
        # And it must actually advertise SOMETHING queryable, or the announce
        # has silently regressed to deposit-only, which is the bug it fixed.
        assert advertised & {"ask", "recall", "meditate"}, (
            "the fish header no longer tells its reader it can be QUERIED"
        )


def test_capabilities_is_derived_not_hardcoded():
    """Guard the 2026-08-31 fix from being un-fixed by a well-meaning edit.

    If someone replaces the derived list with a literal again, this catches it:
    a literal cannot track a verb added to the table at runtime.
    """
    import io
    from contextlib import redirect_stdout

    from linafish.__main__ import cmd_capabilities

    sentinel = "zzz_drift_probe"
    _COMMAND_TABLE[sentinel] = lambda args: None
    try:
        buf = io.StringIO()
        with redirect_stdout(buf):
            cmd_capabilities(None)
        assert sentinel in buf.getvalue(), (
            "capabilities did not report a command present in the dispatch "
            "table — it has gone back to printing a hardcoded list."
        )
    finally:
        _COMMAND_TABLE.pop(sentinel, None)
