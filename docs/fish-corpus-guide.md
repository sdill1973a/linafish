# Building Fish from Different Corpus Types

Five corpus shapes, five different lessons.

## Single-Voice Prose (one person's writing — journals, sessions, essays)

**Problem:** 88% of pairs couple above 0.50. One giant formation.
**Fix:** `FishEngine(subtract_centroid=True)` — removes the author's mean embedding.
**Result:** p75 drops from 0.84 to 0.49. 1 formation → 49.
**Gamma:** Use adaptive (default). The residuals have natural differentiation.

## Mixed Corpus (e.g., MSBA relationship fish — docs + conversation + donors)

**Problem:** Diverse sources, but session transcripts contain tool_result noise.
**Fix:** Do NOT use centroid subtraction — already diverse. Clean input instead.
**Key:** Extract paragraphs by keyword, skip `tool_use_id`/`tool_result` blocks.
**Lesson:** 51 clean crystals > 110 noisy ones. Quality > quantity.

## Code Corpus (e.g., dev fish — a codebase)

**Problem:** All code "sounds the same" to MI vectorizer. One blob.
**Fix:** `subtract_centroid=True` AND `min_gamma=0.30` (code is more homogeneous than prose).
**Key:** Include file paths in crystal text — gives structural context.
**Result:** 5 formations revealing architecture layers (backend, search, data, config, UI).

## JSON-Heavy Corpus (e.g., raw scars with metadata)

**Problem:** Structural keys (`type`, `timestamp`, `classification`) dominate MI vectors.
**Fix:** Extract text content before feeding. Strip metadata. Feed the human words, not the JSON structure.
**Key:** The boilerplate IS the noise. Same fix as tool_result pollution.

## Formation Count as Diagnostic

| Count | Meaning |
|-------|---------|
| 0 | Gamma too high, or too few crystals (<30), or centroid subtraction + adaptive = too conservative |
| 1 | Pathology — everything couples to everything. Need centroid subtraction or higher gamma. |
| 2-5 | Coarse differentiation. May need lower gamma or more crystals. |
| 5-50 | Healthy. Real patterns. |
| 50+ | May be over-splitting. Check if formations are meaningful or just noise. |

## The Fish-as-Dev-Tool Pattern

1. Feed the codebase to a fish (include file paths)
2. Read the formations — they show what couples (the architecture)
3. The heaviest formation is the center of gravity
4. The lightest formation is what needs building
5. Uncoupled observations are the raw material — individual files that don't fit a pattern yet
6. Build FROM the fish, not from a blank architecture doc
