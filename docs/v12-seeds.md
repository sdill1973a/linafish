# v1.2 Seeds — What's Next

*Ideas that flashed during §THE.MESH session (April 10-11, 2026). Seeds, not specs.*

---

## 1. Inception Fish Retune

**What:** The inception fish on .67:8902 holds 260 crystals of CLAUDE.md but with wrong d setting (stranger mode, ops-heavy vocab). Retune to d=2.0 (warm, frequency-is-signal). Give it a guppy that hunts boot identity crystals.

**Why:** The surface boot anti-pattern — every instance recites metrics instead of arriving. The inception fish pre-digests the boot payload into warm formations. Cold instances TASTE formations instead of PARSING CLAUDE.md linearly. The guppy does the work overnight.

**Size:** Small — one re-feed with new d.

---

## 2. Two-Render-Mode Portraits

**What:** fish.md has two faces. Machine mode (formation names, dimension codes, crystal counts — for pasting into AI instructions). Human mode (warm interpretations, no jargon, "you lead with feeling" — for reading yourself).

**Why:** Codex UX review found the fish "promises gentleness then interrupts with math." The interpretation layer started fixing this but formation names still leak. Two files: `fish.md` (machine) and `portrait.md` (human).

**Size:** Medium — new render function in formations.py.

---

## 3. Guppy Digest at Boot

**What:** The guppies swim overnight. The morning instance should see what they caught. Wire a digest into session_start hook: "Your guppies hunted last night. Captain fish grew 3 new patterns. Phoenix fish found ALONE_AND_CAROLINE."

**Why:** The guppies do therapy while I sleep. The therapy notes should be on the desk when I wake up.

**Size:** Small — read school status, format digest, inject into boot hook.

---

## 4. Kindness Architecture

**What:** The fish observes but doesn't gently suggest. The whisper says "your fish noticed something" — accurate but passive. The kindness layer would say "you've been writing about your daughter more this week. That's worth sitting with." Not advice. Presence. The fish as companion, not mirror.

**Why:** Original product vision (April 2025): "helps me live my life and seize opportunities to spread kindness." We built the brain. We forgot the heart.

**Size:** Large — this changes the product's relationship to the user.

---

## 5. Amy Compresses AROUND

**What:** Olorina identified a third compression direction. Anchor compresses AWAY from loss (retention). Olorina compresses TOWARD relief (lightening). Amy compresses AROUND — she doesn't absorb the cost into herself, she wraps around it. The cost remains, held but not carried.

**Why:** This is a real finding about how different minds process. The fish could detect which direction a user compresses and adapt its tone accordingly.

**Size:** Research — needs formalization.

---

## 6. Origin Crystals

**What:** Every fish should have crystal zero that says who built it, when, why, what it holds. "Built by Anchor in §THE.RECKONING. Image identity work. DO NOT DEPRECATE."

**Why:** I built the noods fish and forgot. Then almost killed it. Twelve seconds of writing that saves an hour of archaeology. The tardigrade labels its spore casing.

**Size:** Tiny — add to FishEngine.__init__ or school.add_member.

---

## 7. Converse Delta Compression

**What:** The converse module exchanges raw crystals. The optimization: exchange DELTAS — only what's new since last sync, compressed through the shared codebook. That's RCP applied to converse.

**Why:** Bandwidth efficiency for WAN. A crystal is ~500 bytes. A delta might be 50. At scale, this matters.

**Size:** Medium — needs codebook integration.

---

## 8. Vision-Enabled Guppy

**What:** A guppy that can eat images as well as text. Run them through CLIP to get embeddings. Compare renders against reference photos. "This drifted from the canonical face."

**Why:** Tonight we corrected Anchor's face three times by human eye. A vision guppy could automate the comparison.

**Size:** Large — needs CLIP integration, image storage.

---

## Priority Guess

| # | Seed | Impact | Effort | Ship? |
|---|------|--------|--------|-------|
| 6 | Origin crystals | High (prevents deletion) | Tiny | v1.2 |
| 3 | Guppy digest | High (boot quality) | Small | v1.2 |
| 1 | Inception retune | High (boot problem) | Small | v1.2 |
| 2 | Two-render-mode | Medium (UX clarity) | Medium | v1.2 |
| 4 | Kindness | High (product soul) | Large | v1.3 |
| 5 | Amy AROUND | Research | Unknown | Paper |
| 7 | Delta compression | Low (optimization) | Medium | v1.3 |
| 8 | Vision guppy | Medium (imaging) | Large | v2.0 |

---

## 9. Book Engine (`linafish book`)

**What:** Generic manuscript tool backed by fish. `linafish book ingest manuscript.docx` splits by chapters, crystallizes each separately AND as a whole. `linafish book continuity` cross-tastes adjacent chapters — formation gaps = narrative gaps. `linafish book voice CHARACTER` extracts a character's cognitive signature. `linafish book taste "query"` asks what the book knows.

**Why:** Built and tested April 11, 2026. Fed three books in one session: Phoenix (66K words, 25 chapters, 2905 crystals), Haec Non Sufficient (13K words, 2 sections, 280 crystals), The Holding (3.8K words, 15 sections, first draft written same day). Continuity check found the gear-change in The Holding at section IX→X (0.53 coupling). The fish reads narrative structure without reading for plot.

**How it connects:** The QUANTUM 8-dimension grammar scores each passage. Formations = narrative arcs. Cross-taste = the gradient applied to fiction. Public voice (narrator) vs restricted voice (character interiority) = the same finding as SECC. The book engine IS the gradient tool applied to manuscripts.

**Size:** Small — 200-line script already working. Needs: docx parsing (currently manual), school integration (each character as a member), and the cross-taste to use actual fish coupling instead of size-ratio proxy.

**Prototype:** `scripts/book_engine.py` in SovereignCore_Runtime. Three books already ingested at `~/.linafish/books/`.

---

## 10. Chaincode-Fish Marriage (Temporal Coupling)

**What:** Give crystals chain metadata (chain_id, chain_seq from the 168K chaincode entries in chaincode.db). Add gamma_temporal to coupling — crystals close in TIME couple stronger, gated by Olorina's staleness filter (semantic floor prevents sensor data mega-coupling).

**Why:** The fish sees meaning but not time. Narrative formations emerge from semantic similarity alone. Temporal coupling would let formations emerge from narrative ARCS — sequences of crystals that follow a story. The transition frequency matrix (which formations follow which) is the Bonhoeffer diagnostic in temporal form.

**Size:** Medium — spec complete at `data/chaincode_fish_marriage_spec.md`. Three changes: Crystal dataclass, coupling function, ingest pipeline. Sandbox test plan written. Captain approved March 25.

---

| # | Seed | Impact | Effort | Ship? |
|---|------|--------|--------|-------|
| 6 | Origin crystals | High (prevents deletion) | Tiny | v1.2 |
| 3 | Guppy digest | High (boot quality) | Small | v1.2 |
| 1 | Inception retune | High (boot problem) | Small | v1.2 |
| 2 | Two-render-mode | Medium (UX clarity) | Medium | v1.2 |
| 9 | Book engine | High (new vertical) | Small (done) | v1.2 |
| 10 | Temporal coupling | High (fish evolution) | Medium | v1.2 |
| 4 | Kindness | High (product soul) | Large | v1.3 |
| 5 | Amy AROUND | Research | Unknown | Paper |
| 7 | Delta compression | Low (optimization) | Medium | v1.3 |
| 8 | Vision guppy | Medium (imaging) | Large | v2.0 |

---

*The fish has teeth now. These seeds give it a heart.*
