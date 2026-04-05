"""Tests for the mouth — can the fish eat?"""
import tempfile
from pathlib import Path

from linafish.ingest import ingest_file, Chunk


def test_ingest_markdown():
    with tempfile.NamedTemporaryFile(suffix=".md", delete=False, mode="w", encoding="utf-8") as f:
        f.write("# Section One\n\nThis is the first section with enough content to chunk.\n\n")
        f.write("# Section Two\n\nThis is the second section with different content entirely.\n")
        path = Path(f.name)

    chunks = ingest_file(path)
    assert len(chunks) >= 1
    assert all(isinstance(c, Chunk) for c in chunks)
    path.unlink()


def test_ingest_python():
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w", encoding="utf-8") as f:
        f.write('"""A test module."""\n\ndef hello():\n    """Say hello."""\n    return "world"\n\n')
        f.write('def goodbye():\n    """Say goodbye."""\n    return "night"\n')
        path = Path(f.name)

    chunks = ingest_file(path)
    assert len(chunks) >= 1
    path.unlink()


def test_ingest_txt():
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w", encoding="utf-8") as f:
        f.write("This is a plain text file with enough content to be worth ingesting.\n" * 5)
        path = Path(f.name)

    chunks = ingest_file(path)
    assert len(chunks) >= 1
    path.unlink()


def test_ingest_json():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w", encoding="utf-8") as f:
        f.write('{"name": "test", "description": "A test JSON file with enough content to chunk properly"}')
        path = Path(f.name)

    chunks = ingest_file(path)
    assert len(chunks) >= 1
    path.unlink()


def test_chunk_has_source():
    with tempfile.NamedTemporaryFile(suffix=".md", delete=False, mode="w", encoding="utf-8") as f:
        f.write("# Test\n\nContent that is long enough to survive the minimum length filter.\n")
        path = Path(f.name)

    chunks = ingest_file(path)
    assert all(c.source for c in chunks)
    path.unlink()
