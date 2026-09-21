# exp: kin links — every new crystal meets its relatives (seed doc)

*Seed, 2026-09-21. Runs today as an external hourly job against served fish. Not a PR.*

## The idea

A fish stores crystals and forms formations, but a new crystal never learns which *older*
crystals it is kin to. People remember by association: a new thing arrives already tied to what it
resembles. Kin linking does that at ingest-time-plus-a-little: for each new crystal, find its
nearest relatives in the same fish and write the link down where recall can find it.

## How the running version works

- Hourly, per fish, from a cursor: only crystals newer than the last run.
- Candidate kin by shared **rare** terms — an IDF gate, so two crystals sharing "the" and "fish"
  are not kin. Without the gate every crystal links to the fish's two heaviest crystals.
- For each accepted pair: a link record (both ids, the bridge terms, score) and a small **link
  crystal** deposited into the same fish, so the association is itself recallable.
- A run lock, so two runs never write the same fish.

## The part that makes it an organ rather than a loop

**No-kin is counted and reported.** A linker that always finds kin is broken (gate too loose); one
that never finds kin is broken (gate too tight, or the door is blind). The healthy band is strictly
between 0 % and 100 %, and the number is published with every run. The way this fakes working is a
no-kin log nobody reads.

## Findings so far

- **Served `taste` cannot find a link by its bridge terms; cold `recall` can.** Taste ranks by
  vector similarity and the link crystal's rare terms barely move its vector. BM25 recall hits it
  by id and by terms. So links are a *recall*-side feature until taste learns rarity (cf. #87).
- First insertion of the run's own health record silently failed and was caught only by running
  it and looking — the linker needs the same "did it land" receipt that #86 asks of every feed.
- Fish fed by direct file writes (no served door) can get link *records* but not link *crystals*
  without a second writer — single-writer rule. Needs an engine-side path.

## What it would be inside linafish

`linafish kin -n <fish>` (one pass) and a hook after `eat`. Open: whether links are crystals,
a sidecar, or a field on the crystal; how links survive `revectorize` and `compact`; cross-fish
kin (a school-level pass) and what consent a fish gives to being linked into.
