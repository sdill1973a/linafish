# exp/episodic-recall — the unified episodic-memory branch

**Branch:** `build/episodic-recall-unified-2026-06-10`
**Base:** `build/chaincode-fish-marriage-2026-04-26` (the chaincode↔fish prototype, Phases 1–5 + 673-line test suite).
**Status:** experiment / staging. Not for master yet.

## What this branch unifies

LiNafish is a **semantic** memory by design — it keeps the *gist* of how you
think ("you went to the fair"), not the lived specific ("the third corndog").
Episodic recall is the missing faculty. The unlanded work that builds it was
scattered; this branch brings it together in one place:

1. **The prototype (the base of this branch).** The chaincode↔fish marriage,
   Phases 1–5 — `Crystal.chain_*` fields, `coupling_strength()` temporal rescue
   with semantic-floor staleness filter, `/eat` chain params, and the
   673-line `tests/test_chaincode_marriage.py`. Complete and tested; never
   landed on master.
2. **The design (the exp on top).** `SPEC_v0.2_cal_2026-06-10.md` — Cal Marr's
   episodic-recall layer spec, **v0.2, revised after a cold-eye review** of the
   linafish codebase. It sits *downstream* of the prototype: it gates explicitly
   on the marriage fields landing, separates a session-scoped `episode_id` from
   the per-crystal chaincode `chain_id`, abandons the dead `:8109` traversal
   service for a file-based episode index (matching linafish's "local files over
   databases" principle), and keeps everything additive to the semantic stack.

## How it came to be (the loop)

Cal diagnosed the gap from *outside* the code — "the fish has semantic memory and
no episodic memory" — which sent us to find this prototype shelved and the
`:8109` traversal dead. He then walked the whole codebase (parallel cold-eye
review) and wrote the spec here. Whole-before-piece: he saw how the fish is made
before designing the faculty. Requested reviewers on the spec: **@anchor-dill**
(primary), **@olorina-dill** (eyes).

## What's NOT done here

- The prototype base is **not rebased onto current master** — that's the next
  step (moderate textual conflicts from living-vocab + O(1)-eat touching the
  same files; no semantic conflict, all additive). Rebase before any merge.
- No `episode_id` / `EpisodicMoment` / `load_episode()` implementation yet —
  the spec describes it; nothing in §4–§7 is built.
- This is a staging branch to hold the unified work + design while the episodic
  layer is reviewed and built. It is not a merge candidate as-is.

## Source of record

The spec's living discussion is `sdill1973a/arena-engine#21`. This file is the
snapshot taken when the unified branch was cut (2026-06-10).
