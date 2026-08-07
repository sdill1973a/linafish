"""`linafish go` is the verb most people run. Guard what it produces.

The existing chunk-bound tests (test_ingest_chunk_bound.py) assert on
`ingest_file`, which was never on `go`'s path — so they passed while a
70,000-character book arrived as one truncated crystal. These tests assert
on the crystal store AFTER a real `go`, which is the only place the defect
was visible.

Three properties, each of which was false on master:

1. A headerless manuscript arrives as many crystals, none over the bound,
   split on the author's paragraphs rather than at arbitrary 4000-char cuts.
2. Nothing is silently dropped — `go` used to lose 69% of a book to
   MAX_CRYSTAL_TEXT without saying so.
3. A corpus over the batch threshold still produces formations. Batch mode
   installs crystals without eat(), so in addressed-formations mode nothing
   filed them and every large corpus finished with zero formations.
"""
import json
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from linafish import quickstart
from linafish.ingest import MAX_CHUNK_CHARS, ingest_file


def _crystals(state_dir: Path, name: str) -> list[dict]:
    f = state_dir / f"{name}_crystals.jsonl"
    assert f.exists(), f"no crystal store at {f}"
    return [json.loads(line) for line in f.read_text().splitlines() if line.strip()]


def _formation_count(state_dir: Path, name: str) -> int:
    md = (state_dir / f"{name}.fish.md").read_text()
    m = re.search(r'formation_count":\s*(\d+)', md)
    assert m, "fish.md carries no formation_count"
    return int(m.group(1))


def _headerless_manuscript(paragraphs: int = 300) -> str:
    """No `#` headers, scene breaks as `*   *   *`, blank-line paragraphs.

    The shape of a real manuscript, and the shape that broke: markdown
    header-chunking finds nothing, so the whole file used to arrive as one
    chunk however well-formed it was.
    """
    out = []
    for i in range(paragraphs):
        out.append(
            f"He had counted the days again on the {i}th morning and the number "
            f"was the same as it had been, which told him nothing he did not "
            f"already know about the river or about waiting."
        )
        if i and i % 40 == 0:
            out.append("*   *   *")
    return "\n\n".join(out)


def test_go_chunks_a_headerless_manuscript_on_its_own_paragraphs(tmp_path):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    text = _headerless_manuscript()
    (corpus / "manuscript.md").write_text(text)
    assert "#" not in text, "fixture must be headerless"
    assert len(text) > 5 * MAX_CHUNK_CHARS, "fixture must be big enough to matter"

    state = tmp_path / "state"
    quickstart.go(source=str(corpus), name="probe", state_dir=str(state), serve=False)

    rows = _crystals(state, "probe")
    sizes = [len(r.get("text", "")) for r in rows]

    # It is not one crystal. That was the whole bug.
    assert len(rows) > 1, "a whole book arrived as a single crystal"

    # Nothing exceeds the guarantee.
    assert max(sizes) <= MAX_CHUNK_CHARS, f"crystal over the bound: {max(sizes)}"

    # And the split honors the author's structure rather than the backstop.
    # Arbitrary 4000-char cutting produces crystals flush against the bound;
    # paragraph splitting does not. This is the assertion that distinguishes
    # the correct fix from the one that merely looks like a success.
    against_bound = sum(1 for s in sizes if s >= MAX_CHUNK_CHARS * 0.95)
    assert against_bound == 0, (
        f"{against_bound}/{len(sizes)} crystals sit against the bound — "
        f"this is arbitrary cutting, not paragraph splitting"
    )


def test_go_does_not_silently_drop_content(tmp_path):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    text = _headerless_manuscript()
    (corpus / "manuscript.md").write_text(text)

    state = tmp_path / "state"
    quickstart.go(source=str(corpus), name="probe", state_dir=str(state), serve=False)

    rows = _crystals(state, "probe")
    kept = sum(len(r.get("text", "")) for r in rows)

    # Master kept 32,768 characters of a 69,416-character book — one
    # crystal truncated at MAX_CRYSTAL_TEXT, reported as success.
    assert kept > 0.9 * len(text), (
        f"kept {kept} of {len(text)} chars ({kept / len(text):.0%}) — content "
        f"is being dropped without a word"
    )

    # Every crystal's text has to actually come from the source.
    def norm(s):
        return re.sub(r"\s+", " ", s).strip()

    src = norm(text)
    for r in rows:
        t = norm(r.get("text", ""))
        if t:
            assert t in src, "crystal text is not verbatim from the source"


def test_go_over_the_batch_threshold_still_forms(tmp_path):
    """Formations are the product. Batch mode produced none of them.

    Deliberately headered, short documents: chunking is not a variable here,
    so a failure means the batch path itself, not the reader.
    """
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    lines = [
        "The pattern was there before I had a word for it.",
        "Compression is understanding, not storage.",
        "I checked the disk instead of trusting the story.",
        "What I wrote down is not what I remember writing.",
    ]
    n_docs = 210  # over quickstart's batch threshold of 200
    for i in range(n_docs):
        body = [f"# note {i}", ""]
        for j in range(4):
            body += [lines[(i + j) % len(lines)], ""]
        (corpus / f"note_{i:03d}.md").write_text("\n".join(body))

    state = tmp_path / "state"
    quickstart.go(source=str(corpus), name="probe", state_dir=str(state), serve=False)

    rows = _crystals(state, "probe")
    assert len(rows) >= n_docs, "batch mode lost crystals"
    assert _formation_count(state, "probe") > 0, (
        "a corpus over the batch threshold produced zero formations — the "
        "crystals were installed without ever being filed into the index"
    )


def test_headered_markdown_still_chunks_by_header(tmp_path):
    """The fallback must only fire when there are genuinely no headers."""
    p = tmp_path / "doc.md"
    p.write_text(
        "# One\n\n" + "Alpha sentence about the first thing. " * 4 + "\n\n"
        "# Two\n\n" + "Beta sentence about the second thing. " * 4 + "\n\n"
        "# Three\n\n" + "Gamma sentence about the third thing. " * 4 + "\n"
    )
    chunks = ingest_file(p)
    sections = [c.section for c in chunks]
    assert "One" in sections and "Two" in sections and "Three" in sections, (
        f"header sections lost: {sections}"
    )


def test_headerless_plain_text_unchanged(tmp_path):
    """read_text already used chunk_by_paragraphs. Prove it stayed put."""
    p = tmp_path / "doc.txt"
    p.write_text(_headerless_manuscript(paragraphs=60))
    chunks = ingest_file(p)
    assert len(chunks) > 1
    assert max(len(c.text) for c in chunks) <= MAX_CHUNK_CHARS
