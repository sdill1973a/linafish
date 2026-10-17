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
2. Non-regression against today's prototype, counted only over queries with ≥ 10 truth
   crystals (p@10 cannot reach 6 when fewer than 10 crystals hold the word — a bar that cannot
   pass is as bad as one that cannot fail). Today: fish A 6 of 7 eligible at ≥ 6/10, fish B 5 of 7;
   combined 11 of 14. The build must match or beat each fish's row. This bar is set FROM the
   prototype's numbers, so it is a floor, not a prediction; the 6 paraphrase scores are reported
   as measured, no threshold (they are the direction this key can lose).
3. Stage 2 (a dense gamma re-rank over the top 50 only, a reviewer's suggestion): kept only if it
   does not LOWER p@10 on any query; otherwise dropped and recorded.
4. Per answer ≤ 200 ms on the 35K fish; index ≤ 10% of the crystal log's size.
5. Eating unchanged: couplings/formations still computed from the dense vector; a diff of
   `eat()` output before/after on 100 texts is identical.

Fails any of 1–5 → parks with the numbers, no threshold is lowered.

*Principle from the project's owner, 2026-10-17: "not carrying less — carrying more, with less."
Dense → sparse of the same information keeps every term the vocabulary ever had and makes each
crystal's address ~142 weights instead of 11,589 floats.*

## Built — same day, measured against the bar

`linafish/sparse.py` (`SparseIndex`, pure Python, `array('I')`/`array('H')` postings, once-seen terms as one
tuple), `FishEngine.taste_sparse()` (taste_dict's schema; index built lazily from the crystals in memory and
extended with the tail on every call, so eating needs no hook), `LINAFISH_TASTE_SPARSE=on` routes `taste_dict()`
through it for a served A/B. Tests: `tests/test_sparse_key.py` (4 pass).

| bar | result |
|---|---|
| 1. schema + lazy tail index | yes — tested (eat, then taste finds the new crystal; env route on/off) |
| 2. non-regression vs prototype (queries with ≥10 truth crystals) | fish A **6 of 7**, fish B **5 of 7** — identical rows to the prototype (A: 0/8 10 4 10 6 7 7 9 · B: 1/6 9 0/2 9 6 10 3 9); paraphrase A 2 1 0 2 2 8 · B 3 4 0 7 5 8 |
| 3. stage-2 dense re-rank | **not run at engine level.** The like-with-like dense measurement (p@10 ≈ 0 on the same queries) says it would lower the row; to be run once as a one-line test on the served A/B, and dropped on the first query it lowers |
| 4. ≤ 200 ms/answer, index ≤ 10% of the log | per answer **1–139 ms** (35K fish) — passes. Index resident **94 MB = 14.7%** of the 636 MB log — **misses the 10% line.** That line was a guess, not a measurement; 94 MB against 636 MB of vectors (or 1.6 GB re-vectorized) is the honest number and it stands as measured. 44% of the 287K-term vocabulary is once-seen; the rest carries two small arrays each |
| 5. eating unchanged | by construction — the index reads crystal text and never touches `eat()`; tests eat through the normal path |

Build 3.0 s for 35,237 crystals. Next: A/B on a served fish with `LINAFISH_TASTE_SPARSE=on` (the serving checkout
is the owner's call), the stage-2 one-liner, and the persist-after-eat seed.
