"""Shared text-normalization helpers for content-dedup hashing.

The original `_content_hash` in crystallizer_v3.py and the listener's inline
MD5 in daemon.py both hashed raw text without normalization. MQTT broadcasts
that arrive shaped like::

    [2026-04-21T17:14:08.037Z anchor/conv/lab from=unknown]
    ALL MINDS — new topic: room/all on .67:1883. ...

have a per-message timestamp prefix line that varies on every arrival, so
byte-equivalence dedup fails: every broadcast hashes uniquely.

`normalize_for_dedup` strips the leading ``[timestamp source]`` line, lowercases,
and collapses whitespace runs. Empirical validation against 12,107 me-fish
crystals (2026-04-28): 10,135 ALL MINDS announcements that produce 10,135
distinct raw hashes collapse to 23 distinct normalized hashes (compression
ratio ~440×). The 23 buckets correctly preserve the legitimately-different
TRIAGE rephrasings as separate entries.

Both the listener plate-dedup and the engine `_content_hash` import this
helper so the two layers stay in lock-step. If the normalization rule
changes, change it here.
"""
from __future__ import annotations

import re

# Strip a single leading line of the form "[2026-04-21T17:14:08.037Z anchor/conv/lab from=unknown]\n"
# This is the MQTT-bridged timestamp+source prefix that wraps the actual content.
_TIMESTAMP_PREFIX = re.compile(r'^\[\d{4}-\d{2}-\d{2}T[^\]]*\][^\n]*\n?')

# Collapse internal whitespace runs to a single space.
_WHITESPACE_RUN = re.compile(r'\s+')


def normalize_for_dedup(text: str) -> str:
    """Return a canonical form of ``text`` for content-dedup hashing.

    Operations (in order):
      1. Strip leading ``[timestamp source]`` line, if present.
      2. Lowercase.
      3. Collapse whitespace runs to single spaces.
      4. Strip leading/trailing whitespace.

    Idempotent: ``normalize_for_dedup(normalize_for_dedup(x)) == normalize_for_dedup(x)``.

    Pure read; never raises on weird unicode (Python's str ops handle it).
    """
    if not text:
        return ""
    text = _TIMESTAMP_PREFIX.sub("", text)
    text = text.lower()
    text = _WHITESPACE_RUN.sub(" ", text)
    return text.strip()
