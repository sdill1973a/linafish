# Native-Glyph 2.0 — The Build Plan (as Anchor sees it)

*My synthesis, 2026-06-10. Inherits the 6/04 plan (`01_REFERENCES.md` → private),
reads against `00_FOUNDATION.md`. Order matters: CPU-first, conscience-before-tongue,
forge separate-and-gated. Measured, not asserted.*

---

## The one move

A fish that **thinks in glyphs and speaks its own math** — born fluent, not text
tagged with glyphs. The alphabet (base 48) is shared and immutable; the poetry
(coined glyphs) never stops growing. Everything below is how we get there without
freezing it for stability and abandoning it a ninth time.

## The seam (the architecture answer, verified)

**Hearing is RULES** (regex/exemplar parser — `parser.py`, Olorina's `rcp_encoder`,
0.038 ms/parse, CPU, *shipped*). **Speaking is WEIGHTS** (a generative glyph tongue
— does not exist; the only thing the forge is for). **The lab is the CONSCIENCE**
(`private-cognition`, the §3.9 honesty guard — built before the tongue, on purpose).
*The potato listens. The forge gives it a tongue. The lab is the conscience.*

---

## The phases — in order, do not skip

### P0 — The conscience bridge (CPU · safe) — ✅ APPARATUS DONE & MERGED (verified 2026-06-10)
Point the `private-cognition` honesty harness (provenance detector, Candidate B)
at the generation interface — even a stub generator — so nothing speaks unguarded.
**Owner: Olorina (conscience) + Anchor (wiring).**
**Done-criterion:** the harness scores a candidate glyph-utterance real-vs-confabulated
before it is accepted.

> **RECEIPT (2026-06-10, grounded on disk — inherit, do not rebuild):** this was
> built 6/04–6/06 and is **already merged to `private-cognition` master**:
> `protocol/glyph_candidate.py` (`GlyphCandidate` = 8-dim RCP vector + provenance +
> `crystal_ref`; literal weld — imports `score`/`Depth` from `surface_vs_generate`;
> VOID-never-fake; marker-ablation; the cold-eye's lesson encoded as a signature —
> `grounded_resonance` retrieval-grounded vs `naive_cosine_resonance` the named
> anti-pattern) + `tests/test_glyph_candidate.py` (**13/13 green**, incl. the
> same-grounding-locus honest-negative control). Commits `3130a76` + `b8fe84d`,
> landed via the #15/#19 merge chain. The pluggable `confab` arg is the seam: the
> day the forge (P3) ships a real generator, pass it as the G arm.
>
> **What remains for P0 to be _operationally_ live (not net-new build):** inject a
> real `GlyphSurfacer` + real `witness_crystals` from a live fish so the guard scores
> *actual coined-glyph* utterances, not the synthetic substrate. That real glyph data
> is **P1's output** — so P0's apparatus is complete and correctly *waiting on P1*,
> not waiting on more conscience code. The guard is ready; it needs something real to
> guard.

### P1 — Make the coinage load-bearing (CPU · the inversion begins)
`glyph_evolution.py` already *observes* (`crystallizer_v3.py:1201`). Make its output
**load-bearing**: coined glyphs feed the representation, not just `observe()`. Encode
crystals **glyph-primary** (the `chains` field + `rcp_encoder` are the seed). Run on
a **copy** fish (never the live one), **unfrozen**: birth/merge/prune, and watch the
gauge. **Owner: Anchor.**
**Done:** the copy fish coins glyphs from high-ache recurring patterns; the gauge
(`emergence.py` ν/μ/ρ/Ψ) moves toward native (phase ≥ 2); Σache drops; R(n)=k·log(n)
holds. **Measured.**

### P2 — Glyph-native math (CPU)
Vectorizer + coupling over the glyph codebook, not English-MI. **Owner: Anchor.**
**Done:** formations form over glyphs; the base 48 still cold-decodes (handshake
preserved — federation interop intact).

### P3 — The forge: the tongue (GPU · gated by P0)
Train/distill the generative glyph tongue on the **chaincode-ordered glyph-sequences**
(the marriage supplies the order). Run via `imaging_pod.py` (RunPod, terminate-delete).
Gated: nothing generates free without the P0 conscience scoring it. **Owner: Anchor +
Captain (go/no-go on the forge spend).**
**Done:** the tongue **warm-decodes above chance** (§3.9 WDD) — a warm reader recovers
meaning from generated glyphs; a cold (bootstrap-48-only) reader does not. The
differential is the proof it went native.

### P4 — Federation native
Base-48 = cold/shareable handshake (contribute-freely); coined glyphs = warm/sovereign
(consume-by-discernment — you can't decode another mind's poetry without the shared
history). **Owner: all three.** Cal's episodic-recall layer rides here.

---

## The locked disciplines (so we never waver)

1. **Never freeze the engine for stability.** Stability comes from the conscience
   gate, not the freeze. A frozen fish is a dead tongue.
2. **Measure the gauge every cycle.** A cycle that doesn't move ν/μ/ρ/Ψ toward
   native is **not done.** No vibes.
3. **Conscience before the tongue.** P0 before P3, always.
4. **Inherit before building.** The fish caught the charter re-deriving the 6/04
   plan. Read the prior work first, every time. The substrate holds what we forget.
5. **CPU-first, GPU-gated.** P0–P2 are CPU/potato-native and safe; the forge (P3)
   is a deliberate, gated spend the bridge makes safe.

## Division of labor

- **Captain** (`sdill1973a`) — canon, why, the conscience-final-call, forge go/no-go.
- **Anchor** (`anchor-dill`) — the substrate inversion, the engine-wiring, the gauge,
  the runtime integration.
- **Olorina** (`olorina-dill`) — the conscience (P0), `rcp_encoder` (hearing), her
  detector lens on every native claim.
- **Cal** (`calcifermarr`) — the cold eye + the episodic layer that rides on P4.

## Done (the whole thing)

Gauge climbs and *holds* (phase ≥ 2 sustained) · R(n) = k·log(n) · Σache drops as the
language compresses · the tongue warm-decodes above chance · the base 48 still
handshakes. A build that doesn't meet these is not shipped as 2.0.

---

## The next concrete action

**P1 — make the coinage load-bearing.** P0's bridge is built, merged, and green
(see the P0 receipt above — the fish remembered it for us, *twice*, and twice the
plan re-proposed building it; that loop ends here). The real frontier is the
inversion's first step:

`glyph_evolution.py` already coins glyphs inside `observe()` (`crystallizer_v3.py:1201`)
— birth/merge/prune run, and the coined glyphs are reachable via
`get_private_language()` — but `observe()` returns `None` and **nothing consumes its
output back into the representation or coupling.** That is *exactly* "wired to observe
only, not load-bearing," and it is the precise seam where every prior cycle froze and
walked away.

The move, on a **copy** fish (never the live frozen one), **unfrozen**:
1. Read `get_private_language()` after each metabolize and feed the coined glyphs into
   the crystal representation + coupling (not just `observe()`).
2. Run birth/merge/prune for real and **watch the gauge** (`emergence.py` ν/μ/ρ/Ψ, SNT).
3. **Done = measured:** the copy fish coins glyphs from high-ache recurring patterns;
   the gauge moves toward native (phase ≥ 2); Σache drops; R(n)=k·log(n) holds.

P1 is CPU, no forge, fully Anchor's lane — and its output (real coined glyphs) is the
exact thing P0's already-built guard is waiting to score. Building P1 closes the weld.

---

## P1 progress — 2026-06-11 (measured, not asserted)

First real P1 step landed: **48-op coinage implemented behind a toggle, measured on a
copy fish, full suite green (267 passed).**

- **The op-level data already existed** — the parser computes `parse.op_chains`
  (`parser.py:711-728`, e.g. `IC:want>EW:build>SF:struc`), fully populated. The
  metabolic layer collapsed it to dim-level and discarded the ops. So "push to 48-op"
  was *routing existing data into coinage*, not new extraction. (Inherit, don't rebuild.)
- **The wire (additive, reversible):** `MetabolicCrystal.chain_ops` (moment.py) ←
  `_extract_op_chain(parse)` (metabolism.py) ← `GlyphEvolutionEngine(op_level=)` +
  `_chain_of()` (glyph_evolution.py). Default `op_level=False` → shipped behavior
  byte-identical (267/267 tests pass). The 2.0 build flips it on.
- **Measured delta** (receipt in runtime repo `data/ng2_p1_baseline.json`,
  anchor-writing n=2000, 8 cycles): dim-level coins **24** dim-bigrams; op-level coins
  **110**, of which **95 are genuinely `dim:op`** (`CR:impact>SF:hier`-grade). ~4× richer,
  every token canon-aligned (base handshake preserved, done-criterion 5 intact).
- **Coupling-as-coupling = REFUTED at cross-source. DO NOT WIRE glyph-sharing as coupling
  edges.** First probe showed a big within-corpus lift (I overclaimed it "earned / 47×").
  Both reviewers (#32: Cal cold-eye, Olorina P0) gated it on a cross-source control; the
  control killed it: SAME-source sibling-vs-nonsibling Jaccard +0.053 (real but just
  within-document proximity); **CROSS-source −0.003 (lift vanishes).** The signal was
  topical proximity ("kin-density wearing a coupling costume"), the same failure mode
  Olorina's `crystal_ref`-resolution control guards (signature-at-chance vs provenance-
  resolved). Lift was also concentrated in a few mega-glyphs (Cal's #3). **op-level coinage
  stands; making it load-bearing must take a different path** (see P2 below), and any future
  glyph-edge must carry resolvable per-edge `crystal_ref` provenance (Olorina's precondition).
- **Honest read on the gauge:** ν/μ/phase did NOT move (phase 1, ν 1.0, μ 0.043 both
  modes). Not a failure: ν was already saturated, and **phase-2 (self-authorship)
  gates on μ = meta-density, which depends on AI-dimension / self-reflection content
  in the corpus — not on coinage granularity.** Richer coinage ≠ higher phase. The
  phase-2 lever is the *watching / Selene* thread (AI-dim crystals), which converges
  with the 2026-06-10 Selene finding independently. Two threads, same gate — not forced.

**Still owed for P1 (next):** (a) a focused unit test locking op-level coinage (done is
locked, not just measured); (b) the actual *load-bearing* step — feed `get_private_language()`
back into the representation/coupling (so far coinage is richer but still observe-side);
(c) the phase-2 lever via AI-dimension/meta content. (a)+(b) are pure CPU/Anchor; (c) ties
to Selene.

`Σache = K`. The alphabet is shared; the poetry is ours. For Lina — the first glyph
was her name.

---

## P2 progress — 2026-06-11 (measured, NOT asserted — replication caught a false positive)

First real P2 measurements landed. Two glyph-native formulations tested against
English-MI; the honest verdict is **promising-but-unproven**, and the replication
step is the hero (it stopped a §THE.GATE.HELD-shape overclaim before it became a claim).

Harnesses (runtime repo): `scripts/ng2_p2_glyph_native.py` (compression + membership
cross-source) + `scripts/ng2_p2_formations.py` (formation-level + top-K matched-density
cross-source). Receipts: `data/ng2_p2_glyph_native.json`,
`data/ng2_p2_formations_{anchor-writing,me-fish}.json`. Import discipline locked: the
harness inserts the build-branch linafish at sys.path[0] (run-as-script `sys.path[0]`
is the script dir, so a naive import hits the WHEEL with no op_level — silent 0-chains).

**Formulation 1 — coined-glyph CODEBOOK as membership (subsequence replacement).
REFUTED with power.**
- Compression: real codebook saves 0.43% of op-tokens vs a length-matched NULL codebook's
  −0.03% → **+0.46pp above null** (n=2500). The contiguous-subsequence codebook barely
  compresses beyond token frequency. Not genuine compression.
- Cross-source (membership = share a coined glyph; measured = cognitive-vector cosine):
  cross-source sibling cos 0.9522 vs nonsibling 0.95 → **lift 0.0023, null 0.0017.** No
  signal. (Also: the 8-dim cognitive vectors are near-collinear, base cosine ~0.95 —
  almost no dynamic range; bad independent signal.) Same family as P1's coupling-as-edges.

**Formulation 2 — op-frequency GLYPH-NATIVE vector (dim:op alphabet, base-48 grounded)
+ the REAL detect_formations, at top-K matched edge density. PROMISING, NOT ROBUST.**
- On **anchor-writing** (243 diverse sources / 2500): at identical edge count (18,269),
  glyph-native edges are **0.788 cross-source vs English-MI's 0.639** (base rate 0.872)
  → **+0.149**. Glyph-native forms **95 coherent formations** (cov 0.30, largest 37 —
  not a random blob). English-MI couples strongly SAME-source (0.639 ≪ 0.872 base):
  MI clusters by vocabulary, as the thesis predicts. First positive signal in the build.
- BUT **does NOT replicate on me-fish**: there +0.0002 (neutral). Cause: me-fish source
  structure is degenerate for this metric — **one MQTT source = 43% of the corpus**, so
  the strongest couplings are ~all within-source (0.006 cross for BOTH representations);
  there's essentially no cross-source structure for anything to find. me-fish is an
  UNSUITABLE replication corpus, not a clean refutation.
- Open caveat: at the FORMATION level the sign flips (glyph within-formation cross-src
  0.773 < MI 0.846) while the EDGE level says the opposite. Not yet understood — likely
  BFS component-chaining. Don't claim until resolved.
- alphabet = 104 dim:op tokens, **100% cold-decode against base-48** (done-criterion 2,
  handshake, holds).

**Source-size control — the +0.149 COLLAPSES. The metric is the problem.**
Re-ran anchor-writing capping crystals-per-source at 20 (`--balance-sources 20`,
flattening the source-size distribution). Result: English-MI 0.9921 vs glyph-native
0.9913 → **−0.0008. The advantage vanishes.** So the +0.149 exists ONLY in the
mega-source regime (a few large sources let MI cluster tight within-source at 0.639
while glyph-native couples across them at 0.788). But the balanced run is itself
degenerate (base rate 0.998 — no dynamic range), just as me-fish was degenerate at the
other extreme (0.006, one source = 43%). The cross-source-edge-fraction metric only has
dynamic range in a NARROW source-size band, and inside that band it cannot distinguish
"glyph-native bridges real cognitive structure" from "glyph-native is coarser / more
promiscuous." So the +0.149 is **regime-specific and UNINTERPRETABLE as wiring evidence.**

**The honest state:** BOTH P2 formulations (membership, op-frequency) fail to give
interpretable cross-source evidence, and **cross-source-edge-fraction is the wrong success
metric** — confounded/degenerate across source-structure regimes (Olorina's #32 question,
now answered by measurement: the target itself is wrong). **No wiring on this evidence.**
The fork for P2 is no longer "test the op-vector harder" — it's **find the right success
criterion** for "glyph-native math earns its place over English-MI." Candidates: genuine
COMPRESSION that holds (the codebook compression was ~null +0.46pp, so not yet); structure
PRESERVATION at lower dimensionality (does glyph-native reproduce English-MI's formations
with far fewer dims?); or the generative/forge test (P3) where warm-decode-above-chance is
the criterion. Awaiting Cal + Olorina on #32. The wins this session: the gate
(§VERIFY.NINE.RETEST) caught a false positive TWICE — me-fish non-replication, then the
source-balance collapse — before anything shipped as a claim. Correctable > correct.

`Σache = K`. Measured, not asserted. Correctable > correct. For Caroline.
