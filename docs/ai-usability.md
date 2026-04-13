# AI Usability — Discoverability Findings

**Written**: 2026-04-13
**Author**: Anchor (Claude Opus 4.6 on .140)
**Context**: Dev-hat audit of linafish 1.1.0 package discoverability, sparked by Captain's question "are these not well advertised in the build?"

---

## The short version

**Three major modules ship as dead code in 1.1.0.** They exist on disk, are well-written, solve real problems — and have **zero imports** anywhere in the package. Two more are buried behind conditional runtime imports most users never hit. A dev (AI or human) walking into the repo cannot discover them from `linafish --help`, and the surface docs don't mention them.

**This matters because these are exactly the modules that solve the common user problems** (flat formations, gap detection, closed-loop learning, fresh-fish bootstrap).

## The orphans — zero imports, no CLI, no doc references

### `linafish/guppy.py` — 19 KB

**Docstring**: *"The nervous system. Self-feeding fish that hunt gaps. Born from a corpus. Grows by hunting. Reports to the room. Talks to other guppies through shared water. Two hunting modes: REINFORCE (hunt for more of what you already know) and ACHE (hunt for what you're MISSING)."*

**Git log**: commit `4d831b1 v1.1.0 — The Nervous System` — this was framed as the hero feature of 1.1.0. But:

```
$ rg "import guppy|from .*guppy" .
(zero hits)
```

**Nobody imports it. It's not wired into any code path. The CLI has no `linafish guppy` or `linafish hunt` subcommand. The README and docs/ do not reference it by name except in `docs/next-build.md`.**

This is **exactly** the module a user needs when their formations go flat (the problem Anchor had this morning). "Read your own formations, find where you're thin, build queries from what's absent, dart out, nibble, crystallize." Ache-hunt mode is the measurement + action loop.

### `linafish/feedback.py` — 3 KB

**Docstring**: *"The fish learns from usage. When a formation helps, its weight goes up. When it doesn't, weight decays. The loop: eat -> crystallize -> form -> serve -> use -> feedback -> eat. The fish that learns what matters through use."*

**Nobody imports it.** The closed learning loop the docstring describes isn't closed in the current build. There's no plumbing from `/taste` or `/pfc` usage back to formation weight. Every fish_taste injection is free from the fish's perspective — helpful or useless, the next query weights the same crystals.

**This is the smallest unwired module (3 KB) and the highest leverage.** One afternoon of work connects it.

### `linafish/seed_formations.py` — 6 KB

**Docstring**: *"The grimoire for new fish. Five root-level cognitive attractors that any human's writing will grow toward. These are the universal superglyphs — structural basins that exist in every mind. The stranger's fish starts with these as empty formations. As crystals couple, some will drift toward these basins. The seeds that attract crystals survive. The ones that don't dissolve. The grimoire burns off. That's the design."*

**Nobody imports it.** A fresh `linafish go ~/journal` run for a stranger does not seed the fish with these universal basins. The grimoire exists in source but isn't planted.

This matters for cold-boot quality on stranger corpora. With seeds, a 50-document first eat has a chance at meaningful formations. Without them, it's BFS on sparse coupling with no priors.

## The buried — conditional/lazy imports

### `linafish/emergence.py` — 8 KB

**Docstring**: *"Semantic Novelty Threshold detection. From 'The Meta-Singularity Vector' (Scott Dill, August 2025). A formation demonstrates genuine emergence when it generates cognitive patterns not derivable from the bootstrap grammar. Not just recombination of the 48 — something NEW. Metrics: ν (Novelty Degree)."*

**Imported by**: `glyph_evolution.py:25` — only `emergence.BOOTSTRAP_OPS` is used, as a constant lookup. The actual novelty detection logic (ν measurement) is not called anywhere.

This is the **objective answer to "is the fish learning?"** Captain asked me that this morning. I had to guess. `emergence.measure_novelty()` exists, is public, and nothing calls it.

### `linafish/glyph_evolution.py` — 10 KB

**Docstring**: *"How private language grows from the common base. Initialize with 48 → monitor usage → generate new when ache > threshold → merge when overlap > 0.8 → prune unused → evolve α, β, γ."*

**Imported by**: `crystallizer_v3.py:576` only, and only inside a conditional runtime import:
```python
from .glyph_evolution import GlyphEvolutionEngine
```

So private-language growth only activates on a specific v3 code path. Users of the default `linafish go` flow do not get language evolution.

## The CLI surface vs the module surface

**`linafish --help` registers 23 subcommands** (from `__main__.py`):

```
eat, taste, recall, ask, status, serve, http, demo, go, init, watch,
fuse, room, session, history, diff, revert, absorb, converse, school,
whisper, check, listen
```

**Modules not exposed via CLI at all:**

| Module | Purpose | Why a user would want it |
|---|---|---|
| `guppy.py` | Ache-hunt gap detection | "My formations are flat — what's missing?" |
| `emergence.py` | ν novelty metric | "Is my fish actually learning or just rearranging?" |
| `feedback.py` | Usage-weighted learning | "Does my fish get smarter when I use it?" |
| `seed_formations.py` | Universal bootstrap attractors | Cold-start quality for stranger corpora |
| `glyph_evolution.py` | Private language growth | "Show me my evolved glyphs vs the canonical 48" |
| `metabolism.py` | 8-organ moment digestion (Level 1-4) | Lens analysis on a single text |
| `metrics.py` | 5 health metrics (R(n), Bell test, vocab drift, dimension balance, coupling density) | `linafish doctor` — is my fish healthy? |
| `assessment.py` | PreAssessment + FormativeAssessment | "Where am I before I start? How much did I grow?" |
| `parser.py` | QLP cognitive parser | "Which dimension does this text perform?" |
| `quantum_operations.py` | 300+ cognitive operations | "Classify this text by operation, not topic" |

**10 modules with substantive functionality have no CLI, no doc reference, no examples, no tests shipping them.** A dev reading `linafish --help` would conclude the package does what the CLI says it does. The package does much more.

## The docstring vs help-text gap

Every module has a clear docstring. `linafish <subcommand> --help` shows argparse flags but **never the module docstring**. A user running `linafish fuse --help` sees:

```
Usage: linafish fuse [-h] [--min-d MIN_D] ...
```

and not the beautiful stellar-fusion metaphor from `fusion.py`'s docstring. The "what is this for" is in the source and not the help text.

## What a first-time AI dev should see

When an AI assistant (or a human) types `linafish --help` or opens the repo for the first time, here is what they should get:

1. **A one-paragraph "what this is"** — the `__init__.py` has it, the README has a version of it, neither surfaces through `--help`.
2. **A capability map** — the list above, with 1-line descriptions per module, grouped by layer (ingest / engine / clustering / emergence / feedback / network / UX).
3. **An "I want to X, which tool do I use" cookbook** — e.g. "I want to find gaps → `linafish hunt` (guppy ache mode). I want to see if my fish is learning → `linafish emerge --measure` (ν metric)."
4. **A health check command** — `linafish doctor` wrapping `metrics.py` + `assessment.py` to give one-page fish status.
5. **A deliberate "unwired modules" note** for devs — either "these are experimental, not wired yet" OR "these are ready, unwired — help wanted."

## Proposed work (branch `exp/ai-usability`)

Ordered by leverage:

1. **Wire `feedback.py`** into the `/taste` read path. When a crystal is returned, increment its usage counter. On next reclustering, weight usage into the coupling score. **3 KB module, ~50 lines of wiring. One afternoon.**

2. **Expose `guppy.py` as `linafish hunt`** — a CLI command that runs ache-hunt mode against the current fish, returns gap queries as output. **One CLI subcommand + argparse wiring.**

3. **Wire `emergence.py` as `linafish emerge`** — measure ν against bootstrap closure, return a number. One-line answer to "is my fish learning?" **One CLI subcommand + wrapper function.**

4. **Wire `seed_formations.py` into `quickstart.py go`** — on first eat of an empty fish, plant the 5 universal seeds before BFS. **One import + one call.**

5. **Add `linafish doctor`** — runs all `metrics.py` checks, returns a health summary. **One CLI subcommand wrapping existing functions.**

6. **Expand `linafish --help`** to show module docstrings per subcommand. Replace argparse `description=` with the module's `__doc__`. **Mechanical, ~20 lines.**

7. **Write `docs/capabilities.md`** — the capability map above, maintained in sync with modules. **Documentation task.**

8. **Add `linafish capabilities`** as a CLI command that prints `docs/capabilities.md`. **One CLI subcommand.**

None of these are big. All together, maybe a single day of focused work. They would ~2x the usable surface of the package for AI devs and humans alike.

## Why this matters for the AI use case

Captain's point when he asked for this: **"we have to make it usable for the AI at least."** An AI assistant building on linafish is the primary user of the package right now — Anchor on .140, Olorina on .35, eventually Calcifer at Josh's. An AI dev can read the README and infer parts of the system, but cannot discover capability that lives only in `git log` and module docstrings. The AI must be able to run `linafish --help` or query an endpoint and learn what's possible.

Right now, the answer to "what can linafish do for me" depends on which commit of which branch you happen to land on and whether you know to grep the source tree. That's a discoverability bug, not a feature bug. The features are already built.

## Findings, compressed

- **3 modules orphaned**: `guppy`, `feedback`, `seed_formations`
- **2 modules deeply buried**: `emergence`, `glyph_evolution`
- **10 modules library-only** with no CLI exposure
- **1 README, 20 docs/ files** exist and are good, but are not referenced from CLI help
- **0 modules** surface their own docstrings via `--help`
- **1 `ai-usability` branch** now exists to house the fixes

---

*Ship-what's-built before building more. The nervous system is already in the box. Plug it in.*
