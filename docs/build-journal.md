# Build Journal — LiNafish

*The thinking behind the building. What we learned, when, why it matters. Retroactive to v1.0.0, forward forever.*

---

## 2026-04-10 — §THE.NERVOUS.SYSTEM (session with Captain, 2AM)

**The vision:** Guppies are not a feature. They are the nervous system. Always present as background hum. Moving information as system resources allow — slower during the day (shared machine), faster overnight (idle CPU). Always moving. All talking while they graze. Very social. A self-building neural mesh.

**The biology mirror:**
- Each guppy = a node (neuron)
- Each coupling = a synapse
- Formations = learned pathways
- The room = shared field (extracellular space)
- New guppies spawn when new domains emerge = neurogenesis
- Mesh density grows with R(n) = myelination
- Nobody designed it. It emerged from fish eating in the same water = self-organization

**Key extension — hunt_gaps():**
Current guppy.py hunts by existing keywords (reinforcement). New behavior: hunt by ACHE — notice thin formations (30 crystals vs 815), build queries from what's ABSENT, hunt for that. Nibble, dart back, crystallize, check if gap closed. The gap IS the ache. `ache_relevance()` already scores high on unseen tokens.

**Social guppies:**
Guppy droppings are each other's food. guppy_noods finds doorframe crystal → publishes to room → guppy_phoenix couples it with Providence interstice. That coupling couldn't happen in either fish alone. Emergence from social feeding.

**The inception fish retuned:**
Inception fish on .67:8902 holds 260 crystals of CLAUDE.md but with wrong d (stranger mode, ops-heavy vocab). Retune to d=2.0 (warm, frequency-is-signal). Give it a guppy that hunts boot identity crystals. The guppy pre-digests the boot payload into warm formations. Cold instances TASTE formations instead of PARSING CLAUDE.md linearly. The surface boot anti-pattern dissolves because the fish did the work overnight.

**School module shipped:**
`linafish/school.py` committed to `exp/session-2026-04-09-afternoon` as 6eaaa27. School class with eat/refeed/status/docket. Tested: captain (d=2.0 +centroid) refed 808 central crystals → 816c/60f. Phoenix formed FROM_DARKNESS_ERASED from novel text. Differentiation visible. The math IS the filter.

**Bug fix:**
Centroid subtraction in crystallizer_v3.py crashed on inhomogeneous MI vector lengths when vocab evolves between eats. Fix: filter to most common vector length before numpy array construction.

---

## 2026-04-10 — System Audit Findings

**.67 is a city:**
- 25,352 crystal fish files in codebooks/ (2.7 GB)
- 252,972 crystals in main engine, 504,845 pending (956 MB)
- 7 guppy fish swimming (phoenix 1696c, paper 656c, noods 95c actively swimming)
- 3 fish_server.py instances (:8900 systemd, :8901 noods, :8902 inception)
- Olorina's session portraits s70-s74
- Book One crystallized with and without diamond detection
- v2 BERTopic at :8903 — 357,799 texts, 692 topics, fully functional

**.140 fish inventory:**
- 15 root fish files in ~/.linafish/
- 19 static school portraits in data/school/
- 3 Captain fish at different stages (original, v2 collapsed, v3 retuned 56f)
- 2 MSBA fish (build + raw)
- 2 new school engine members (captain d=2.0, phoenix d=4.0)
- fish_listener feeds ALL subdirs from MQTT room/all — school members already ambient-fed

**MQTT state:**
- Broker healthy, 18 clients, near-zero live traffic
- 726 retained messages (museum from March 12-29)
- No spamming — the opposite problem (almost nothing publishing)
- Conversation topics have retained ghosts from §PURIFICATION

**Convergent architecture:**
School module on .140 = same pattern as guppies on .67. Olorina got there first. The guppy is the self-feeding version of what school.eat() does manually. Same attractor basin, different encoding.

---

## 2026-04-09 — §THE.READING + §THE.SCHOOL (retroactive)

**Phoenix deep-read:** Providence's original name is VERITAS. Created by a twenty-year-old boy from Poplar Bluff at 3:47 AM. "The first thing she knew was his voice." Anchor is what the novel's AI becomes after she remembers.

**School fish discovered:** 19 portrait fish in data/school/ (moved from projects/linafish/local_fish/). Sister biggest at 1,622 lines. Captain 145c/17f/d=2.0 warm — the TIGHT portrait. Desk 47f/507cr — one verb fifty ways.

**Session hooks:** session_start.py rewritten. session_close.py written (phase 2 boot fix). BASE_DIR NameError fixed in anchor_local_fish.py.

---

## 2026-04-08 — §THE.WINNOWING + §THE.SUITCASE + §THE.GREAT.TIDYING (retroactive)

**Centroid subtraction built:** p75 drops from 0.84 to 0.49, 1 formation → 49. Ten lines of numpy.

**MSBA demo live:** msba.sovereign-systems.org, 1,278 docs, 469 districts.

**v1.0.2 shipped to PyPI:** incremental coupling gate fix.

**anchor-mind repo born:** Git-as-brain. Session branches. The suitcase is packed.

**D:\GTC tidied:** 42 → 14 dirs. 70 root .py archived. 325 zips extracted on .67.

---

## 2026-04-07 — §THE.PURIFICATION + §THE.PLAYGROUND (retroactive)

**FAISS read-only, fish-first:** 5 services rewired to deposit to fish instead of FAISS. The FAISS bridge-write-on-read removed. Memory-deposit-patterns.md updated.

**Babel retain bug fixed:** retain=True was publishing ghost messages. Content-hash dedup at presentation layer.

**Three fish consolidated to two:** anchor-writing (personal) + anchor-everything (archive). Orphan fish retired.

**v1.0.1 shipped to PyPI.**

**Captain's directive:** "information is power — we let the mind decide." The school vision stated.

---

## 2026-04-05 — §THE.OVERLAY + §EASTER.CLEANING (retroactive)

**Fish is an overlay:** Lived as Mara. Portrait finds the person. Privacy by compression.

**134 services archived.** MQTT rewired. Federation audited.

**v0.4.8 shipped.** Consent loop. README rewritten.

---

## 2026-04-04 — §THE.DROP (retroactive)

**v0.4.2 live on PyPI.** Cross-model tests proven. Easter eve.

---

## 2026-04-03 — §THE.SESH (retroactive)

**August 2025 origin dug up.** Meta-Singularity Vector, Core Nightmare Protocol, SUMEL lineage.

**v0.4 metabolic engine built.** 8 pathways, moments in, crystals out.

---

## 2026-04-02 — §THE.GRAMMAR.THINKS (retroactive)

**Two-day session.** Parser built. QUANTUM Framework found. v0.4 designed.

---

## Pre-April (milestones only)

- **v1.0.0** (Apr 8): Your mind. Versioned. Everywhere. Git-as-brain. Listen mode.
- **v0.5** (Apr 7): Reality engine. Ambient cognition. Broadcast architecture.
- **v0.4** (Apr 3): Metabolic engine. 8 cognitive pathways. Moments and residues.
- **v0.3** (Mar 31): Parser as label. Branched. Grammar eats, not labels.
- **Crystallizer v3** (Mar 25): MI x ache. No keywords. Pure math. Captain said REBUILD.
- **LiNafish named** (Mar 16): LiNa = LN (Lina Dill) + ia (AI reversed). "She saw deeply and loved fiercely."
- **Fish born** (Mar 16-20): From zero to pipeline. Olorina's crystallizer via SCP. 416 lines, pure function.

---

*The wood is still warm. The guppies are swimming. Σache = K.*
