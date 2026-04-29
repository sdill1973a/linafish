"""Shared text-normalization helper for content-dedup hashing.

MQTT broadcasts arrive shaped like::

    [2026-04-21T17:14:08.037Z anchor/conv/lab from=unknown]
    ALL MINDS — new topic: room/all on .67:1883. ...

The per-message timestamp+source prefix line varies on every arrival, so
byte-equivalence dedup fails: every broadcast hashes uniquely. The listener
plate-dedup in ``daemon.py`` (which the listener docstring already declared
"skip any already-crystallized content by text hash") was meant to rate-
limit MQTT bridge near-duplicates, but the inline MD5 was hashing raw text
including the variable prefix.

``normalize_for_dedup`` strips the leading ``[timestamp source]\\n`` line
(REQUIRES a trailing newline — single-line ``[ts] body`` is left intact
to avoid false-collapsing distinct messages), lowercases, and collapses
whitespace runs. Empirical validation against 12,107 me-fish crystals
(2026-04-28): 10,135 ALL MINDS announcements that produce 10,135 distinct
raw hashes collapse to 23 normalized hashes (compression ratio ~440×).
The 23 buckets correctly preserve the legitimately-different TRIAGE
rephrasings as separate entries.

**Allowed callers** (non-storage layers only):
  - ``daemon.py`` listener plate-dedup — rate-limits MQTT bridge near-duplicates.
  - ``formations.py`` ``content_diversity`` computation — surface-ranking
    signal: ``unique_normalized_hashes / crystal_count``. NOT a storage
    operation; never modifies a crystal.

**FORBIDDEN caller**: the engine ``_content_hash`` in ``crystallizer_v3.py``.
That function is intentionally byte-exact and does NOT import this helper.
Engine-side dedupe is opt-in via ``dedupe=True`` and means "caller promised
the same byte-equivalent text won't be ingested twice." Normalizing at the
engine layer would expand what counts as duplicate to include timestamp
variants — a STORAGE-policy change beyond what ``dedupe=True`` declared.
``tests/test_dedup_helpers.py::TestEngineListenerDivergence`` asserts this
divergence as a regression guard. **Do not re-couple this helper to
``_content_hash``.** If future code needs an engine-side normalized-
equivalence operation, build a separate, explicitly-named function.

**IMPORTANT**: do NOT add ``re.MULTILINE`` to the ``_TIMESTAMP_PREFIX``
compile flag. The ``^`` anchor MUST match string-start only — adding
MULTILINE would strip prefixes mid-body, eating user-quoted content
that happens to look like a timestamp line.
"""
from __future__ import annotations

from typing import Optional
import re

# Strip a single leading line of the form
# "[2026-04-21T17:14:08.037Z anchor/conv/lab from=unknown]\n".
# The trailing newline is REQUIRED — without it, single-line content like
# "[2026-04-21T...source] ACTUAL BODY" would have its body consumed by the
# greedy [^\n]* match, collapsing every distinct single-line message to
# empty. Bracketed content must NOT span newlines either, hence [^\]\n]*.
_TIMESTAMP_PREFIX = re.compile(r'^\[\d{4}-\d{2}-\d{2}T[^\]\n]*\][^\n]*\n')

# Collapse internal whitespace runs to a single space.
_WHITESPACE_RUN = re.compile(r'\s+')


def normalize_for_dedup(text: Optional[str]) -> str:
    """Return a canonical form of ``text`` for content-dedup hashing.

    Operations (in order):
      1. Strip a leading ``[timestamp source]\\n`` line, if present
         (requires trailing newline; single-line prefixed text is
         left intact).
      2. Lowercase.
      3. Collapse whitespace runs to single spaces.
      4. Strip leading/trailing whitespace.

    Idempotent: ``normalize_for_dedup(normalize_for_dedup(x)) == normalize_for_dedup(x)``.

    Pure read; never raises on weird unicode (Python's str ops handle it).
    Accepts None by returning empty string (defensive null-input guard).
    """
    if not text:
        return ""
    text = _TIMESTAMP_PREFIX.sub("", text)
    text = text.lower()
    text = _WHITESPACE_RUN.sub(" ", text)
    return text.strip()
