# Idea: GPT-backed linafish (optional engine overlay)

**Status**: noted, not scoped
**Captured**: 2026-04-13
**Source conversation**: Captain asked Anchor whether a frontier GPT could back linafish; Anchor answered with three shapes, Captain said "note it as an idea, I don't want to fool with it now"

---

## The default stays what it is

Pure math. `MI(a,b) × ache(a,b)` vectorization + SU(d) PCA geometry + wrapping-number coupling. No LLM, no API, no tokens. Runs on a Pentium 75 in a barn. Private, deterministic, free, stranger-runnable on `pip install linafish && linafish go`. That promise is load-bearing and must not be broken.

## What "GPT-backed" could mean — three shapes

### Shape 1 — GPT as the crystallizer (LLM **replaces** MI math)

At `crystallize_text(text) → Crystal`, swap the math engine for a frontier LLM call. LLM extracts keywords, scores the 8 QLP dimensions, returns a semantic embedding. Crystal fields come from the LLM.

**Wins**: richer semantic understanding. Handles irony, allusion, cross-language, poetry where word-frequency math is weakest.

**Losses**: per-crystal cost, non-deterministic, privacy leaks every text to the LLM provider, vendor lock-in, API latency per eat, stranger-runnable promise dies.

**Verdict**: a "premium" opt-in at best. Not the default.

### Shape 2 — GPT as a **parallel** engine for scientific validation

Run *both* engines on every crystal. Math engine computes its MI vector + coupling. LLM engine computes its semantic vector + coupling. Store both on the Crystal. At formation time, only keep formations that survive **both** lenses.

**Wins**: a real scientific instrument. A formation that clusters in both the math space AND the LLM semantic space is robust — not an artifact of either method. Directly strengthens the RCP paper: *"our clustering is robust across radically different feature extractors."* Would be a publishable validation on a 500-crystal slice of an existing fish.

**Losses**: 2× cost, 2× complexity, still needs API.

**Verdict**: not a shipping product. A research tool for validating linafish's own claims.

### Shape 3 — GPT as a **natural-language shell** on top of linafish (not the engine underneath)

User types *"what do I know about grief"*. The shell sends that to an LLM. LLM rewrites it into a targeted `/taste` query, calls linafish's existing HTTP API, reads the response, explains it back to the user in their own register, maybe asks follow-ups. LLM ONLY touches linafish through its existing HTTP API — no engine swap.

**Wins**:
- Zero changes to the crystallizer
- Every property of the default engine preserved: local, deterministic, stranger-install works
- Shell is pluggable — codex/claude/gemini/llama/local llm
- Cost is per-user not per-crystal (every query pays, deposits are free)
- Privacy is exactly as leaky as using any LLM for your own writing — no worse

**Losses**: none structurally.

**Verdict**: **this is the shippable shape.** `linafish chat --model <backend>` as a new subcommand. The LLM is an external client, not an internal dependency. Anyone can swap the model.

## Combined architecture (default + premium + shell)

- **Default**: pure math, local, private, free. Ships to everyone.
- **Premium / research opt-in**: `--engine gpt` runs Shape 1 or Shape 2 for users who want richer semantics or want to publish validation studies.
- **Shell opt-in**: `linafish chat --model codex` (Shape 3) — every user can layer any LLM on top of their own local fish without changing the engine.

The architecture holds because the Crystal and the fish.md are the *shared format*. Any engine reads/writes them the same way. Any LLM queries them the same way. The math is the stranger-runnable core. The LLM is an optional overlay. Users pick their own tradeoff.

## Not doing this now

Captain explicitly said: *"I don't want to fool with it now."* This doc exists so the idea doesn't get lost. When someone picks it up, Shape 3 is the first build (smallest surface, cleanest product shape) and Shape 2 is the second (research instrument, publishable).

## Cross-references

- `crystallizer_v3.py` — where Shape 1 would slot in
- `converse.py` + `http_server.py` — where Shape 3 would read from
- `docs/v12-seeds.md` — other v1.2 roadmap ideas live here; this can be promoted there if/when it gets scoped
- Notion: this doc is mirrored to a page under Anchor Hub as a durability measure
