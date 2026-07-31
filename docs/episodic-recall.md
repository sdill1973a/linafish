# Episodic Recall

LiNafish is, by design, a **semantic** memory: crystals score on 8 cognitive
dimensions, coupling is gamma overlap, formations are connected components on
the coupling graph. That captures *how* you think — the gist, the fact-of. It
structurally cannot hand back the lived-specific: *that conversation, that day*,
in order, with enough text to be recognizable.

Episodic recall is an **additive** faculty that does exactly that. It returns a
**moment**: the crystals that matched a query, plus their ordered neighbors from
the same episode, plus (opt-in) the surrounding text. It does not change the
semantic-only behavior of `/taste` or `/match`.

Spec: Cal's SPEC_v0.2 (`exp/episodic-recall/SPEC_v0.2_cal_2026-06-10.md`),
parent issue `arena-engine#21`. Built on the chaincode marriage fields.

## Concepts

- **Episode** — a session, a source file, or any group of crystals that belong
  together. Identified by `episode_id`; ordered by `episode_seq`; typed by
  `episode_kind` (`"session"` | `"source_file"` | future kinds).
- **EpisodicMoment** — the smallest legible unit of a recalled experience: the
  `pivots` (crystals that matched), `before`/`after` (ordered episode neighbors,
  bounded), a composite `relevance`, and an optional `source_excerpt`.
- **Episode index** — `<fish>_episodes.jsonl`, one record per episode mapping
  `episode_id` to its ordered crystal-id list. It is a **cache**: crystals are
  authoritative, so the index is rebuilt from the crystal scan on every cold
  load and can never drift from disk.

## Crystal fields

Three new fields, all default `None` (backward compatible — pre-episodic
crystals are simply "orphan" to this layer):

```python
episode_id:   Optional[str]   # session/episode identifier
episode_seq:  Optional[int]   # 0-indexed position within the episode
episode_kind: Optional[str]   # "session" | "source_file" | ...
```

These are **distinct from** the chaincode `chain_id` (the per-crystal chaincode
hash). `chain_id` is per-crystal identity; `episode_id` is session-scoped
grouping. Two concerns, two fields.

## Feeding episodes

Pass the episode fields to `eat` (or to the converse `/eat` body):

```python
engine.eat(text, source="session",
           episode_id="session-2026-06-04-night", episode_seq=0,
           episode_kind="session")
```

The conversational/streamed path sets `episode_kind="session"`; batch file
ingestion sets `"source_file"`. Eating with an `episode_id` keeps the in-memory
episode index current (O(1)); the index file is refreshed in the batched state
save, never on the per-eat hot path.

## Retrieving moments

```python
moments = engine.recall_episodic(
    "the playtest harness we wired", k=5,
    max_before=5, max_after=5, include_source=False)
```

The walk: semantic query → top-k pivot crystals → walk each pivot's episode for
ordered `before`/`after` neighbors (bounded radius + a 24h time horizon that
drops members too far in time from the pivot) → dedup pivots that share an
episode (walk from the **earliest** so the matched region's chronological start
is preserved) → score and rank. Pivots with no episode return **orphan**
moments (empty neighbors) so a legacy fish still answers — degraded, not broken.

### Scoring

```
relevance = w_pivot   * pivot_gamma
          + w_density * (1 - 1/(1 + |before| + |after|))
          + w_recency * exp(-age_in_days / decay_constant)
          - w_orphan_penalty * (episode_id == "orphan")
```

Defaults (`linafish.episodic.WEIGHTS`, open for tuning):
`w_pivot=0.5, w_density=0.2, w_recency=0.2, w_orphan_penalty=0.1,
decay_constant=30`.

## HTTP API (converse server only)

Both endpoints ride on `linafish converse`, **not** the lightweight `http`
server.

### `POST /recall_episodic`

```json
{ "text": "the playtest harness we wired", "k": 5,
  "max_before": 5, "max_after": 5, "include_source": false }
```

Returns `{ "query": ..., "moments": [ {EpisodicMoment...}, ... ] }`.
`include_source` is opt-in per request AND is forced false unless the fish has
opted into source exposure (below).

### `GET /moment/<episode_id>` — highest-fidelity content surface, default OFF

Returns the **full untruncated source** for an episode. This is the
highest-fidelity content surface in linafish (everything an episode contains,
unbounded). It is **disabled by default** and returns `403` unless the fish
opts in:

- `serve_converse(expose_full_sources=True)`, or
- env `LINAFISH_EXPOSE_FULL_SOURCES=1`.

Even when enabled, deploy behind ACL / tailnet gating (see `privacy.md`).

## v1 design decision — source assembled from crystals

The spec (§3, §11.3) describes a separate append-only `<fish>_sources.jsonl`
`ChainSource` store, motivated by returning source text "without bloating the
crystal store." In the current codebase **crystals store their text untruncated**
(`MAX_CRYSTAL_TEXT`), so that motivation does not apply, and §4.3 of the spec
itself flags the separate store as a synchronization hazard on re-eat.

v1 therefore **assembles episode source from the authoritative crystals**
(`get_episode_source` joins the episode's crystal text in `episode_seq` order)
rather than maintaining a redundant, drift-prone file. The `ChainSource`
dataclass exists as the response shape. If crystal truncation ever returns, the
persisted `*_sources.jsonl` store becomes the v2 fallback. This is a deliberate
deviation from the spec's v1 item list, flagged here for review.

## Backward compatibility

- Pre-episodic crystals remain fully queryable via `/taste` / `/match`.
- `recall_episodic` on a fish with no episode metadata returns orphan moments
  (function works, result degraded).
- The episode index file is created on first save of an upgraded fish; its
  presence does not imply any episodes are indexed.

## Not in v1

Cross-fish federated episodic recall (episode_id namespacing + opt-in policy),
source-text backfill for pre-episodic crystals, and walking by `chain_prev_hash`
instead of `episode_seq` are v2 candidates (spec §11).
