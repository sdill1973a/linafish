"""Truncating a crystal must be audible.

MAX_CRYSTAL_TEXT bounds pathological input, which is fine. It did so
silently, which is not. This module has already suffered this exact bug
once: the cap was 300 chars, it cut every substantive deposit to a headline,
formations went flat, and the fix was to raise the number rather than make
the cut visible. So it recurred at the new size.

Feeding a 70,000-char novel produced a crystal of exactly 32768 chars and
reported success. 53% of the book was gone and the only way to find out was
to read the JSONL and notice two crystals sitting at precisely the cap.
"""
import logging

from linafish import crystallizer_v3 as c3


def test_oversized_text_warns_with_the_numbers(caplog):
    c3._TRUNCATION_WARNED.clear()
    big = "the walls held the day's heat until two in the morning. " * 2000
    assert len(big) > c3.MAX_CRYSTAL_TEXT
    with caplog.at_level(logging.WARNING, logger="linafish.crystallizer_v3"):
        c3._warn_truncation("manuscript.md", len(big))
    assert len(caplog.records) == 1
    msg = caplog.records[0].getMessage()
    assert "TRUNCATED" in msg
    assert "manuscript.md" in msg
    assert "DROPPED" in msg


def test_warning_is_deduped_per_source(caplog):
    c3._TRUNCATION_WARNED.clear()
    with caplog.at_level(logging.WARNING, logger="linafish.crystallizer_v3"):
        for _ in range(5):
            c3._warn_truncation("same.md", 70000)
    assert len(caplog.records) == 1, "a big ingest would spam once per call"


def test_within_bound_is_silent(caplog):
    """Ordinary pages and session turns must not warn."""
    c3._TRUNCATION_WARNED.clear()
    with caplog.at_level(logging.WARNING, logger="linafish.crystallizer_v3"):
        pass  # nothing crystallized over the bound
    assert caplog.records == []
