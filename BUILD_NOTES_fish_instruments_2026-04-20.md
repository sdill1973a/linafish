# BUILD NOTES — fish instruments, 2026-04-20

Branch: `build/fish-instruments-2026-04-20`

## Purpose

Two measurement instruments that observe behavior already present in the fish, without changing persistence, vocab, or HTTP surface.

Both address specific items in the "ideas we're circling but haven't shipped" list:

1. **Glyph lifecycle monitor** — does the grimoire fade as designed? (mother-tongue burn-off measurement).
2. **Conservation check** — is Σache ≈ K across the corpus over time? (mathematical skeleton Gap 3).

Neither changes the fish. They read crystals and report.

## Scope (for this branch)

- Add `FishEngine.glyph_lifecycle_stats(bins=10)` → dict.
- Add `FishEngine.conservation_stats(bins=10)` → dict.
- Add CLI subcommand `linafish lifecycle --name <fish> [--state-dir ...] [--bins N]`.
- Add CLI subcommand `linafish conservation --name <fish> [--state-dir ...] [--bins N]`.
- Regression tests for both.
- No HTTP endpoints this pass (would be the next step after we see the shape of real output).
- No changes to engine behavior, persistence, or existing CLI.

## Why these two together in one branch

They share a motif — *instruments that measure what's already happening*. Both read the same crystal stream, bucket by order/time, and produce summary stats. Natural to ship together.

## Ship order in this branch

1. Glyph lifecycle (primary).
2. Conservation check (secondary; may slip to a follow-up commit).
3. Tests for both.
4. Doc: add section to README or a `docs/instruments.md`.

## What we *aren't* doing here

- No QLP metabolic-engine rewire (that's the v0.4 work, separate branch).
- No direction-vector (TOWARD/AWAY-FROM) on formations (different scope).
- No Keeper Protocol formalization (docs work, separate).
- No multi-mind formation detection (needs cross-corpus infra).

## Status

- [x] Branch created from master 2026-04-20.
- [ ] `glyph_lifecycle_stats` method.
- [ ] `linafish lifecycle` CLI.
- [ ] Tests.
- [ ] `conservation_stats` method.
- [ ] `linafish conservation` CLI.
- [ ] Tests.
- [ ] Push branch to origin (no PR yet — Captain review first).
