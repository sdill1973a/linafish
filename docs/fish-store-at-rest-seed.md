# exp: a fish at rest — the store (seed doc)

*Seed, 2026-09-21. An idea with one measured spike behind it. Not a PR.*

## The idea

A person's memories are not all loaded; they are *available* — reached as needed. A served
fish today is the opposite: `converse` loads the whole engine and holds it. The store is the
format that lets a fish sit on disk at near-zero cost and still answer `taste` and `recall`
with the same ranking the engine gives.

## What was measured (one fish, one spike)

Fish: 8,616 crystals, vocab 3,964, d=200, frozen vocabulary.

| | engine (served) | store (door) |
|---|---|---|
| open | 24–29 s | 0.06 s |
| idle resident | 1,910 MB | 48 MB |
| taste | 1.21 s | 0.01 s |
| parity, 3 taste + 3 recall cues | — | top-1 same, top-10 identical, max score Δ 0.0000 |

**Where the weight is:** 1.42 GB of the 1.91 GB is one dict — the vectorizer's token-pair
co-occurrence counts (`pair_counts`, ~7.06 M pairs). Found by dropping structures one at a time.
Crystals (texts + vectors) are under 50 MB. So the store is not about the crystals; it is about
the vectorizer.

**The move:** for a *frozen* vocab, `mi(token, vocab_word)` is a fixed function. Compute it once
with the engine's own `mi()`, write it as a sparse matrix (CSR, row = token), and let the OS page
in only the rows a probe's tokens touch.

## Layout tried

```
meta.json         N, D, vocab, token ids, doc_count, totals, built_at, source
vectors.f32       N x D float32, memmap, row = crystal row
vector_len.*      per-row vector length (see "the miss" below)
mi_indptr.i64     CSR over tokens
mi_indices.i16    vocab id
mi_data.f32       mi(token, vocab_word)
crystals.sqlite   id, ts, source, text, keywords, meta — texts on demand
token_df.json     token -> doc frequency (+ doc_count), for ache relevance
baseline.json     the engine's own answers to the parity cues
```

Parity contract: the door's `taste` must reproduce the engine's ranking (same gamma, same vectors,
probe built from the same MI table); `recall` runs the engine's BM25 over texts streamed from
SQLite. Any divergence prints as a MISS. Miss condition named before the run: idle ≥ 50 MB, cold
recall > 5 s, or parity fails.

## The miss worth keeping

First build silently dropped 1,602 crystals. A long-lived fish carries **mixed vector widths**
(here 200 → 3,964, from vocabulary growth over its life); the builder assumed one width and
skipped the rest as "empty". The engine's gamma zips — it truncates to the shorter vector — so the
store needs a per-row length and must never assume uniform D. Caught only because the miss
condition was named first and a named crystal was absent.

## Open questions

- **A living fish.** All of this holds for a frozen vocab. A vocab that grows (`linafish live`,
  the emerging door) changes the MI table. Rebuild on election? Delta rows? This is the real
  design question and it is the same one as traditional-vs-emerging vocabulary.
- **One door, many fish.** If a fish at rest is ~50 MB, one process can serve a whole school
  instead of one process per fish.
- **Writes.** The spike is read-only. `/eat` against a store needs an append path for vectors +
  SQLite and a rule for when the MI table is stale.
- **A meter.** Loads per day × resident size is the cost this removes; nothing reports it yet.

## Not claimed

One fish, six cues, one machine. No write path. No living vocabulary. Parity beyond top-10 not
checked.
