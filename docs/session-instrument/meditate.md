# `meditate` — the superthink verb

**Status:** design spec. Not implemented. The build follows.

## Idea

A `meditate` verb that **surfaces ("bubbles up")** relevant crystals and
formations from one or more fish and frames them as a meditation / superthink —
not a flat recall list. The fish is the voice; this makes the act of consulting
it a first-class tool.

It formalizes something that today is done by hand (reach for recall, surface
the relevant past material, reflect from what bubbles up) into a single verb
with knobs.

## Modifiers

- **content / theme** — what to meditate on (free text, e.g. "the path from
  here"). Drives the surfacing query.
- **time** — a window: recent, a date range, or **dormancy** — surface what's
  been quiet and is *re-touching* (the rediscovery / re-emergence signal). Ties
  to an objective time base + concept-dormancy tracking.
- **model scaling ("superthink")** — scale depth: a cheap fast pass for a quick
  surface, or a deeper pass (co-access walk, superglyph emergence, cross-fish
  synthesis) for a real superthink. Cost scales with depth, chosen explicitly;
  cheapest-capable by default. linafish stays model-agnostic, so the
  summarizer/scorer is a pluggable hook the caller provides.

## Why it matters — "zero faith involved"

The point: it surfaces **real** content from the fish — crystals, formations,
the warm-decoder material — **mechanically**. No performed reflection, no
confabulation, no "trust me." Anyone who installed linafish and grew a fish can
`meditate` it and get *their own* substrate bubbling up, with no belief required
that there's "something there." The fish either surfaces material or it doesn't;
the act is **verifiable, not faith-based.**

This is the warm-decoder thesis turned into a verb: the differential between
what a fish holds and what a cold reader sees, made queryable on demand.

## What it unifies

Today these are separate pieces: keeper-style voice-framed recall, flat
`recall` keyword search, `whisper` (unprompted signal), `emerge` (phase
classification), co-access / superglyph surfacing, the school fan-out.
`meditate` is the **one verb that orchestrates the bubble-up** across fish with
content / time / model knobs.

## Open questions for the build
- linafish-core verb (so every install gets it) vs a host-side skill wrapping
  the CLI? Leans core — "a tool everyone can use."
- How does model-scaling pick the model? linafish stays model-agnostic → a
  pluggable scorer/summarizer hook the caller supplies.
- Multi-fish ("your fish*es*"): surface across the school/corpus and synthesize,
  or one fish at a time with an `--across` flag?
- Output shape: a framed meditation (prose) vs ranked surfaced crystals vs both.

## Relationship to the session instrument
`meditate` and the open/close delta instrument are the same move — formalize an
implicit, faith-based ritual into a measurable, faith-free tool that reads the
fish's real measurements. See `open-close-delta.md` and `README.md`.
