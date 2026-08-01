"""A book must not arrive as one crystal.

Every reader splits on structure it hopes is there: markdown on `#` headers,
prose on blank lines. Manuscripts routinely have neither. A 70,000-character
novel whose scene breaks are `*   *   *` and whose paragraphs are single
newlines matched nothing and came through as ONE chunk — one crystal, one
vector, a whole book contributing less signal to the fish than a README.

It failed silently. The eat reported success, and 133 crystals looked
plausible right up until you noticed two of the eleven files were 1 chunk
each and they were the two that mattered.

Structure-splitting is now a preference. The bound is the guarantee.
"""
import tempfile
from pathlib import Path

from linafish.ingest import MAX_CHUNK_CHARS, ingest_file


def _write(tmp, name, text):
    p = Path(tmp) / name
    p.write_text(text, encoding="utf-8")
    return p


def test_headerless_manuscript_does_not_become_one_crystal():
    """The actual failure: no '#' headers, no blank lines. Haec v6."""
    body = "\n".join(
        f"He counted the days again, and the number was {i}, and the walls "
        f"held the heat until two in the morning and released it slowly."
        for i in range(600)
    )
    with tempfile.TemporaryDirectory() as tmp:
        chunks = ingest_file(_write(tmp, "manuscript.md", body))
    assert len(chunks) > 1, "a headerless manuscript still arrives as one chunk"
    assert all(len(c.text) <= MAX_CHUNK_CHARS for c in chunks)


def test_every_chunk_is_bounded_regardless_of_separator():
    """No blank lines, no newlines, no sentence punctuation — nothing to split
    on at all. The hard cut is ugly; a novel-sized crystal is worse."""
    with tempfile.TemporaryDirectory() as tmp:
        chunks = ingest_file(_write(tmp, "wall.txt", "word " * 20000))
    assert chunks
    assert all(len(c.text) <= MAX_CHUNK_CHARS for c in chunks)


def test_normal_files_are_left_alone():
    """The bound must not shred documents that chunked correctly before."""
    doc = "# One\n\nA short section.\n\n# Two\n\nAnother short section.\n"
    with tempfile.TemporaryDirectory() as tmp:
        chunks = ingest_file(_write(tmp, "notes.md", doc))
    assert len(chunks) == 2
    assert "short section" in chunks[0].text


def test_sentence_split_does_not_produce_a_crystal_per_sentence():
    """Fragments are reassembled up to the bound, not emitted individually."""
    body = " ".join(f"Sentence number {i} is here." for i in range(1200))
    with tempfile.TemporaryDirectory() as tmp:
        chunks = ingest_file(_write(tmp, "run-on.txt", body))
    assert all(len(c.text) <= MAX_CHUNK_CHARS for c in chunks)
    # Well short of one-per-sentence; each chunk should carry many.
    assert len(chunks) < 200, f"over-split into {len(chunks)} chunks"
    assert sum(len(c.text) for c in chunks) > len(body) * 0.9, \
        "content was dropped during splitting"
