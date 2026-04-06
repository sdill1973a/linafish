# LiNafish Architecture

## Processing Pipeline

```
  Documents                  Crystals              Formations           Output
  ─────────                  ────────              ──────────           ──────

  .md .txt .pdf    ┌──────────────────┐   ┌────────────────┐   ┌──────────────┐
  .docx .json .py  │   CRYSTALLIZE    │   │     COUPLE     │   │     FORM     │
       │           │                  │   │                │   │              │
       ▼           │  text ──► tokens │   │  pairwise γ    │   │  BFS flood   │
  ┌─────────┐      │  tokens ──► 8d   │   │  (Jaccard on   │   │  fill on     │
  │ INGEST  │      │  vector (QLP)    │   │   8d vectors)  │   │  coupling    │
  │         │──────│  + keywords      │───│                │───│  graph       │
  │ extract │      │  + ache score    │   │  crystals with │   │              │
  │ chunk   │      │  = Crystal       │   │  γ > threshold │   │  min size    │
  │ detect  │      │                  │   │  get coupled   │   │  gate (≥2)   │
  └─────────┘      └──────────────────┘   └────────────────┘   └──────┬───────┘
                                                                      │
                      ┌───────────────────────────────────────────────┘
                      ▼
               ┌─────────────┐     ┌───────────────┐     ┌─────────────────┐
               │  PORTRAIT   │     │    SERVE      │     │     GROW        │
               │             │     │               │     │                 │
               │  formations │     │  HTTP /pfc    │     │  new text ──►   │
               │  ──► named  │     │  MCP tools:   │     │  re-crystallize │
               │  cognitive  │────►│   taste, eat, │────►│  re-couple      │
               │  patterns   │     │   pfc, health │     │  re-form        │
               │  ──► fish.md│     │   status      │     │  ──► fish grows │
               └─────────────┘     └───────────────┘     └─────────────────┘
```

## Overview

LiNafish is a cognitive profiling library. It reads a person's writing, measures _how_ they think across 8 dimensions, and produces a portable file (`fish.md`) that any LLM can read to understand that person's cognitive patterns.

The core insight: coupling measures cognitive architecture, not topic. Two texts about completely different subjects will couple if the author uses the same cognitive operations — the same ratio of feeling to structuring to testing. This is what makes the fish a portrait of the person rather than a summary of their topics.

Pure Python. No required dependencies. No GPU. No cloud. No account.

## Stage 1: Ingest

**Module:** `linafish/ingest.py`
**Role:** Read files and extract text chunks.

The ingest layer handles format-specific extraction:

| Format | Method |
|--------|--------|
| `.md`  | Split on headers. Each section becomes a chunk. |
| `.txt` | Split on blank lines (paragraph boundaries). |
| `.pdf` | Extract via `pdfplumber` if available, else skip. |
| `.docx`| Extract via `python-docx` if available, else skip. |
| `.json`| Extract string values recursively. |
| `.py`, `.js`, etc. | Extract docstrings and comments. |

Each chunk is a `Chunk` dataclass carrying the text, source path, section name, chunk type (narrative, data, code, metadata), and position within the source file.

Chunking is semantic, not mechanical. A markdown file splits at headers because that is where the author marked meaning boundaries. A 512-token sliding window does not know where meaning lives. Headers do.

**Key function:** `ingest_directory(path) -> list[Chunk]`

## Stage 2: Crystallize

**Module:** `linafish/crystallizer.py` (keyword-based, v1) and `linafish/crystallizer_v3.py` (MI-based, v3)
**Role:** Compress each text into an 8-dimensional cognitive signature.

The engine currently uses v3 (`crystallizer_v3.py`) by default. The v1 crystallizer (`crystallizer.py`) is retained for comparison and as a fallback.

### The 8 Dimensions (QLP-8)

| Code | Name | What it measures |
|------|------|-----------------|
| KO | Knowing | Generating, synthesizing, analyzing, extracting |
| TE | Testing | Verifying, validating, measuring, predicting |
| SF | Structuring | Organizing, connecting, framing hierarchies |
| CR | Relating | Contextualizing, bridging, relating to time/place/people |
| IC | Wanting | Feeling, desiring, grieving, hoping, needing |
| DE | Specializing | Domain-specific technical/scientific/philosophical depth |
| EW | Acting | Executing, building, deploying, doing physical work |
| AI | Reflecting | Meta-cognition, learning about learning, self-awareness |

### v1 Vectorization (keyword TF-IDF)

1. Tokenize text into lowercase alpha tokens.
2. For each dimension, count keyword hits from a curated vocabulary (~30-50 terms per dimension).
3. Score = `density * 0.6 + coverage * 0.4`, where density is hit frequency and coverage is vocabulary breadth.
4. Normalize so the maximum dimension scores 1.0.

Result: an 8-element float vector. Deterministic. Reproducible. No model weights.

### v3 Vectorization (mutual information)

1. Build a corpus-wide co-occurrence matrix.
2. Compute mutual information between each term and each cognitive dimension using a canonical seed grammar (8 dimensions x ~10 seed terms).
3. The MI vectorizer learns a vocabulary specific to the corpus — personal vocabulary, not a fixed keyword list.
4. Crystals get both an `mi_vector` (full vocabulary length) and a `resonance` vector (reduced via PCA to `d^2 - 1` dimensions).

The canonical seed grammar ("the grimoire") bootstraps new corpora. As R(n) grows with more exchanges, corpus-specific terms displace the seeds. The grimoire fades by design.

### Crystal Data Structure

```python
@dataclass
class Crystal:
    id: str                    # SHA-based hash
    ts: str                    # ISO timestamp
    text: str                  # source text (truncated to ~300 chars)
    source: str                # file path or label
    resonance: List[float]     # 8d cognitive vector
    keywords: List[str]        # top 5 domain terms
    couplings: List[Tuple[str, float]]  # [(crystal_id, gamma)]
    structural: bool           # long-lived (True) vs ephemeral (False)
    formation: Optional[str]   # assigned formation name
    ache: float                # compression loss score
```

### Ache

Every crystal carries an `ache` score measuring compression loss:

```
ache = 0.40 * cycles + 0.30 * misses + 0.30 * depth_variance
```

- **cycles**: text length / keyword density (how much was compressed)
- **misses**: fraction of dimensions near zero (blind spots)
- **depth_variance**: unevenness of the resonance vector (specialist vs generalist)

Ache is fuel, not error. High ache means the text had more to say than the crystal could capture.

## Stage 3: Couple

**Module:** `linafish/crystallizer.py` (`couple_crystals`, `gamma_coefficient`)
**Role:** Compare crystals pairwise and link those with similar cognitive architecture.

### Gamma Coefficient

The primary coupling metric is a Jaccard-style overlap on the 8-dimensional vectors:

```
gamma(a, b) = sum(min(a_i, b_i)) / sum(max(a_i, b_i))
```

Range: [0, 1]. Two crystals with identical cognitive profiles score 1.0. Two with no dimensional overlap score 0.0.

A secondary cosine similarity check catches directional similarity that gamma misses — texts that point the same cognitive direction but at different magnitudes.

### Adaptive Threshold

The gamma threshold is not hardcoded. `adaptive_gamma()` samples random pairs from the corpus, measures the density distribution, and picks a threshold that keeps coupling at a target percentage (default: top ~15% of pairs). This prevents both under-coupling (sparse corpora) and over-coupling (dense corpora).

Default starting threshold: 0.45. Adjusted up for dense corpora, down for sparse ones.

### Coupling is the Key Operation

This is where topic drops out and cognitive habit remains. A journal entry about grief (high IC, high CR) and a journal entry about gardening (high IC, high EW) will couple if both show the same pattern of turning feeling into action. The _what_ differs. The _how_ matches. That match is the coupling.

Uses numpy when available for vectorized pairwise computation. Falls back to pure Python with identical results.

## Stage 4: Form

**Module:** `linafish/formations.py`
**Role:** Discover formations — recurring cognitive patterns — from the coupling graph.

### Algorithm

1. **Fission**: If any connected component exceeds 15% of the total crystal count, cut weak links (bottom 30th percentile of gamma within that component) and re-flood. This prevents mega-formations that say nothing.

2. **BFS flood fill**: Treat crystals as nodes and couplings as edges. Run breadth-first search to find connected components. Each component is a candidate formation.

3. **Minimum size gate**: Components with fewer than 2 crystals are discarded. Single crystals are noise or one-offs — formations represent _habits_, which require repetition.

4. **Naming**: Each formation is named from its cognitive signature, not its keywords. The top 2-3 cognitive dimensions form the name: `ACTING+RELATING_via_FEELING`. This names what the person _does_ cognitively, not what they write about.

5. **Theme keywords**: The top 5 keywords across all member crystals are collected for human readability, but the name comes from the dimensions.

### Formation Data Structure

```python
@dataclass
class Formation:
    name: str                     # e.g. "ACTING+RELATING_via_FEELING"
    crystals: List[Crystal]       # member crystals
    cognitive_centroid: List[float]  # average 8d vector across members
    theme_keywords: List[str]     # most common keywords
    size: int                     # crystal count
```

### Shuffle Invariance

Formations are deterministic given the same input. The coupling graph depends only on pairwise gamma values, which are commutative. BFS finds the same connected components regardless of traversal order. Verified experimentally: same formations across 7 randomized input orderings, with only naming tie-breaks varying (from `Counter.most_common` ties).

## Stage 5: Portrait

**Module:** `linafish/engine.py` (`FishEngine.pfc()`, fish.md rendering)
**Role:** Render formations into a human-readable, AI-readable file.

The `fish.md` file is the output artifact. Structure:

```markdown
# [name].fish.md
*N crystals. M formations. Last fed: [timestamp].*

## Formations

**ACTING+RELATING_via_FEELING** (12 crystals)
  Dominant: EW (Acting), CR (Relating), IC (Feeling)
  Theme: work, garden, mother, morning, quiet
  This person habitually turns emotion into physical action
  and tests whether the action landed in relationship.

**KNOWING+TESTING_via_STRUCTURING** (8 crystals)
  ...

## AI Overlay Instructions
[Instructions for any LLM reading this file]

<!-- STATE (machine-readable JSON below this line) -->
```

The file is simultaneously:
- **Human-readable**: anyone can open it and understand the person's cognitive patterns.
- **AI-readable**: any LLM that reads it at session start arrives "warm" — knowing how the person thinks, not just what they have said.
- **Git-versionable**: every change is committed. The fish has a history.

The `pfc()` method returns the formations section as a string, suitable for injection into an AI's context window.

## Stage 6: Serve

**Modules:** `linafish/http_server.py`, `linafish/server.py`
**Role:** Expose the fish over HTTP or MCP for live AI integration.

### HTTP Server (`http_server.py`)

Stdlib-only HTTP server. Zero dependencies.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/pfc` | GET | Formations as text (the metacognitive overlay) |
| `/boot` | GET | AI primer + formations (full warm-boot payload) |
| `/health` | GET | Engine stats as JSON |
| `/eat` | POST | Feed text: `{"text": "...", "source": "..."}` |
| `/taste` | POST | Cross-corpus match: `{"text": "...", "top": 5}` |
| `/match` | POST | Tight recall (higher threshold than taste) |
| `/fish` | GET | Raw fish.md contents |

### MCP Server (`server.py`)

Stdio-based MCP (Model Context Protocol) server for Claude Code integration. Exposes 5 tools:

| Tool | Description |
|------|-------------|
| `fish_pfc` | Get the metacognitive overlay |
| `fish_eat` | Feed new content |
| `fish_taste` | Cross-corpus matching (looser threshold) |
| `fish_match` | Tight recall (stricter threshold) |
| `fish_health` | Engine statistics |

Both servers wrap the same `FishEngine` instance.

## Stage 7: Grow

**Module:** `linafish/engine.py` (`FishEngine.eat()`, `FishEngine.eat_path()`)
**Role:** Incremental learning. The fish deepens over time.

When new text is fed to the engine:

1. The text is crystallized against the current vocabulary.
2. The new crystal is coupled against all existing crystals.
3. Formations are recomputed (full BFS, not incremental patching).
4. The fish.md file is regenerated and git-committed.

The vocabulary itself can evolve. The v3 engine tracks co-occurrence statistics across all ingested text. When the corpus grows, the MI vectorizer can be retrained (a "re-eat" cycle), which may shift which terms are most informative. Terms that were distinctive early on may become common; new terms may emerge as distinctive.

### Assessment Integration

The engine optionally integrates an RTI-parallel assessment layer:

- **Pre-assessment**: Before first ingestion, screen the corpus to set the intimacy parameter `d` (warm/blend/stranger) and per-term seed weights. Analogous to universal screening in education.
- **Formative assessment**: At each re-eat cycle, compare current state to the last snapshot. What formations survived? What dissolved? What emerged? Adjust seed weights accordingly. The re-eat _is_ the formative assessment — same operation, two lenses.

## Module Map

```
linafish/
├── __init__.py          # Exports: FishEngine, go
├── __main__.py          # CLI entry point
├── engine.py            # FishEngine — the core orchestrator
├── crystallizer.py      # v1 crystallizer (keyword TF-IDF)
├── crystallizer_v3.py   # v3 crystallizer (MI x ache, no keywords)
├── formations.py        # Formation detection (BFS on coupling graph)
├── formations_v3.py     # v3 formation detection
├── ingest.py            # File reading and chunking
├── server.py            # MCP server (stdio)
├── http_server.py       # HTTP server (stdlib)
├── assessment.py        # RTI-parallel pre/formative assessment
├── quickstart.py        # `linafish go` one-command entry
├── codebook.py          # Codebook rendering utilities
├── compress.py          # Compression utilities
├── eat.py               # Eat command implementation
├── feedback.py          # Learning feedback loop
├── metrics.py           # R(n) and statistical measures
├── parser.py            # QLP grammar parser
└── data/
    └── ai_primer.md     # Instructions for any LLM reading a fish
```

## Design Decisions

**TF-IDF over neural embeddings.** The 8-dimensional vector is computed by counting keyword hits against a curated vocabulary. This means: no GPU, no model download, no API call, deterministic output, reproducible results across machines. The tradeoff is lower semantic coverage — the vocabulary must be extended for new domains. The `extend_vocabulary()` function handles this explicitly.

**Local files over databases.** All state lives in `~/.linafish/` as JSON, JSONL, and markdown files. No SQLite. No cloud sync. No account creation. The fish.md file is the primary artifact — if you lose everything else, the fish.md still teaches an AI who you are.

**fish.md is the interface.** The output file is simultaneously documentation, data, and API. A human reads the formations section. An AI reads the overlay instructions. Git versions the changes. There is no separate "export" step — the fish.md _is_ the export.

**Coupling on cognitive dimensions, not topics.** This is the central design choice. Two texts couple when they share cognitive architecture (the same ratio of knowing to feeling to acting), regardless of subject matter. This produces a portrait of _how someone thinks_, not a topic model of _what they write about_.

**Shuffle invariance.** The pipeline produces the same formations regardless of document input order. Gamma is commutative. BFS finds the same connected components regardless of traversal starting point. The only variance is in formation _naming_ when keyword frequency ties occur (Counter.most_common tie-breaking is insertion-order dependent). Formation membership is stable.

**Pure Python with optional acceleration.** Numpy is used when available for vectorized pairwise gamma computation (`couple_crystals`). Without numpy, the same computation runs in pure Python nested loops. Results are identical. Performance differs: numpy matters at >1000 crystals.

**The grimoire fades.** The canonical seed vocabulary bootstraps new corpora but is designed to be displaced as the corpus develops its own distinctive terms. A fish that has ingested 500 documents uses mostly corpus-learned vocabulary. A fish with 5 documents relies heavily on the seeds. This is intentional — the system adapts to the person, not the other way around.
