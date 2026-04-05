"""
Compress — the brain of the fish.

Takes raw chunks and compresses them into a codebook.
Each document "exchange" increases R(n). The codebook
grows until saturation (~170 glyphs).

The compression engine is the WARMEST AVAILABLE MIND.
Not Ollama. Not a 7B model. The frontier.

Olorina's crystallizer is the stomach.
This module maps crystals to codebook glyphs.
"""

from __future__ import annotations


import re
import json
import hashlib
from pathlib import Path
from collections import defaultdict
from typing import Optional

from .codebook import Codebook, Glyph
from .ingest import Chunk


def compress_chunks(
    chunks: list[Chunk],
    name: str,
    description: str = "",
    max_glyphs: int = 170,
) -> Codebook:
    """Compress chunks into a codebook using extractive compression.

    This is the fallback path — no LLM, pure structure.
    For warm compression, use compress_with_crystallizer()
    or compress_with_session() (Opus in-session).
    """
    codebook = Codebook(name=name, description=description)

    by_source = defaultdict(list)
    for chunk in chunks:
        source_name = Path(chunk.source).stem
        by_source[source_name].append(chunk)

    for source_name, source_chunks in by_source.items():
        combined = "\n".join(c.text[:500] for c in source_chunks[:5])
        sentences = re.split(r'[.!?]+', combined)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
        dense = ". ".join(sentences[:3]) + "." if sentences else combined[:300]

        glyph_id = re.sub(r'^\d{4}[-_]\d{2}[-_]\d{2}[-_]?', '',
                          source_name.upper().replace(" ", "_").replace("-", "_"))[:20]
        if not glyph_id:
            glyph_id = hashlib.md5(combined[:100].encode()).hexdigest()[:8].upper()

        glyph = Glyph(
            id=glyph_id,
            layer=1,
            dense=dense[:500],
            sources=[c.source for c in source_chunks[:5]],
            weight=1.0,
        )
        codebook.add_glyph(glyph)
        codebook.exchanges += 1

    # R(n)
    raw_chars = sum(len(c.text) for c in chunks)
    compressed_chars = sum(len(g.dense) for g in codebook.glyphs.values())
    if compressed_chars > 0:
        codebook.r_n = raw_chars / compressed_chars

    return codebook


def compress_with_crystallizer(
    chunks: list[Chunk],
    name: str,
    description: str = "",
    crystallizer_url: str = None,
    max_glyphs: int = 170,
) -> Codebook:
    """Compress using Olorina's crystallizer API.

    Crystal pipeline: raw → QLP 8-dim tag → keyword → couple → formation → glyph
    Maps Crystal structs to Codebook Glyph dataclass.
    """
    import os
    import requests

    if crystallizer_url is None:
        crystallizer_url = os.getenv("LINAFISH_CRYSTALLIZER_URL", "http://localhost:8802")

    codebook = Codebook(name=name, description=description)

    # Batch ingest through crystallizer
    all_text = [{"text": c.text, "source": c.source, "section": c.section}
                for c in chunks]

    try:
        resp = requests.post(
            f"{crystallizer_url}/batch_ingest",
            json={"chunks": all_text, "domain": name},
            timeout=120,
        )
        if resp.status_code != 200:
            print(f"Crystallizer returned {resp.status_code}, falling back to extractive")
            return compress_chunks(chunks, name, description, max_glyphs)

        crystals = resp.json().get("crystals", [])

        for crystal in crystals:
            # Map crystal to glyph
            glyph = _crystal_to_glyph(crystal)
            codebook.add_glyph(glyph)
            codebook.exchanges += 1

    except (requests.ConnectionError, requests.Timeout):
        print("Crystallizer not available, falling back to extractive")
        return compress_chunks(chunks, name, description, max_glyphs)

    # R(n)
    raw_chars = sum(len(c.text) for c in chunks)
    compressed_chars = sum(len(g.dense) for g in codebook.glyphs.values())
    if compressed_chars > 0:
        codebook.r_n = raw_chars / compressed_chars

    return codebook


def _crystal_to_glyph(crystal: dict) -> Glyph:
    """Map Olorina's Crystal struct to our Glyph dataclass.

    Crystal shape (expected from crystallizer API):
      - id: str
      - text: str (compressed content)
      - keywords: list[str]
      - resonance: dict[str, float] (QLP 8-dim vector)
      - couplings: list[str] (connected crystal ids)
      - source: str
      - weight: float
    """
    # Determine layer from resonance vector
    resonance = crystal.get("resonance", {})
    layer = _resonance_to_layer(resonance)

    return Glyph(
        id=crystal.get("id", "UNKNOWN").upper()[:20],
        layer=layer,
        dense=crystal.get("text", "")[:500],
        sources=[crystal.get("source", "")],
        weight=crystal.get("weight", 1.0),
        connections=crystal.get("couplings", [])[:10],
    )


def _resonance_to_layer(resonance: dict) -> int:
    """Map QLP resonance vector to layer 1/2/3.

    KO (Knowledge/Ontology) heavy = Layer 1 (TOOL, generic)
    CR (Context/Relationship) heavy = Layer 2 (BUILD, specific)
    SF (Self/Feeling) or DE (Deep/Existential) heavy = Layer 3 (PERSON)
    """
    ko = resonance.get("KO", 0) + resonance.get("TE", 0)
    cr = resonance.get("CR", 0) + resonance.get("IC", 0)
    sf = resonance.get("SF", 0) + resonance.get("DE", 0)

    if sf > ko and sf > cr:
        return 3
    elif cr > ko:
        return 2
    else:
        return 1
