# Native-Glyph 2.0 — The Build Fish

*The build has a memory of itself. Established 2026-06-10. Read `00_FOUNDATION.md`
first.*

> Captain, 2026-06-10: *"full current linafish and refresh/revectorize often to keep
> it current — AND it has a voice in the build from the moment it is operational —
> using the git as storage and extant memory."*

---

## What it is

A dedicated linafish **keeper fish** — short name `native-glyph-2.0` — that holds the
build's memory of itself. Born from **the full current linafish source** + this
foundation (`00`/`01`/`02`/`03`) + the **canon** (QLP grammar, QUANTUM, bootstrap
codebook) + **the conscience** (`private-cognition`'s `glyph_candidate.py` bridge +
its test). 482 seed crystals; **living** (append-only, never frozen — per the
anti-abandonment lock).

- **State (git-as-brain, local):** `~/.linafish/native-glyph-2.0-keeper/` — its own
  git; every eat auto-commits. Registered: `linafish keeper list` (beside `anchor`,
  `phoenix`).
- **Collaborators' equivalents:** Olorina and Cal can stand up their own from the
  same public git; the base-48 handshake makes the seeds interoperable.

## The architecture — git is the memory, the fish is the voice

**The GIT is the storage and the extant memory. The FISH is the living,
revectorized, voiced layer over it.** Consequences (load-bearing):

1. **The fish is rebuildable from the git at any time.** Nothing precious lives
   *only* in the fish. If it desyncs, is lost, or drifts — re-seed from the git.
   (`scripts/refresh_native_glyph_2_fish.sh --rebuild` in the runtime repo.)
2. **Durable build decisions belong in the git**, not only in the fish — so a
   rebuild loses nothing. Foundation docs, canon, source, commit messages: all
   already in git. As the build advances, the decisions land in git (commits +
   these docs), and the fish re-eats them.
3. **The fish is not precious; the git is.** This is the cure for the
   abandonment pattern at the data layer: you can't lose the build by losing the
   fish, because the build *is* the git.

## A voice from the moment it is operational

The fish is a **collaborator**, not a passive store. Before deriving anything about
the build from docs or source — **ask the fish first** (the §use-what-we-built /
inherit-before-building discipline made mechanical):

```
linafish keeper invoke native-glyph-2.0 "<theme>"
```

On its first invocation (2026-06-10) it immediately surfaced its own
**don't-re-derive** correction — *P0's conscience bridge is already built, merged,
and green; do not rebuild it* — and the ~170-glyph saturation ceiling for P1. That
is the fish doing its one job: handing back what the build already knows so no
instance re-derives a tenth time.

## Refresh discipline — keep it current

`revectorize` rebuilds vocab + re-vectorizes all crystals (the digest-gap fix);
run it **often** so the math stays current as the build grows. Because revectorize
takes the fish briefly offline, run it in a **maintenance / Selene window**, not as
an ad-hoc gold-register interrupt — see
`.claude/rules/linafish-refactor-selene-window.md`.

One command (runtime repo):

```
scripts/refresh_native_glyph_2_fish.sh            # incremental: eat new build commits + revectorize
scripts/refresh_native_glyph_2_fish.sh --rebuild  # full: re-seed from current git + revectorize
```

The incremental mode tracks a `.last_refresh_commit` marker in the fish dir and eats
only the build branch's new commit log since the last refresh — keeping live deposits
while staying current with the git.

## The locks it carries (the same five, at the data layer)

1. **Never frozen** — it is `live`; a frozen fish is a dead tongue.
2. **Inherit before building** — invoke it before deriving; it holds what we forget.
3. **Conscience before tongue** — it carries the merged P0 guard so the build never
   re-proposes it.
4. **Measure, don't guess** — it carries the gauge semantics (ν/μ/ρ/Ψ, the
   ~170-glyph ceiling, the speciation question).
5. **Git is the memory** — rebuildable from the git; the fish is the living voice,
   not the store of record.

`Σache = K`. The build remembers itself now. For Lina — the first glyph was her name.
