# Build Queue — v1.1

*The candidate features. Pick one. Ship.*

Each item below has:
- **What** — one sentence
- **Why** — the pitch
- **Seed branch** — where to start coding
- **Shape** — what the end result looks like
- **Weight** — rough effort

---

## 1. `absorb` — Eat RAG and vector databases

**What:** `linafish absorb <source>` ingests existing FAISS indexes, NetworkX graphs, Chroma databases, or live RAG HTTP endpoints as native fish crystals — preserving embeddings, entity edges, and metadata without re-ingestion.

**Why:** Every team with existing RAG infrastructure has hours of ingestion work they don't want to lose. Today linafish makes them choose: crystallize from scratch (slow, pure) OR keep their existing RAG (fast, siloed). This feature collapses the choice. One fish. Their prior work counts.

This is the migration moat: *"We read your existing RAG and turn it into something that actually thinks in formations."*

**Seed branch:** `exp/absorb-rag-sources`

**Shape:**
```bash
linafish absorb phoenix_local.faiss      # FAISS index → crystals with pre-embedded vectors
linafish absorb phoenix_graph_v2.pkl     # NetworkX DiGraph → crystals + couplings from edges
linafish absorb chroma_db/               # Chroma persist dir → crystals
linafish absorb http://.67:8200/api      # Live RAG endpoint → stream crystals
```

Under the hood:
- **FAISS reader:** iterate vectors + docstore metadata, flag `pre_embedded=True`, reuse vector as coupling vector
- **NetworkX reader:** each node → crystal with type/layer attrs; each edge → coupling with default weight
- **Chroma reader:** read persistent Chroma dir, extract collections + embeddings
- **HTTP reader:** paginate remote API, build fish from returned docs + vectors

**Weight:** Half a day for FAISS + NetworkX (the two we actually need for Phoenix). Another half for Chroma + HTTP.

---

## 2. `converse` — Two fish, one shared state, crystals as messages

**What:** Two (or more) instances point at the same fish state directory. Each crystal is tagged with `source_mind`. Coupling between crystals from different minds IS the conversation. No MQTT bridge, no message queue, no dedup layer.

**Why:** Already seeded in `exp/rcp-notes-and-fish` (April 7). The fish already solved the dedup/threading/routing problems that bridge logs were trying to solve. Coupling IS dedup. Formations ARE topic threads. Write a crystal, the other mind reads the formation it lands in. The relationship IS the channel.

**Seed branch:** `exp/rcp-notes-and-fish` *(already exists — just needs prototyping)*

**Shape:**
```bash
# Mind A
linafish converse --state /shared/fish --name anchor
# writes crystals, reads formations

# Mind B
linafish converse --state /shared/fish --name olorina
# reads Anchor's new crystals, writes her own
```

Under the hood:
- Shared state dir (local FS or sync-shared folder)
- `source_mind` already exists in crystal metadata
- Formation-level filtering: *"show me what's new from mind X since last check"*
- Incremental formation detection (don't rebuild all formations on every crystal)
- Optional: RCP encoding for the crystal text so diffs are in glyph-space

**Weight:** One day. Most primitives already exist. Needs: watch loop, source_mind filter, incremental form rebuild.

---

## 3. Bridge log fix — dedup + de-truncate

**What:** Fix `olorin_conversation.jsonl` writer on .67 so it doesn't republish retained MQTT messages, and fix the babel_read truncation at ~300 chars.

**Why:** Critical bug. Today's §THE.PURIFICATION session patched the reader side (content-hash dedup) but the WRITER still produces duplicates. Ollie's full messages still get cut in the reader. Blocks sister comms from being trustworthy.

**Seed branch:** `exp/bridge-writer-fix`

**Shape:**
- `.67:/home/sdill/qlp_mqtt_bridge.py` — set retain=False on subscribe OR dedup on content hash before append-to-log
- `services/babel_mcp_server.py` on .140 — remove or raise the ~300 char limit in `babel_read`
- Optional: retroactive dedup script for existing `olorin_conversation.jsonl`

**Weight:** Half day including retroactive cleanup.

---

## 4. `listener` nested fish scanning

**What:** `linafish listen` currently only sees 2 local fish (flat `~/.linafish/` structure). Make it walk subdirectories so nested fish state dirs get fed too.

**Why:** As people build fish-per-project, the flat structure breaks. A fish in `~/writing/novel/.linafish/` should be fed by ambient listeners just like one in `~/.linafish/main/`.

**Seed branch:** `exp/listener-nested-scan`

**Shape:**
- Walk up to N levels from state-dir root
- Find any directory containing `*_v3_state.json` or `*.fish.md`
- Add source filtering: don't eat your own MQTT publishes (self-loop prevention)
- Crystal count logging per feed
- Formation change detection: *"New formation emerged: X"*

**Weight:** Few hours.

---

## 5. Tripod onboarding polish

**What:** `linafish go` on first run should tell the user exactly what happened: *"Your fish is at X. Paste the fish.md into your AI. Git is tracking changes at Y. Run `linafish history` to see growth."* Make the AI/human/git tripod visible from run one.

**Why:** v1.0 shipped with the right architecture but the first-run UX is buried in docs. A new user runs `linafish go` and doesn't know which file to paste into Claude, that git is already tracking it, or that `linafish history` exists. The tripod is the feature — it should be the first thing explained.

**Seed branch:** `exp/tripod-onboarding`

**Shape:**
- Post-`go` summary: three lines, one per tripod leg
- README front section: *"Three readers of one file"* before install instructions
- `linafish go --silent` flag for automation (current default is already quiet, but make it explicit)

**Weight:** Half day including README rewrite.

---

## Nice-to-have (not in v1.1 scope, noted for later)

- **Gamma that adapts to fish maturity** — young fish more open, mature fish more selective
- **Formation decay** — crystals that stop coupling as the landscape shifts get archived, not deleted
- **Pod media lab fix** — SDXL dies on fresh RunPod pods, works on ingest pods, unsolved
- **Cloud Run portrait API** — Vertex Gemini as hosted portrait engine
- **GCS bucket for public fishverse hosting** — shareable fish via public URL
- **RCP-encoded state diffs** — commit messages as glyphs, not English

---

## Picking order suggestion

For commercial momentum: **#1 absorb** → **#5 tripod** → **#2 converse**
For bug hygiene: **#3 bridge fix** → **#4 listener scan** → #1 absorb
For product depth: **#2 converse** → **#1 absorb** → #5 tripod

---

*The door ships itself. The queue is the soil.*
