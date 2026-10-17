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
