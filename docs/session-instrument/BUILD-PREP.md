# Build-Prep — Session Instrument + Chaincodes + Meditate

**Research front-loaded 2026-06-20 so the next session is pure build.** Read this
first; it maps every existing primitive (reuse) and every gap (build-new), with
file:line, for all three tracks. Specs: `open-close-delta.md`, `meditate.md`,
`README.md`. This doc is the *how*.

---

## TRACK A — Chaincodes + Episodic Recall (the foundation; build FIRST)

### What's already built (don't reinvent)
`build/chaincode-fish-marriage-2026-04-26` (5 phases, ~1461 insertions, **673-line
test suite** `tests/test_chaincode_marriage.py`) already implements on Crystal:
- `chain_id` (chaincode hash — per-crystal identity), `chain_seq`
- `chain_created_at` (+ time-decay)
- `chain_prev_hash` (parent-child linkage)
- `/eat` accepts form + JSON
- A/B harness **proves** Phase 2 temporal rescue is *additive* (only adds edges,
  never removes) + a staleness filter blocks sensor mega-coupling.

`build/episodic-recall-unified-2026-06-10` = the 5 chaincode commits **+** Cal's
**`exp/episodic-recall/SPEC_v0.2_cal_2026-06-10.md`** (376 lines) + README. **Build
from THIS branch** — it's the superset.

### Cal's SPEC_v0.2 — the canonical target (summary)
- **Dependency gate:** chaincode-fish-marriage `chain_*` fields must be on the live
  Crystal first; everything else builds on them.
- Adds **`episode_id` / `episode_seq`** (session-scoped grouping — *distinct* from the
  per-crystal `chain_id` hash; both default None, backward-compatible).
- **`EpisodicMoment`** (renamed from `Moment` to avoid colliding with
  `linafish/moment.py`) — "what was happening when that was thought."
- **`ChainSource`** — `*_sources.jsonl` source-text preservation (recall returns
  enough text to be specific without bloating the crystal store).
- **Episode index file + `load_episode()`** — file-based (linafish "local files over
  databases"; the `:8109` chaincode service is **abandoned** by the spec — 172K
  entries are NOT migration targets).
- **Walking algorithm** — bounded radius + time-horizon around semantic pivots,
  orphan handling.
- **API:** `POST /recall_episodic` (semantic query → walk episodes → ranked moments);
  `GET /moment/{episode_id}` = **HIGHEST PRIVACY SURFACE, default OFF** (opt-in via
  `episodic.expose_full_sources = true`).
- Parent issue `sdill1973a/arena-engine#21`; reviewers `@anchor-dill` (primary),
  `@olorina-dill`.

### The rebase (build move #1) — and the eat-latency fix rides with it
The branch is **61 behind master, 3 conflict files: `linafish/crystallizer_v3.py`,
`linafish/engine.py`, `linafish/http_server.py`.** These are the SAME three files the
**eat-latency root-fix** touches (see runtime repo `data/runbooks/
fish_engine_eat_latency_root_fix_2026-06-20.md`: `eat()`→`_save_state()` re-serializes
the whole corpus every eat). **Do both in one integration pass** — rebase the chaincode
work onto current master and apply the per-eat-save decoupling at the same time, since
they edit the same `eat`/`_save_state`/`/eat` code. Run the 673-line marriage test suite
to verify the rebase preserved chaincode behavior.

---

## TRACK B — Open/Close Delta Instrument (spec: open-close-delta.md)

### REUSE — primitives that already exist (file:line)
- **`gamma(a, b)`** — `crystallizer_v3.py:698` — Jaccard-style vector coupling [0,1].
  *The* primitive for the **user↔assistant position delta**: compare their cognitive
  vectors. (1 = aligned, 0 = orthogonal.)
- **`chain_similarity(chains_a, chains_b)`** — `parser.py:736` — thinking-pattern
  distance [0,1] (Jaccard on dimension-chain sets). Alt user↔assistant metric (how
  differently they *reason*).
- **`compute_nmi(partition_a, partition_b)`** — `fusion.py:60` — distance between two
  mental models (how each partitions the same content). For deeper divergence.
- **`compute_emergence(crystals, evolved_ops, previous_ops)`** — `emergence.py` —
  `novelty_degree` (ν) + `self_ref_density` (ρ). Candidate signal for **"independent
  grounding"** (is the position novel/self-authored vs parroted).
- **`warmth_score`** — `assessment.py:266` — relational(IC+CR)/technical(KO+TE+SF+DE).
  A warm-vs-cold lens per side.
- **R(n) / `FishSnapshot.capture`** — `metrics.py:82`; **`DeltaReport.compare`** →
  `r_n_delta` `metrics.py:192`; **`compression_score`** — `formations.py:187`
  (substantiveness vs noise) — candidates for the **session↔reality** coherence side.
- **`absorb.py` source attribution** + the **just-merged `afferent.py`** (school router,
  curated/mined routing) — the seed for a grounding/source-attribution meter.

### BUILD-NEW (these do NOT exist — they're the real work)
1. **Cross-position comparator** — take two sources' aggregated cognitive vectors (or
   chains) → numeric divergence. Wrap `gamma()` / `chain_similarity()`; tag content by
   `source_mind` to separate user vs assistant. (Crystals already carry `source` /
   `source_mind`.)
2. **Session↔reality grounding meter** — ratio of source-attributed/externally-tethered
   content to conversation-internal content. Build on `absorb.py` + `afferent.py`.
   *This is the external-reality tether delta.*
3. **Warm-vs-cold differential** — explicit 2-pass: score the same content with
   shared-history context vs cold/bootstrap, return the divergence. (warmth_score +
   ache exist; the paired 2-pass does not.)
4. **Mirror-trajectory detector** — `d(user↔assistant delta)/d(turn)` AND
   independent-grounding contribution; fire the close when distance shrinks WHILE
   grounding drops. Needs per-turn delta history (a small rolling log).
5. **Locked boundary record schema** — immutable timestamp + the deltas at open/close
   (phase 1 of the spec; smallest first surface).

---

## TRACK C — `meditate` verb (spec: meditate.md)

### REUSE — orchestration entry points (file:line)
- **`FishEngine.recall(query, top)`** — `engine.py:2152` — BM25 hits as text.
- **`cmd_whisper`** — `__main__.py:824` — picks the 2nd/3rd strongest formation
  (surprising-not-obvious); reuse its selection logic.
- **`compute_emergence` / `emergence_gradient` / `collective_snt`** — `emergence.py` —
  ν/μ/ρ/Ψ + phase per formation; rank surfaced material by novelty.
- **`invoke_keeper(name, theme, top)`** — `keeper.py:195` → `{persona, recall, ...}` —
  scoped-fish framed surfacing.
- **`School.eat / refeed`** — `school.py:48-196` — fan across facets.
- **couplings** (`crystal.couplings: [(id, gamma)]`) + **`FeedbackLoop.usage`**
  (`feedback.py`: `{hits, helpful, last_used, weight_modifier}`) — co-access + "matters
  through use."
- **CLI dispatch** — `__main__.py:2402+` (add subparser) + commands dict (~:2860) +
  define `cmd_meditate`. Skeleton in `meditate.md` / Agent-2 report.

### BUILD-NEW (gaps)
1. **Dormancy classification** — "was active → went quiet → re-touching." Source signal:
   `feedback.usage[formation]["last_used"]`. No phase classifier exists.
2. **Per-crystal `last_accessed`** — feedback tracks *formations*, not crystals. Extend
   to crystal-id granularity (recall already iterates crystals).
3. **Formation co-occurrence edges** — no `formation_A ↔ formation_B` graph; build by
   traversing couplings grouped by `formation.member_ids`.
4. **Time-window filter** — build on `daily.py` date-indexed snapshots + `crystal.ts`.
5. **Model-scaling router** — `fast` = recall only; `balanced` = + emerge; `deep` = +
   co-access walk + cross-fish synthesis. linafish stays model-agnostic → the deep
   summarizer is a **pluggable hook the caller supplies** (the host wires its gateway).

---

## THE UNIFICATION (why these three are one build)
- **Chaincodes serve BOTH** episodic recall AND open/close-delta component 4 (the
  boundary sequence IS a chaincode — `chain_prev_hash` links open→close→open).
- **gamma / RCP / emergence** serve the deltas (Track B reuses Track A's vector math).
- **meditate** surfaces from the same substrate the deltas measure; dormancy (C) reuses
  the same temporal data episodic recall (A) needs.
One coherent instrument: the fish measures distance (RCP/gamma), chaincodes give it
episodic/temporal structure, the deltas read that distance at boundaries + live, and
meditate is the on-demand surfacing of it all.

## RECOMMENDED NEXT-SESSION SEQUENCE
1. **Integration pass on `crystallizer_v3.py` + `engine.py` + `http_server.py`:** rebase
   `episodic-recall-unified` onto master, resolving the 3 conflicts, AND apply the
   eat-latency per-eat-save decoupling in the same pass. Run the 673-line marriage suite.
   Land chain_* on master (Cal's dependency gate). *(Needs a Selene window on .67 for the
   live engine per linafish-refactor-selene-window — or build+test on .140 first.)*
2. **Episodic layer** per Cal SPEC_v0.2: `episode_id`/`episode_seq`, `EpisodicMoment`,
   `ChainSource`, episode index + `load_episode()`, `/recall_episodic`. Privacy-gate
   `/moment`.
3. **meditate** verb: wire the REUSE entry points behind the CLI subcommand; build the 5
   gaps (start dormancy + time-window, they're cheapest and highest-value).
4. **Open/close-delta:** locked boundary record (phase 1) → grounding meter + cross-
   position comparator → mirror-trajectory detector. Answer "what does the user need it
   to do?" before coding (it frames the schema).

**Gate reminder:** linafish is public + privacy-gated (`linafish-release-privacy-gate.md`).
Keep specs/code public-safe; the pre-commit hook scans added lines.
