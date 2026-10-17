# exp/persist-after-eat — formation and couplings are computed after the crystal is already on disk (seed)

*2026-10-17. Measured on two live fish; mechanism read from the code.*

## The finding

`crystallize_text()` appends the new crystal to the JSONL log (`_persist_crystal`) and returns.
Only then does `eat()` call `_file_into_formation()` (sets `crystal.formation`) and
`rebuild_formations()` → `_couple_appended_crystals()` (sets `crystal.couplings`). The log is
append-only and no code path rewrites a line, so **neither field ever reaches disk.**

Per-day on a 35K-crystal fish: every crystal through 2026-08-15 has a formation and couplings;
from 2026-08-16 onward **0 of ~13,900**. The earlier crystals look complete only because a
one-time revectorize (PR #57's atomic log rewrite) rewrote the log from memory on 08-15. On a
second fish the same stop appears in September. The served process's own `/crystals` shows
today's crystals with `formation: None, couplings: []` while `/health` reports 387 formations.

## Measured mechanism (scratch fish, 40 eats, fresh state dir, 2.3.1)

| | in memory after eat | on disk | reloaded |
|---|---|---|---|
| formation set | 40/40 | **0/40** | 40/40 (re-derived at load by `reindex_formations`, O(N)) |
| couplings set | **0/40** | 0/40 | 0/40 |

**CORRECTED the same hour.** The table above was taken on 40 near-identical texts, and the adaptive
coupling threshold (p75 of sampled gammas) ties out on identical vectors — a scratch artifact, not the
defect. Rerun with 60 varied real texts:

| | in memory after eat | on disk | reloaded | after one more eat |
|---|---|---|---|---|
| formation set | 60/60 | **0/60** | 60/60 (re-derived at load) | — |
| couplings set | **59/60** | **0/60** | 56/60 (recomputed for the whole tail at load) | 56/61 |

So it is ONE defect: both fields are computed after the crystal is appended and nothing ever writes
them. The served process has them in memory; every disk reader sees None/[]; and every cold load
recomputes couplings for the entire unpersisted tail (on a 35K fish that tail is ~13,900 crystals —
the measured 240 s first eat). The earlier "couplings are not produced at all" line is withdrawn.

## Consequences

- Every cold load re-couples the whole tail on the first eat (measured: ~76K `coupling_angle`
  calls, 240 s on mapped vectors) and never writes the result — paid again next load.
- Every reader of the log (compaction, the glyph↔chain join, any offline tool) sees a fish that
  stopped forming in August.
- An organ that cannot fail: `eat()` returns `formations: N` from memory, so nothing noticed.

## Proposed fix (root, not workaround)

Persist AFTER the crystal is complete: move `_persist_crystal` out of `crystallize_text` into
`eat()`/`eat_many()`/`eat_path()` after filing and coupling (one call site each), or have
`eat()` rewrite the just-appended line in place (seek to the recorded offset; same length is not
guaranteed, so the first form is simpler). Add a load-time check that counts tail crystals with
`formation is None` and reports it in `/health` and `doctor` — the direction this organ could
not fail in. Backfill: one `_rewrite_crystal_log()` after a full in-memory recouple, behind a
verb, never automatic.

## Built — same day

`UniversalFish.repersist_tail(k)` (crystallizer_v3): `_persist_crystal` now records each crystal's line offset;
after `eat()` has filed and coupled, the tail line is rewritten from memory — self-verifying (the lines from the
recorded offset must parse to exactly the tail's ids, else nothing is touched; tested with a foreign line appended).
Hooked in `eat()` (k=1), `eat_many()` (the batch, after the final rebuild) and `eat_path()` (the new crystals).
Tests: `tests/test_persist_after_eat.py` (formation on disk for every crystal; the crystal's own couplings on disk;
a cold load reads them back; the guard refuses when the tail moved).

Still true, stated: couplings a new crystal adds to OLDER crystals (beyond the tail) reach disk only on a full
rewrite — a `doctor`/backfill verb over `_rewrite_crystal_log()` after one in-memory recouple is the follow-up for
the ~13,900 already-unpersisted crystals on the live fish. Not automatic.
