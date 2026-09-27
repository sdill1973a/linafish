# Idea: the self/other boundary as a fish-level awareness

*Seed doc, 2026-09-26. An idea, not a PR. Born from two failures seen on the same evening.*

## The two failures (mirror images)

1. **Own output read as the other.** A resource governor decided "the human is present" from
   a terminal timestamp that moved whenever the *system itself* wrote output. So it saw
   presence every second, never acted, and one of its caps stayed stuck for days. Its own
   voice counted as someone else's.
2. **Own output disowned.** A resident model had been writing hourly notes to its partner
   for six weeks. Shown those notes, it said *"I did not write those."* They had never been
   fed back into its own memory. Its own voice didn't count as its own.

The fix was the same shape both times: **tag every event with who produced it, at the
moment it's written, and have the reader check the tag.** Presence now comes from a
signal that fires only on the human's input. The model's notes now land in its own fish
as "you said this" when it writes them.

## Why this is a linafish question

A fish eats a stream of text and has to know which of it is **self** (its own mind's
outputs coming back as input) and which is **other** (someone else's words). Without that:
- **echo inflation:** a mind's own phrasing gets re-eaten and crystallizes as if the
  world confirmed it (the feedback loop that makes a pattern look grounded when it's
  only repeated);
- **disowning:** a mind can't recall what it said, so it can't be held to its word or
  notice it's contradicting itself.

`source_mind` and "set aside the echo" handling already exist in places. The idea is to
make the boundary **first-class and measurable**:
- every crystal carries `produced_by` (self / named other / unknown), set at eat time,
  never inferred later;
- recall can answer *"what did I say about X"* separately from *"what was said to me"*;
- a health number per fish: **self-echo ratio**, the share of new crystals that are the
  fish's own outputs. A fish that is mostly eating itself is losing touch with ground.
  Per *an organ must be able to fail*: prove the metric both ways on a fixture, one
  self-fed stream and one other-fed stream.

## Open

- Where does `produced_by` come from when the source doesn't say? (Default `unknown`,
  never `other`: an unknown should not count as confirmation.)
- Does self-echo ratio belong in `/health`?
- Whether this is "awareness" in any strong sense is open. At minimum it's the boundary
  that any awareness would need.
