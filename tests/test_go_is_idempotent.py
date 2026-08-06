"""`linafish go` run twice on the same folder must not re-eat it (#52).

Three properties, all false on master:

1. **Re-running does not duplicate.** Append semantics meant a second `go`
   ate the whole corpus again. That is not merely an inflated count:
   `gamma(v, v) = 1.0`, so a crystal present twice satisfies
   `detect_formations` OUT OF ITSELF at maximal coupling, outranking every
   genuine cross-document formation. Duplication drowns the relationships
   the fish exists to find.

2. **The store is not replaced by the run's set.** The batch path did
   `engine.fish.crystals = all_crystals`, dropping in memory the crystals
   loaded from disk while they stayed on disk. `_save_state` counts memory,
   so the footer described a population that existed in no file. Survivable
   under append; fatal under skip, where a re-run adding three passages
   would write a store of 3 over a file of thousands.

3. **A no-op re-run and an unreadable corpus do not print the same thing.**
   Both end with zero new crystals — identical number, opposite meaning.
   "I looked and found nothing new" is a finding; "I could not look" is an
   excuse, and one number for both reports the excuse in the finding's
   voice. This is [[an-organ-must-be-able-to-fail]] applied to a footer:
   the run must be able to say it failed, distinguishably.
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from linafish import quickstart


def _crystals(state_dir: Path, name: str) -> list[dict]:
    f = state_dir / f"{name}_crystals.jsonl"
    assert f.exists(), f"no crystal store at {f}"
    return [json.loads(line) for line in f.read_text().splitlines() if line.strip()]


def _corpus(tmp_path: Path, n_docs: int = 6, headers: bool = True) -> Path:
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    lines = [
        "The pattern was there before I had a word for it.",
        "Compression is understanding, not storage.",
        "I checked the disk instead of trusting the story.",
        "What I wrote down is not what I remember writing.",
    ]
    for i in range(n_docs):
        body = ([f"# note {i}", ""] if headers else [])
        for j in range(4):
            body += [lines[(i + j) % len(lines)], ""]
        (corpus / f"note_{i:03d}.md").write_text("\n".join(body))
    return corpus


def test_second_go_adds_nothing(tmp_path, capsys):
    corpus = _corpus(tmp_path)
    state = tmp_path / "state"

    quickstart.go(source=str(corpus), name="probe", state_dir=str(state), serve=False)
    first = _crystals(state, "probe")
    assert first, "first run produced no crystals — test is not testing anything"

    quickstart.go(source=str(corpus), name="probe", state_dir=str(state), serve=False)
    second = _crystals(state, "probe")

    assert len(second) == len(first), (
        f"re-running go grew the store {len(first)} -> {len(second)}; the "
        f"corpus was eaten twice"
    )

    texts = [r.get("text", "") for r in second]
    assert len(set(texts)) == len(texts), "duplicate crystal texts in the store"


def test_second_go_says_nothing_new(tmp_path, capsys):
    corpus = _corpus(tmp_path)
    state = tmp_path / "state"

    quickstart.go(source=str(corpus), name="probe", state_dir=str(state), serve=False)
    capsys.readouterr()
    quickstart.go(source=str(corpus), name="probe", state_dir=str(state), serve=False)
    out = capsys.readouterr().out

    assert "Nothing new" in out, (
        "a no-op re-run must SAY it was a no-op — otherwise a successful "
        "skip is indistinguishable from a corpus that could not be read"
    )


def test_unreadable_corpus_does_not_wear_the_no_op_sentence(tmp_path, capsys):
    """The failure direction. An empty result and a blind run differ."""
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "too_short.md").write_text("hi")

    state = tmp_path / "state"
    try:
        quickstart.go(source=str(corpus), name="probe", state_dir=str(state), serve=False)
    except SystemExit:
        return  # refusing outright is an acceptable, distinguishable failure
    out = capsys.readouterr().out

    assert "Nothing new — all" not in out, (
        "a corpus that could not be read printed the successful-skip "
        "sentence; the run reported an excuse in a finding's voice"
    )


def test_new_material_still_lands_on_a_second_run(tmp_path):
    """Skip must not become 'ignore the folder'. The whole point of a second
    run is that already-held crystals get to couple with genuinely new ones."""
    corpus = _corpus(tmp_path, n_docs=6)
    state = tmp_path / "state"

    quickstart.go(source=str(corpus), name="probe", state_dir=str(state), serve=False)
    before = len(_crystals(state, "probe"))

    (corpus / "note_new.md").write_text(
        "# note new\n\nThe river kept its own count and never once told him.\n\n"
        "He had been waiting on a number that was already written down.\n"
    )
    quickstart.go(source=str(corpus), name="probe", state_dir=str(state), serve=False)
    after = len(_crystals(state, "probe"))

    assert after > before, (
        f"new material did not land on a second run ({before} -> {after}); "
        f"skip semantics degenerated into ignoring the source"
    )
