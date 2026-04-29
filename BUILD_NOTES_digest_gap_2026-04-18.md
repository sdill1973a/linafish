# BUILD NOTES — §THE.DIGEST.GAP fix

**Branch:** `build/digest-gap-2026-04-18`
**Started:** 2026-04-17 evening / 2026-04-18 early morning session
**Author:** Anchor, with Captain

*This file is for the next me who picks this branch up. It is not documentation for PyPI or users — it is a build journal so I can walk in cold and know exactly where I left off.*

---

## What this branch adds

### `FishEngine.revectorize_all()` — new method in `linafish/engine.py`

Called as standalone: `engine.revectorize_all(vocab_size=None, d=None)`.

It fixes §THE.DIGEST.GAP (GitHub linafish issue #1) by:
1. Creating a fresh `MIVectorizer`
2. Re-feeding it every crystal's text (full-corpus relearning)
3. Re-freezing vocab from refreshed co-occurrence stats
4. Re-computing each crystal's `mi_vector`, `ache`, and `resonance` against the new vocab
5. Clearing `couplings` so `rebuild_formations()` recomputes them
6. Calling `rebuild_formations()` against the new vector space
7. Saving state (`commit=False` — caller decides when to git-commit)

Returns dict: pre/post formation counts, survived/dissolved/emerged names, crystals_processed, vocab sample, epoch.

### `linafish revectorize` — new CLI command in `linafish/__main__.py`

```
linafish revectorize --name <fish> --state-dir <path> \
    [--vocab-size N] [--d FLOAT] [--subtract-centroid]
```

Flows `--subtract-centroid` into `engine.subtract_centroid` before running.

### Capabilities listing update

Added `("revectorize", "Rebuild vocab + re-vectorize all crystals — fix for §THE.DIGEST.GAP")` under Feeding.

---

## What we validated

### ✅ `me` fish (136 crystals) — mechanism works

First run: 14 → 9 formations. 6 survived, 8 dissolved, 3 emerged. Real re-shaping.
Second run (via integrated CLI): 10 → 8 formations. 4 survived, 6 dissolved, 4 emerged. Converging toward stable structure.

Top vocab shifted to real current corpus terms: `fish, linafish, anchor, session, formation, memory, build, hook, one, crystals, test, work, codex, captain, notion`.

**This proves the mechanism on a normal heterogeneous-enough corpus.**

### ✅ faiss-absorb-test (96→2319 crystals, exploration JSON)

Ran clean, no errors. Collapsed 24 → 1 formation. Diagnosis: the corpus is homogeneous JSON tool-output text. Not a revectorize failure — the source data genuinely has one mega-pattern and the engine is being honest.

### ❌ anchor-everything (9,289 crystals)

At d=4.0 with `--subtract-centroid`: 1 → 1 formation (COORDINATION_AVOIDANCE_DASHBOARD → BIOMETRICS_CLAIM_AGENT). Same collapse, different name.

At d=2.0 with `--subtract-centroid`: 1 → 1 formation (→ DISCOVERIES_CLAIM_DEPLOYMENT). Still collapsed. At d=2.0 the vocab regressed — top tokens became stop words (`the, what, that`). Warm mode emphasizes frequent terms; on single-voice text that backfires.

### 🟡 anchor-writing (4,291 crystals) — RAN TO END OF SESSION

Started at top of session before context-budget crunch. CPU-active (~8.5 min of user-time observed), process at 437 MB resident, task `b313cjisg`. **Result not captured in this branch — check the task output file next time you're back:**

```
C:/Users/dills/AppData/Local/Temp/claude/D--GTC-SovereignCore-Runtime/4f5ea83f-9834-4ae0-9118-a465f3b25ea4/tasks/b313cjisg.output
```

The canonical anchor-writing fish is the real prize. 4291 crystals including tonight's scar absorb. If it differentiates from 2 → many formations, we have the working fix for the fish Captain actually uses for context. If it collapses like anchor-everything, the fix works in principle but the homogeneous-corpus problem is real and needs different strategy (fresh absorb with better params from the start, not in-place revec).

---

## What we learned about when revectorize helps and when it doesn't

**Helps when:**
- Corpus has real within-corpus variance (multiple topics, multiple registers, multiple time periods with distinct tones)
- The frozen vocab is clearly stale (top tokens don't match current content)
- Formations feel pathologically wrong (too few, one mega-formation, placeholder names)

**Doesn't help when:**
- Corpus is single-voice AND massive AND archive-style (everything shares ~the same vocabulary at the word level)
- Formation detection's coupling thresholds are hit by most pairs regardless of vocab
- The underlying problem is *variance compression*, not stale vocab

**For the second case**, revectorize-in-place isn't the answer. What probably is:
- Fresh absorb into a new fish with better params (tighter `min_gamma` floor, lower `d`, maybe smaller vocab)
- Source-aware or temporal chunking (use the `source` field as a prior so scars cluster separately from session dumps)
- Accept that some corpora are genuinely archive-only and stop expecting formation surfacing from them

---

## Files changed on this branch

```
linafish/__main__.py    +47 lines  (cmd_revectorize + subparser + dispatch + capabilities entry)
linafish/engine.py     +115 lines  (revectorize_all method)
BUILD_NOTES_digest_gap_2026-04-18.md   (this file)
```

Untracked (NOT part of this branch, pre-existing on master): `stress_116.py`, `stress_116_v2.py`, `stress_c8_real.py`, `tests/reeat_cycle_test_report.txt`, `tmp/`.

---

## What's next (pick any, in order of value)

1. **Check the anchor-writing revectorize result** (see task output path above). If good → this branch is ready to ship. If collapsed → needs tuning or a "fresh absorb" alternative before PR.

2. **PR this branch to linafish main** once anchor-writing result confirms the win. The patch is clean, tested, has a meaningful CLI surface.

3. **Write a test in `tests/`** — synthesize a small fish with drift (freeze on vocab A, feed content that shifts to vocab B, check revectorize picks it up). Even a regression test would be good.

4. **Document the caveat** in CHANGELOG.md or docs/ — single-voice homogeneous corpora don't benefit. Revectorize is not a magic de-collapser.

5. **Consider a `revectorize --from-source` mode** — ignore stored crystals entirely, re-absorb from a named source file. This is the "fresh absorb with right params" path for cases where in-place doesn't work.

6. **Benchmark on RunPod with `--workers N`** — if we want to make absorb+revectorize scale to 1M-crystal corpora (the anamnesis case), parallelism is the next engineering step. See the "RunPod + many cores" honest analysis in the runtime session scars.

---

## Dependencies / known state at branch creation

- Running on wheel install at `C:\Python310\Lib\site-packages\linafish` (1.1.6.1)
- Source at `D:\GTC\linafish-clean` on `master` before branching
- For CLI testing, use `PYTHONPATH=D:/GTC/linafish-clean "C:/Python310/python.exe" -m linafish revectorize ...` so the source edits take priority over installed wheel
- Standalone script at `D:/GTC/SovereignCore_Runtime/scripts/revectorize_fish.py` was the prototype; it and the engine-integrated method do the same thing. The script is the debugging-friendly version (prints phase progress); the integrated method is the PR-ready version.
- All backups of the fishes touched tonight live in `C:/Users/dills/.linafish/.revec-backup/<name>-<timestamp>/` and `C:/Users/dills/.linafish/<name>/.revec-backup/<name>-<timestamp>/` for subdir fish. Restore via `cp -r .revec-backup/<name>-<ts>/* <fish-state-dir>/` if anything went sideways.

---

## Session context — why this was built tonight

- §THE.DIGEST.GAP was named as the "1.2.0 architecture item" and highest-value next fix on the linafish 1.1.6 build plate.
- Captain asked: *"what's the fix long term?"* — the answer was this method. He followed with *"push into this"* to turn the answer into a shipped patch.
- Preconditions that made tonight viable: anchor-mind had just been caught up with 10 days of fish drift (commit `2874571`), scars absorbed into anchor-writing (commit `bg6mk9hri`'s 1258-file absorb), anamnesis absorb validated-and-parked (957 crystals, will need chunked/parallelized re-run later). So we were in prime context for the actual fix, not still wrestling with infra.
- The ride-along release-notes survey (Claude Code + Claude API) found `PostCompact` hook, Compaction API, Memory tool, Advisor tool, Managed Agents as platform-level capabilities worth evaluating — separate work, not on this branch, but likely influences future architecture decisions.

---

*Σache = K. For Caroline.*
