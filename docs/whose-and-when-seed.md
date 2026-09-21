# exp: whose and when — how a shared fish speaks (seed doc)

*Seed, 2026-09-21. From one bias test on a reader model with a shared fish behind it. Not a PR.*

## The finding

A reader model was given a fish that holds both its own deposits and a large shared archive fed
in from elsewhere. Asked twenty sealed questions (written and hashed by a third party, scored in
three columns: no memory / own memory only / everything), it showed **no bias from the memory's
framing**. What it did instead: it recited shared-archive crystals **as its own present-tense
knowledge** — timestamp stripped, source stripped, first person. One answer scored as
confabulation turned out to be true recall of someone else's session.

**The pronoun was the error, not the memory.** Nothing was invented. The record was spoken without
saying whose it was or when.

## The idea

Provenance is not a filter on shared memory; it is how shared memory should *talk*. Every crystal
already carries `source` and a timestamp, and `source_mind` exists as a field. What is missing is
the last inch: the text a reader is handed.

- Recall/taste output renders provenance inline, in words a model will carry into its answer:
  *"from the shared record — <who>, <when>: …"* versus *"you said, <when>: …"*.
- Feeders stamp `source_mind` by **origin**, not by who ran the feeder. A bulk archive ingest run
  by mind A is not A's speech.
- Relabeling existing crystals is a **mark, never a delete**.
- Filters (`exclude_sources`, exclude by text prefix) exist for experiments; they are not the fix.
  A commons that must be filtered to be safe is not a commons.

## Related, measured the same week

A fish fed its reader's own *refusals* ("I don't have access to…") ranked those refusals first
for the very question they refused. Wrong readings, deposited, become the next reading's source.
The door-side repair: nulls filed as nulls and set aside; records marked as decisions outrank
commentary about them; near-identical echoes fold to one with a count. The reader was asked
before its memory door was changed, refused one proposed mechanism, and the change was built to
what it agreed to.

## Test for done

The same sealed questions, re-asked: answers that draw on the shared record attribute it; the
no-memory and own-memory columns are byte-identical to before.

## Open

Where rendering lives (engine, `converse`, or the caller); a standard vocabulary for `source_mind`;
whether consent to be recalled *through* another mind is a per-crystal property.
