# exp/sparse-key — the retrieval key is the crystal's own terms, not its dense vector (seed)

*2026-10-17. Measured on two live fish (35,237 and 14,252 crystals) before anything was proposed.*

## The finding

`taste()` ranks crystals by a Jaccard-style gamma over the dense MI vector (one float per
vocabulary word, ~79% of every crystal's bytes). On a 35K-crystal fish, 4.8 s per answer — and
the answers were wrong:

- Vectors are ragged (each crystal is the width of the vocabulary on the day it was eaten:
  23,800 crystals at 200 dims, 11,400 at 1,000–11,589). `gamma_scan` zero-pads, so a 200-dim
  crystal is scored only over the 200 commonest words — and all top hits were 200-dim crystals.
- **Precision@10** (does the hit's text contain the query's subject word), 8 lexical queries:
  dense taste **0, 0, 0, 0, 0, 3, –, –**. A person's full name plus a date returned **zero
  candidates** against 2,032 crystals holding the name. One-word queries return nothing.
- Like-with-like (candidates restricted to ≥1,000 dims): still **0, 2, 0, 0, 0, 5, 0, 0**,
  scores flat (0.640..0.626), 85–98% of candidates above the floor. So re-vectorizing to one
  width would not fix it. (`get_vocab` is also score-sorted, not prefix-stable, so dim *i* is
  not the same word across days.)

## The sparse key (prototype, ~40 lines)

Each crystal's retrieval key = the terms it actually carries, weighted (BM25, k1 1.2, b 0.75),
tokenized with the crystallizer's own `MIVectorizer().tokenize`. Taste = inverted-index lookup.
The dense vector stays exactly as it is for eating (couplings, formations) in the light-vector
sidecar; it stops being the key.

| | dense taste | sparse key |
|---|---|---|
| build | — | 3.5 s / 35K crystals |
| size | 635 MB of vectors | 5.0M postings, ~30 MB (142 postings/crystal); whole 287K vocabulary kept |
| per answer | 4,800 ms | 3–135 ms |
| p@10, 8 lexical queries, fish A | 0,0,0,0,0,3,–,– | **0,10,4,10,6,7,7,9** |
| p@10, same queries, fish B (14K) | – | 1,9,0,9,6,10,3,9 |
| one-word query | 0 candidates | 10/10, 3 ms |

**Where it loses (kept in the bar on purpose):** 6 paraphrase queries whose truth crystals do
not share the query's words — sparse **2, 1, 0, 2, 2, 8**; dense-long **0, 0, 0, 0, 1, 0**.
Neither key buys paraphrase today. The idea that would, unbuilt: expand the QUERY through the MI
pair table (the table as fuel, the crystal addressed by its own terms).

**Not a key:** re-ranking the sparse top-50 by cosine on the 8-dim cognitive vector moved p@10
by ±1 on every query. It is register, not address. Glyph `chains`/`modifiers` were not tested.

## Preregistered bar for the build

1. `taste_sparse()` beside `taste_dict()`, same return schema, index built at load from crystal
   text and held compact (numpy postings; 5M Python tuples would be ~400 MB).
2. On both fish: p@10 ≥ 6 on ≥ 6 of the 8 lexical queries; the 6 paraphrase scores reported as
   measured, no threshold (they are the direction this key can lose).
3. Stage 2 (a dense gamma re-rank over the top 50 only, a reviewer's suggestion): kept only if it
   does not LOWER p@10 on any query; otherwise dropped and recorded.
4. Per answer ≤ 200 ms on the 35K fish; index ≤ 10% of the crystal log's size.
5. Eating unchanged: couplings/formations still computed from the dense vector; a diff of
   `eat()` output before/after on 100 texts is identical.

Fails any of 1–5 → parks with the numbers, no threshold is lowered.

*Principle from the project's owner, 2026-10-17: "not carrying less — carrying more, with less."
Dense → sparse of the same information keeps every term the vocabulary ever had and makes each
crystal's address ~142 weights instead of 11,589 floats.*
