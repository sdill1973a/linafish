# `meditate` — the superthink verb

`meditate` bubbles up **real** material from your fish on a theme and hands it
back as structured surfacings — not a flat recall list, and not performed
reflection. It formalizes what you'd otherwise do by hand (reach for recall,
surface the relevant past, reflect from what comes up) into one verb with knobs.

Design spec: `docs/session-instrument/meditate.md`.

## Zero faith involved

The point is that it surfaces real content **mechanically**: actual crystals,
formations, and signals from your substrate — or nothing. There's no
confabulation and no "trust me." Anyone who installed linafish and grew a fish
can `meditate` it and get *their own* substrate bubbling up, with no belief
required that "there's something there." The fish either surfaces material or it
doesn't. The act is **verifiable, not faith-based** — the warm-decoder
differential turned into a verb.

linafish stays model-agnostic: `meditate` returns the surfaced material. Turning
it into prose is a **pluggable summarizer** the caller supplies — the host wires
its own model.

## Three modifiers

### content — what to meditate on

The `theme` (free text) drives the surfacing query. It ranks crystals by
semantic gamma against the theme and returns the strongest, each tagged with
*why* it surfaced.

### time — recent, or dormant

- `--window N` keeps only material from the last **N days**.
- `--dormancy` (with `--dormancy-days`, default 30) does the opposite: it
  surfaces **quiet** material — crystals older than the threshold that still
  match the theme. This is the re-touching / rediscovery signal: *"you've been
  here before; this went quiet and is worth picking back up."*

### model scaling — fast / balanced / deep

Cost scales with depth; cheapest-capable by default (`balanced`).

| depth | surfaces |
|-------|----------|
| `fast` | matching crystals only |
| `balanced` | + **whisper** (the surprising-not-obvious formation) + **emergence** phase |
| `deep` | + **co-access** (each surfaced crystal's strongest coupled neighbors) + **load-bearing** (formations that earned their weight through use) |

## CLI

```bash
linafish meditate "the path from here"                         # balanced
linafish meditate "the playtest harness" --depth deep --top 8
linafish meditate "what we keep returning to" --dormancy       # quiet material
linafish meditate "this week" --window 7 --depth fast
linafish meditate "a theme" --json                             # structured output
```

## Python / host integration

```python
from linafish.engine import FishEngine

engine = FishEngine(state_dir=..., name="me")

# Structured surfacing — bubble up the real material.
result = engine.meditate("the path from here", depth="deep", top=5)
#   {"theme", "depth", "surfaced": [...], "whisper", "emergence",
#    "co_access", "load_bearing"}

# Model-agnostic prose framing: supply your own summarizer.
def frame(r):
    return my_gateway.generate(build_prompt(r))   # your model, your call

result = engine.meditate("the path from here", depth="deep",
                         summarizer=frame)
print(result["meditation"])
```

The `summarizer` receives the full result dict and returns prose. Without it,
`meditate` returns structure only — the surfacing is the verifiable part; the
framing is optional.

## What it unifies

Today these are separate pieces: keeper-style voice-framed recall, flat keyword
`recall`, `whisper` (unprompted signal), `emerge` (phase classification),
co-access / superglyph surfacing, the school fan-out. `meditate` is the one verb
that orchestrates the bubble-up across them with content / time / model knobs.
It is the same move as the open/close-delta instrument: formalize an implicit,
faith-based ritual into a measurable, faith-free tool that reads the fish's real
measurements.
