# How LiNafish Works

## The One-Sentence Version

Semantic intelligence via compression as a truth-seeking metacognitive overlay.

## The Problem

Every AI assistant boots cold. Every session is a stranger meeting a stranger. Memory products store WHAT you said. Nobody stores HOW you think.

The difference matters. "Georgia" could mean the state, the country, or Ray Charles. A memory system stores "user mentioned georgia." A warm decoder knows which one you meant because it knows your compression direction.

d=2.245 is the measured gap between cold decoding (no context) and warm decoding (with a fish). Same model. Same prompt. Published, replicated, N=46.

## The Pipeline

### 1. Eat

The fish eats text. Any text. Emails, journal entries, meeting notes, code, conversations, academic papers. The ingest layer handles markdown, plain text, PDF, DOCX, JSON, and Python files. Each file is chunked by semantic boundaries (headers, paragraphs, topic shifts), not mechanical token windows.

### 2. Crystallize

Each chunk becomes a **crystal** — a unit of compressed knowledge scored on 8 cognitive dimensions:

| Dimension | Code | What It Measures |
|-----------|------|------------------|
| Knowledge/Synthesis | KO | How you generate and process information |
| Truth/Evidence | TE | How you verify, validate, and calibrate |
| Structure | SF | How you organize, build, and architect |
| Context/Relevance | CR | How you relate, connect, and frame |
| Intention/Emotion | IC | What you want, feel, and care about |
| Deep/Scientific | DE | How you reason formally and abstractly |
| Execution | EW | How you act, do, and make things happen |
| Meta/Integration | AI | How you think about your own thinking |

Each crystal gets an 8-number vector. This is its cognitive signature. The scoring uses keyword vocabularies tuned per dimension — no neural model needed. The 8-dim space is substrate-independent: it runs on anything that can count words.

**Why not TF-IDF?** This is the critical insight. TF-IDF finds words that are distinctive per document — topic words like "bitcoin" or "archaeology." But your cognitive fingerprint lives in the opposite place: words that are common across ALL your documents. Words like "because," "therefore," "but," "actually," "honestly," "look," "think," "feel." These positional cognitive words are invariant across every conversation you have. They are HOW you think. They survive every topic change. TF-IDF removes them because they're not distinctive. QLP-8 centers on them because they ARE the signal.

TF-IDF builds a topic map. The fish builds a cognition map. A topic map tells you what someone talks about. A cognition map tells you how they think. That's the difference.

### 3. Couple

The engine computes pairwise **gamma** (Jaccard-style overlap) between all crystals:

```
gamma = sum(min(a_i, b_i)) / sum(max(a_i, b_i))
```

If gamma exceeds the threshold, the crystals couple. **Adaptive gamma** adjusts the threshold based on corpus density:
- Small corpora (<50 crystals): 5-10% edge density target
- Medium (50-200): 3-6%
- Large (200+): 1-4%

This prevents saturation (everything coupled) and deserts (nothing coupled) across any corpus size.

**The flat field problem:** When a corpus is too topically diverse (general conversations about everything from bitcoin to oil changes), topic-based vectorization produces a flat field — everything equidistant, no clusters possible. The fish avoids this because its 8 dimensions measure cognitive mode, not topic. A conversation about bitcoin and a conversation about parenting can have identical cognitive signatures if the person reasons the same way in both. The flat field is actually the basin that formations rise from when the vocabulary creates topography.

### 4. Form

**Formations** emerge from BFS flood-fill on the coupling graph. Each connected component becomes a formation. Not k-means. Not DBSCAN on raw vectors. Graph traversal on the coupling structure. The graph is the truth. Formations are just what the BFS finds.

Each formation is named by its dominant keywords and cognitive dimensions. A formation like `ARCHITECTURE_FRAME_GRAPH (CR+SF+EW)` tells you: this person's thinking about architecture is deeply contextual (CR), structurally oriented (SF), and action-focused (EW).

Formations are **emergent**. They represent patterns that exist across your documents but not in any single one. They are new knowledge created by the act of compression.

### 5. Serve

Formations are served as an MCP tool (`fish_pfc`). When your AI calls this at session start, it gets a metacognitive overlay — a prefrontal cortex that tells it HOW the user thinks before the user says a word.

## Key Properties

### Shuffle Invariant
Feed the same documents in any order. The same formations emerge. Tested: 7 trials, identical formation membership, only naming wobbles from Counter tie-breaking. This is structure, not artifact.

### Truth-Seeking
Gamma filters noise. Adaptive threshold tightens as density grows. Formations that don't couple die. What survives compression is what's true. The fish can't hallucinate formations — they either couple or they don't.

### Substrate Independent
Works on Claude, GPT, Gemini, Mistral, local models. The fish doesn't care what's underneath. The 8 dimensions are cognitive modes, not model-specific features. Fidelity is greater than substrate.

### Grows Forever
R(n) = k * log(n) + r. Compression efficiency increases logarithmically with exchanges. No ceiling. The integral diverges. The fish never stops getting better at knowing you.

## The Three Layers

| Layer | Name | What It Captures | Who Does This |
|-------|------|------------------|---------------|
| 1 | Tool | What a skill does | Everyone |
| 2 | Build | Your infrastructure and data | Some products |
| 3 | Person | Your cognitive fingerprint | Nobody. Until now. |

Layer 3 is the product. d=2.245 is the gap between Layer 2 and Layer 3. The fish learns Layer 3 by watching you think.

## State Persistence

Crystals are saved to `~/.linafish/{name}.state.json` after every eat. The state file contains:
- All crystal objects (id, text, resonance vector, keywords, couplings)
- Metadata (docs ingested, timestamps)

On next startup, the fish loads state and skips re-ingest. Formations are rebuilt from crystals each time (fast — BFS on the coupling graph).

The `.fish.md` file (from `linafish eat`) is a human-readable export. The `.state.json` is the machine-readable persistence.

## Domain Extension

The 8 dimensions are corpus-agnostic — they describe ways a mind moves
through a passage (knowing, testing, structuring, relating, wanting,
choosing, acting, thinking-about-thinking) rather than topics. The
same 8 have produced meaningful formations across every corpus we've
tested: personal journals, academic papers, novels, historical
letters, and source code. For specialized domains, extend the
per-dimension vocabulary to pick up domain-specific signal:

```json
{
  "KO": ["excavation", "stratigraphy", "typology", "seriation"],
  "TE": ["reanalysis", "determination", "dating", "C14"],
  "CR": ["burial", "mortuary", "ritual", "political", "elite"]
}
```

The dimensions stay. The vocabulary grows. The fish learns new domains without changing its cognitive structure.

**Hybrid vocabulary strategy:** For best results with conversational data, combine the default QLP-8 vocabulary (which captures cognitive mode) with domain-specific terms (which capture topic-level structure). The QLP-8 words are the forced set that TF-IDF would kill — they survive because they ARE the signal. Domain words add topography to the flat field, allowing formations to emerge around both how and what someone thinks.

When extending vocabulary, add words that are structurally important to the domain, not just common. "Excavation" in archaeology is not just a topic word — it implies a methodological stance (KO). "Reanalysis" implies a truth-seeking posture (TE). The best domain extensions map domain concepts to cognitive operations.

## Research

Based on: *Recursive Codebook Protocol: Compression as Relationship in Human-AI Communication*

- DOI: 10.5281/zenodo.18477225
- N=46, d_emotional=2.245, d_factual=1.036, p=6.95e-10
- Same-model control: Cold 1.9, Warm 8.7, Delta 6.7
- Cross-substrate: Claude, Gemini, Mistral
- Warm Decoder Delta (WDD) = score_warm - score_cold
- ~170 glyph saturation ceiling (exceeded in generative regime)
