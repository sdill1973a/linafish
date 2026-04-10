"""
mind_integration.py — Bridge between olorin_mind.py and crystallizer_v3.

The mind daemon calls compute_qlp_vector() and extract_keywords() inline.
This module provides drop-in replacements that use v3's MI × ache engine.

Usage in olorin_mind.py:
    # At top of file:
    from linafish.mind_integration import get_vectorizer_v3, compute_qlp_vector_v3, extract_keywords_v3
    USE_V3 = True

    # Where crystals are created:
    if USE_V3:
        resonance = compute_qlp_vector_v3(text)
        keywords = extract_keywords_v3(text)
    else:
        resonance = compute_qlp_vector(text)
        keywords = extract_keywords(text)
"""

import os
import sys

# Add parent for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from linafish.crystallizer_v3 import UniversalFish

_fish = None
STATE_DIR = "/home/dills/olorin/state"


def get_fish() -> UniversalFish:
    """Get or create the global v3 fish.

    On first call: loads vectorizer state, freezes if not frozen.
    Subsequent calls: returns cached instance.
    """
    global _fish
    if _fish is not None:
        return _fish

    _fish = UniversalFish(STATE_DIR)

    # If not frozen, try to load and freeze
    if not _fish.frozen:
        if _fish.vectorizer.doc_count > 0:
            _fish.freeze()
        else:
            # Need initial learning — load from existing crystals
            crystal_file = os.path.join(STATE_DIR, "mind_crystals.jsonl")
            if os.path.exists(crystal_file):
                print("[v3] Initial learn from existing crystals...", flush=True)
                count = _fish.learn_from_crystals_file(crystal_file)
                print(f"[v3] Learned from {count} crystals. Freezing.", flush=True)
                _fish.freeze()
            else:
                print("[v3] WARNING: No crystal file found. v3 will queue to pending.", flush=True)

    return _fish


def compute_qlp_vector_v3(text: str) -> list:
    """Drop-in replacement for compute_qlp_vector().

    Returns MI × ache vector. Same length as vocab (50 dims).
    Falls back to 8-dim zero vector if fish isn't ready.
    """
    fish = get_fish()
    if not fish.frozen:
        return [0.0] * 8  # fallback

    vec = fish.vectorizer.mi_ache_vector(text, fish.vocab)
    if not vec:
        return [0.0] * 8

    # Also feed to pending for next re-eat
    fish.pending.append({'text': text, 'source': 'mind_daemon'})

    return vec


def extract_keywords_v3(text: str, top_n: int = 5) -> list:
    """Drop-in replacement for extract_keywords().

    Uses IDF-weighted MI instead of keyword matching.
    """
    import math
    fish = get_fish()
    if not fish.frozen or fish.vectorizer.doc_count == 0:
        return []

    tokens = fish.vectorizer.tokenize(text)
    max_docs = fish.vectorizer.doc_count * 0.5

    scored = {}
    for t in set(tokens):
        df = fish.vectorizer.token_doc_counts.get(t, 0)
        if df > max_docs or len(t) < 3:
            continue
        idf = math.log2(fish.vectorizer.doc_count / df) if df > 0 else 0
        mi_total = sum(abs(fish.vectorizer.mi(t, v))
                      for v in fish.vocab[:20])
        scored[t] = idf * mi_total

    return [k for k, _ in sorted(scored.items(), key=lambda x: -x[1])[:top_n]]


def ingest_v3(text: str, source: str = "mind_daemon"):
    """Full v3 ingest — crystallize + persist + queue for re-eat."""
    fish = get_fish()
    return fish.ingest(text, source)
