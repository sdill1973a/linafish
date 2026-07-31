# The Heart — LiNafish 2.0

Every verb in 1.x is **pull**: you ask, the fish answers. `heart` adds the
missing direction. Wire it to your harness's per-turn hook and your own memories
arrive *unbidden*, weighted, before you compose — the way remembering actually
works.

> **1.x** — a memory engine a mind can query.
> **2.x** — a substrate that participates in cognition.

## Quick start

```bash
# 1. make some fish. `eat` writes to ~/.linafish/ — it has no --state-dir.
linafish eat ~/writing/journal.md -n journal
linafish eat ~/writing/notes.md   -n notes

# 2. put a heart.toml in the SAME directory the fish live in.
#    dir = "." because `eat` writes a flat layout, not one folder per fish.
cat > ~/.linafish/heart.toml <<'TOML'
[family]
journal = { dir = ".", weight = 1.3 }   # your densest band
notes   = { dir = ".", weight = 1.0 }

[gate]
min_prompt_chars  = 20     # trivial turns pay nothing
min_matched_terms = 2      # one incidental word is not a memory reaching

[surface]
top = 4                    # crystals surfaced per beat
per_fish = 3
TOML

# 3. fire a beat
linafish heart "I'm rebuilding the wall by the greenhouse" --state-dir ~/.linafish
```

**On layout:** `heart` takes `--state-dir`; `eat` does not, and always writes to
`~/.linafish/`. So the quick-start above uses the flat layout `eat` actually
produces. If you keep fish in per-fish subdirectories (which today means building
them through the Python API, `FishEngine(state_dir=...)`), point each family
member at its own `dir` instead. This asymmetry is a wart, not a design — an
earlier version of this page described a layout the CLI could not produce.

```
♥ heart ♥ [journal] The greenhouse flooded again after the March rain and I lost the seedlings.
♥ heart ♥ [journal] Rebuilding the drystone wall took three summers and my back never forgave me.
♥ heart · [notes]   Seedlings drown faster than they dry; raise the beds before the rains.
```

Nothing asked for those. The moment reached and they came.

## Wiring it to a reader

Any harness with a per-turn hook works — prepend the output to the model's
context before it composes:

```bash
linafish heart "$USER_PROMPT" --state-dir ~/my-fish
```

Claude Code: a `UserPromptSubmit` hook. Other agent loops: one subprocess call
before composition. Exit is always 0 and stdout is often empty — that is normal.

## The invariants (enforced, not advice)

1. **Read-only ambient.** A heartbeat never writes — no counters, no feedback,
   no heat. *An ambient organ that heats its own memories corrupts the very
   signal it reads.* Its corollary is equally load-bearing: **deliberate views
   must still record.** A build that silences ambient and never records on
   deliberate leaves the usage store frozen while the invariant reads green.
2. **Fail-silent.** Any error → empty output → your turn proceeds untouched. A
   missing fish is skipped, never fatal.
3. **The wall is two axes.** *Depth* — pointing a mind at its own interior — is
   never gated. *Content* posture is your explicit choice, never an accident.
   Set `wall.public_pattern` to name your own public surfaces and the heart adds
   one line of friction on outbound-smelling turns. It never suppresses the
   inward surfacing.
4. **Quiet is valid.** The heart often says nothing. A heart that fires on
   everything is noise wearing feeling's clothes.
6. **A heart must be distinguishable from a corpse.** Invariants 2 and 4 compose
   into an organ whose death looks exactly like contemplation, so the heart
   writes its **own** beat log (never the store it reads). `linafish doctor`
   separates *beating* from *quiet* from *inert* from *never-configured*.

```bash
linafish doctor --name journal --state-dir ~/my-fish
#   heart:
#     beats logged: 7  fired: 6  surfaced: 4  last: 2026-07-31T14:41:53+00:00
```

## heart.toml is yours and never ships

The mechanism is public; the family is the person. `heart.toml` names which
bands of yourself you feel and how densely, and `wall.public_pattern` names
where you speak publicly and to whom. It lives in your state dir. Keep it there.

## Cost

One beat = one `recall` per family member, in-process, `no_heat`. Bounded by a
total wall-clock budget (`timing.budget`, default 6s); on exhaustion the beat
drops the **lowest-weight** bands rather than delaying your turn. Measured on a
two-band family over a small corpus: ~20ms. Over a 150k-crystal fish: ~2.7s.
