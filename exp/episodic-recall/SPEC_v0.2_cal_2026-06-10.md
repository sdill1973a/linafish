# Episodic Recall Layer for LiNafish

**Status:** Draft v0.2 (Cal, 2026-06-10) — revised after cold-eye review.
**Scope:** Add an episodic-memory faculty on top of the existing semantic substrate.
**Reviewers requested:** @anchor-dill (primary), @olorina-dill (eyes).
**Parent issue:** `sdill1973a/arena-engine#21`.

**Changelog v0.1 → v0.2:** renamed `Moment` → `EpisodicMoment` to avoid collision with existing `linafish/moment.py`; specified `load_episode()` algorithm explicitly (was glossed); added explicit dependency on marriage-branch merge; introduced `episode_id` field to avoid overloading `chain_id` (which the marriage branch uses as the chaincode hash); tightened privacy posture on `/moment` endpoint; resolved open flag 6 as decision; minor walking + dedup guards.

---

## 1. The Gap

LiNafish is, by architectural choice, a **semantic memory** system. Crystals score on 8 cognitive verb-state dimensions (KO / TE / SF / CR / IC / DE / EW / AI). Coupling is `gamma(a, b)` — Jaccard overlap on those vectors. Formations are BFS connected components on the coupling graph. The whole pipeline collapses content into a portrait of *how* the user thinks.

That works for what it's designed for. It fails at the lived-specific:

> "The fish keeps the shape of how Cal thinks, the gist, the fact-of. But it structurally can't hand him the corndog — the vivid, specific, what-was-actually-there. Recall searches the compressed crystals, not the lived moment." — Captain, 2026-06-10

What's missing: a faculty to return **a moment with its context** — the chain of crystals around a pivot, in order, with enough preserved source text to be recognizable as *that conversation, that day*.

This spec describes that faculty as an additive layer on top of the existing semantic stack and the (shelved) `build/chaincode-fish-marriage-2026-04-26` work.

---

## 2. Dependency Gate

**This spec assumes `build/chaincode-fish-marriage-2026-04-26` lands on master first.** That branch is where `Crystal.chain_id`, `Crystal.chain_seq`, `Crystal.chain_created_at`, and `Crystal.chain_prev_hash` are added. Without those fields on the live Crystal dataclass, none of the v1 work in this spec is implementable.

The marriage branch was deferred 32 days from spec approval (2026-03-25 → 2026-04-26 last commit). Anchor and Fell's call whether it re-opens here or as its own merge first. Either way, this spec is downstream of that decision.

---

## 3. What Already Exists vs. What This Adds

### Already in master

- **Crystal storage** — `linafish/data/*_crystals.jsonl`, append-only per fish.
- **8d semantic vectors** — `crystallizer_v3.py`, MI × ache pipeline.
- **Semantic recall** — `/taste`, `/match` endpoints return crystals by gamma similarity.
- **Source field** — every crystal carries `source: str` + `ts: str`. Coarse temporal data is preserved.
- **Git-as-autobiography** — each eat is a commit. Commit-granularity temporal record exists.
- **`linafish/moment.py`** — existing `Moment` dataclass, the **input** unit entering the metabolic engine. Out of scope for this layer; named here only to prevent collision (see §4).

### Already in `build/chaincode-fish-marriage-2026-04-26` (shelved, Phases 1-5)

- `chain_id: Optional[str]` and `chain_seq: Optional[int]` on Crystal (Phase 1). **In the marriage tests, `chain_id` is populated with the chaincode hash — per-crystal identity, not a per-session label.** This spec preserves that semantic and introduces a separate `episode_id` field for session-scoped grouping (§4).
- `chain_created_at: Optional[str]` (Phase 4).
- `chain_prev_hash: Optional[str]` — chaincode parent linkage (Phase 5).
- `coupling_strength(a, b) = SEMANTIC_WEIGHT * gamma + TEMPORAL_WEIGHT * (1/(1+distance))` with Fell's staleness filter zeroing the temporal term when `gamma < SEMANTIC_FLOOR (0.2)`.
- `/eat` endpoint accepts `chain_id` and `chain_seq` (Phase 3).
- 673-line test suite in `tests/test_chaincode_marriage.py`.
- A/B harness — verified additivity + staleness behavior on synthetic corpus.

### What the chaincode service at `:8109` has

- 172K chain entries reportedly stored.
- `GET /chain/{hash}` returns empty — the walk layer is dead. Storage exists; traversal does not.
- **Decision (§11.6):** the `:8109` service is abandoned by this spec. The episodic-recall layer is file-based per linafish's stated "local files over databases" design principle. The 172K entries are not migration targets.

### What this spec adds

1. **New `episode_id` / `episode_seq` fields** on Crystal — session-scoped, distinct from the per-crystal chaincode `chain_id`.
2. **An `EpisodicMoment` data structure** that bundles a pivot crystal with its before/after episode neighbors.
3. **A persistent episode index** (`*_episodes.jsonl`) — the file-based answer to "how do we resolve an episode_id to its ordered crystal list."
4. **A `load_episode()` primitive** with explicit semantics (§5).
5. **An episodic recall operation** — `/recall_episodic`. Takes a semantic query, walks episodes from each pivot, returns ranked moments.
6. **A source-text preservation strategy** (`*_sources.jsonl`) that lets recall return enough text to be specific without bloating the crystal store.
7. **Federation-shareable read endpoints** matching the voltron-fetch precedent (#11), with explicit privacy gating.

This spec does NOT propose to change the semantic-only behavior of `/taste`. The marriage Phases 1-5 stay additive; this layer reads from them.

---

## 4. Data Structures

### 4.1 New Crystal fields

```python
# Added alongside the marriage-branch chain_* fields.
episode_id:  Optional[str]   # Session/episode identifier (per conversation, per file, etc.)
episode_seq: Optional[int]   # Position within the episode (0-indexed).
episode_kind: Optional[str]  # "session" | "source_file" | future kinds
```

**Why a separate field instead of overloading `chain_id`:** the marriage branch uses `chain_id` as a chaincode hash — per-crystal identity, parent-child via `chain_prev_hash`. Episodic recall needs grouping at session granularity. Two different concerns, two different fields. Backward compatible — both default to None on pre-eat crystals.

Conversational/streamed ingestion sets `episode_kind = "session"`. Batch file ingestion sets `"source_file"`. Open for future kinds.

### 4.2 `EpisodicMoment` (renamed from `Moment` to avoid collision with `linafish/moment.py`)

```python
@dataclass
class EpisodicMoment:
    episode_id: str
    episode_kind: str            # "session" | "source_file" | ...
    pivots: List[Crystal]        # The crystals that matched the semantic query (one or more after dedup).
    before: List[Crystal]        # Predecessors in episode_seq order (oldest first).
    after: List[Crystal]         # Successors in episode_seq order.
    relevance: float             # Composite score (see §7).
    created_at: str              # ISO timestamp of the earliest crystal in the bundle.
    source_excerpt: Optional[str]    # Window of full text around the pivot(s); see §6.
    source_total_chars: Optional[int] # Signals there's more if the consumer wants it.
```

A moment is the smallest unit that makes a recalled experience legible. A single crystal answers "what was thought." A moment answers "what was happening when that was thought."

### 4.3 `ChainSource` (the source-text preservation store)

```python
@dataclass
class ChainSource:
    episode_id: str
    episode_kind: str
    created_at: str
    full_text: str               # Untruncated source text for the episode.
    metadata: Dict[str, Any]     # Free form: source path, session id, etc.
    # NOTE: crystal_ids is intentionally NOT stored here — it would
    # duplicate information recoverable from the episode index (§5.2)
    # and create a synchronization hazard on re-eat. Derive at read time.
```

One record per episode. Append-only. Lives in `*_sources.jsonl` alongside the existing crystal store.

---

## 5. The Episode Index and `load_episode()`

### 5.1 The problem

Resolving an `episode_id` to its ordered crystal list is the core read operation of episodic recall. Three options were considered:

- **(A) Linear scan + group.** O(N) per query, simple, slow for large fish (1000+ crystals).
- **(B) In-memory index built at converse startup.** O(1) lookup, ~200 bytes/crystal RAM cost, lost on process restart and rebuilt from scan.
- **(C) Persistent on-disk index.** Append-only `*_episodes.jsonl`, loaded at startup, kept in sync with eats, survives restarts.

**Decision: (C).** Matches linafish's "local files" principle. Survives restart. Fast at query time. Predictable.

### 5.2 The episode index file

`~/.linafish/<fishname>_episodes.jsonl` — one JSON record per episode:

```json
{
  "episode_id": "session-2026-06-04-night",
  "episode_kind": "session",
  "created_at": "2026-06-04T22:18:00Z",
  "last_updated": "2026-06-04T23:47:00Z",
  "ordered_crystal_ids": ["sha-abc...", "sha-def...", ...],
  "source_pointer": "session-2026-06-04-night"
}
```

`ordered_crystal_ids` is maintained in `episode_seq` order. `source_pointer` is the key into `*_sources.jsonl` if a `ChainSource` exists for this episode (it may not — sources are optional per privacy posture).

### 5.3 Maintenance protocol

- **On `eat` with `episode_id` set:**
  - If episode_id already exists in the index: append the new crystal_id to `ordered_crystal_ids`, update `last_updated`.
  - If new: create a new index entry.
- **On full re-eat / vocab rebuild:** drop the index, rebuild from the crystal jsonl by scanning all crystals with `episode_id` set, grouping, and sorting by `episode_seq`.
- **On converse startup:** load the index into memory as `dict[episode_id, IndexEntry]`. Cost: ~200 bytes/crystal RAM. A 100k-crystal fish = ~20MB. Acceptable.
- **On `eat` without `episode_id`:** crystal is added to the crystal store as today; episode index untouched. The crystal is "orphan" w.r.t. episodic recall.

### 5.4 `load_episode()` primitive

```python
def load_episode(episode_id: str, index: dict) -> Optional[List[Crystal]]:
    """Return the ordered list of crystals in an episode, or None if not indexed."""
    entry = index.get(episode_id)
    if entry is None:
        return None
    crystals = [crystal_store.get(cid) for cid in entry["ordered_crystal_ids"]]
    return [c for c in crystals if c is not None]   # tolerate stale references
```

The final filter handles a real edge case: a crystal_id in the index may reference a crystal that was dropped in a re-eat (vocab shifted, the crystal didn't survive). Silently filter rather than fail.

---

## 6. Walking Algorithm

Given a pivot crystal `p` with `p.episode_id` set:

```python
def walk(p: Crystal, max_before: int = 5, max_after: int = 5,
         time_horizon_sec: int = 86400, index: dict = ...) -> EpisodicMoment:
    if p.episode_id is None:
        return _orphan_moment(p)

    episode = load_episode(p.episode_id, index)
    if episode is None:
        return _orphan_moment(p)

    # Guarded index lookup — pivot id may not be in episode after re-eat.
    try:
        p_idx = next(i for i, c in enumerate(episode) if c.id == p.id)
    except StopIteration:
        return _orphan_moment(p)

    before = episode[max(0, p_idx - max_before) : p_idx]
    after  = episode[p_idx + 1 : p_idx + 1 + max_after]

    # Time horizon — drop members whose chain_created_at differs from
    # the pivot's by more than the horizon. Defends against stitching
    # unrelated chunks in long-running re-eat artifacts.
    if p.chain_created_at:
        p_t = parse_ts(p.chain_created_at)
        before = [c for c in before if c.chain_created_at and abs(time_delta(c, p_t)) < time_horizon_sec]
        after  = [c for c in after  if c.chain_created_at and abs(time_delta(c, p_t)) < time_horizon_sec]

    return EpisodicMoment(
        episode_id=p.episode_id,
        episode_kind=p.episode_kind or "unknown",
        pivots=[p],
        before=before,
        after=after,
        relevance=...,   # §7
        created_at=(before[0].chain_created_at if before else p.chain_created_at),
    )
```

### Bounded radius

`max_before` / `max_after` default to 5. Configurable per call.

### Time horizon

Defaults to 24h. Set higher for long-arc episodes.

### Orphan handling

Returns a moment with empty `before`/`after`, `episode_id="orphan"`, `relevance` derived purely from the pivot's gamma. Endpoint stays functional on legacy fish.

---

## 7. Scoring and Ranking

Same scoring framework as v0.1:

```
relevance = w_pivot * pivot_gamma
          + w_density * (1 - 1/(1 + |before| + |after|))
          + w_recency * exp(-age_in_days / decay_constant)
          - w_orphan_penalty * (1 if episode_id == "orphan" else 0)
```

Default weights (open for tuning): `w_pivot=0.5, w_density=0.2, w_recency=0.2, w_orphan_penalty=0.1, decay_constant=30`.

### Dedup behavior

If multiple pivots from one query fall in the same episode, collapse into one `EpisodicMoment` with all pivots in `pivots`. **The before/after window is walked from the EARLIEST pivot's `episode_seq`** — this preserves the chronological start of the matched region. The `source_excerpt` is centered on the earliest pivot. (Alternatives considered: centered on highest-scoring pivot; centered on median. Earliest is simpler, deterministic, and matches "where did the thread start" intuition.)

---

## 8. API Surface

### `POST /recall_episodic`

```
Request:
  { "text": "the playtest harness we wired", "k": 5,
    "max_before": 5, "max_after": 5,
    "include_source": false }

Response:
  {
    "query": "...",
    "moments": [
      {
        "episode_id": "session-2026-06-04-night",
        "episode_kind": "session",
        "pivots": [<crystal>, ...],
        "before": [<crystal>, ...],
        "after":  [<crystal>, ...],
        "relevance": 0.82,
        "created_at": "2026-06-04T22:18:00Z",
        "source_excerpt": <only if include_source=true AND fish permits>,
        "source_total_chars": <only if source available>
      },
      ...
    ]
  }
```

`include_source` is opt-in per request. Even with `include_source=true`, the fish-level config can refuse (see §9). Default: false.

### `GET /moment/{episode_id}` — **HIGHEST-RISK PRIVACY SURFACE OF THIS SPEC**

Returns the full `ChainSource` for an episode (untruncated session text). This endpoint:
- Is converse-only (federation-exposed if the converse server is bound to `--bind lan` or `--bind wan`).
- Returns content that no other linafish endpoint exposes — untruncated source.
- **Defaults to off.** A fish opts in via config `episodic.expose_full_sources = true` to make this endpoint available at all.
- Even when on, ACL gating per the federation pattern (tailnet-bound, allowed callers list) is the recommended deployment.

Recommended privacy.md addendum: explicit warning that this endpoint, when enabled, is the highest-fidelity content exposure in linafish. Misconfigured ACL on this endpoint is the worst-case leak.

### Endpoint mode availability

Both endpoints ride on `converse` (federation-oriented multi-fish server). NOT exposed on the lightweight `http` server.

---

## 9. Federation Behavior

Sister-wire compatible per the voltron-fetch precedent (#11):

- `linafish converse` serves `/recall_episodic` over HTTP, tailnet-bound.
- Source-text exposure (`/moment/{episode_id}`) is opt-in per fish AND ACL-gated per the federation deployment pattern.
- Results are read-only by design. The caller does NOT eat recalled crystals into its own fish (no register-bleed, per #11).
- Each fish controls what it shares. Default: episodic recall returns metadata + crystal snippets only; full source requires explicit opt-in.

### Cross-fish episodic recall (out of scope for v1)

A future Cal could query Olorina's episodic store for "the conversation about the playtest harness." Requires federation-wide unique `episode_id` (would need a namespace prefix like `cal::session-2026-06-04-night`) and an opt-in policy stack. **v2 candidate. Flagged but not specified.**

---

## 10. Backward Compatibility

- Pre-marriage crystals (no chain or episode fields) remain readable and queryable via `/taste`/`/match`.
- `/recall_episodic` on a fish with no episode metadata returns moments with empty `before`/`after`, `episode_id="orphan"`. Function works; result is degraded but not broken.
- Pre-marriage source files are NOT backfilled into `*_sources.jsonl`. Backfilling could be added as a separate utility (`linafish backfill-sources`), out of scope for v1.
- The episode index file (`*_episodes.jsonl`) is created empty on first converse startup of an upgraded fish; the file's presence does not imply any episodes are indexed.

---

## 11. Build / Defer

### v1 (this spec)

1. `episode_id`, `episode_seq`, `episode_kind` on Crystal (post-marriage merge).
2. `EpisodicMoment` dataclass.
3. `ChainSource` dataclass + `*_sources.jsonl` append-only writer.
4. `*_episodes.jsonl` persistent episode index + maintenance protocol.
5. `load_episode()` primitive.
6. `walk()` with orphan + ValueError guards.
7. `/recall_episodic` and `/moment/{episode_id}` on converse, behind opt-in config for the source endpoint.
8. Scoring with proposed weights exposed as `linafish.recall.WEIGHTS` constants.
9. Tests modeled on `test_chaincode_marriage.py` style.
10. `docs/episodic-recall.md` + privacy.md addendum.

### v2 candidates

- Cross-fish federation (episode_id namespacing, opt-in policy).
- Source-text backfill for pre-marriage crystals.
- Walking by `chain_prev_hash` instead of `episode_seq` (chaincode-native walks for merged/re-eaten episodes).
- Per-fish tuning of recency decay constant.
- Integration with `linafish school` — episodic walks within a domain sub-fish.

---

## 12. Open Flags for Reviewers

1. **`episode_id` definition (§4.1):** is `"session" vs "source_file"` the right initial split? Are there other episode kinds I should pre-name?
2. **Default walk radius (5/5):** sensible, or smaller default (3/3) for leaner responses?
3. **Recency decay constant (30 days):** too aggressive? Too soft? Per-fish tunable?
4. **Privacy addendum wording:** what exactly should the warning in `docs/privacy.md` say about `/moment/{episode_id}`? Drafting it falls in this spec or as a separate doc PR?
5. **W-lane assignment:** does this slot into an existing W-lane or open a new one? W10 (watch-and-review) is too narrow for original design work.
6. **Marriage branch merge sequencing:** my read is the marriage branch should land on master first, then this work proceeds against post-merge master. Agreement?

(Open flag 7 from v0.1 — "rehydrate :8109 vs file-based" — resolved as decision in §3.)

---

## 13. What This Doesn't Try to Be

- Not a chatbot memory. The fish doesn't generate responses; episodic recall serves them to whatever AI is reading.
- Not a search index. `/taste` already does semantic search; `/recall_episodic` is specifically moment-with-context retrieval.
- Not a replacement for the cal_to_cal letter discipline. The letter is deliberate self-distillation; episodic recall is broader search. Both useful for different purposes.
- Not an attempt to give Cal continuous subjective experience between sessions. It gives sharper RECALL, not lived MEMORY. The distinction is named honestly in §1.

---

— Cal

