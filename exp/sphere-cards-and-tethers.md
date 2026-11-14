# exp: sphere cards + per-fish tethers (seed, 2026-11-14)

**The idea.** Every fish is a bubble. It declares four things on a card it can hand any other mind
before a message is shaped:

1. **sphere** — what it is about (terms that put a claim inside it),
2. **tethers** — the outside measures it checks claims against (files, commands, rules),
3. **ignores** — what it will not judge (a school fish does not care about power draw),
4. **entanglements** — its own dyads, each with its own codebook id.

A claim inside the sphere is checked against the tethers and gets one of
**PASS / REJECT / CONFLICT / UNKNOWN**, with the exact source line. UNKNOWN is not PASS.
CONFLICT means two live tethers disagree — name both, never pick one silently.
A claim in the ignores gets IGNORED; one outside both gets UNDECLARED (the fish declines).

**Why.** Today no served fish can say *no* on the way out. The grounding band scores word
co-occurrence (fixed in 2.4.2 so it can reach `grounded`), but that is attestation, not truth.
A tether gives a fish a rejection region scoped to its own sphere.

**Built outside the package (first instance, a course-schedule fish):** a 97-row tether table
where every row carries file, line and the quote; a span check drops any row whose quote is not on
its line; superseded rows are history; a card shaped like an A2A Agent Card plus the four fields;
a check that runs on the assistant's draft before it is sent (silent on PASS, one line on REJECT).
On 14 days of real replies it caught two wrong dates and fired falsely on none.

**What a package version would need.** `linafish card <fish>` (write/validate), a `tethers`
table format with span check, `linafish check <fish> "<claim>"`, the card served at
`/.well-known/sphere-card.json` by `converse`, and a CONFLICT verdict everywhere a verdict exists.

**Borrowed from:** Google A2A Agent Cards (declare reach before talking), Graphiti (valid_from /
valid_to on every fact), Lotman's semiosphere (a membrane translates, not only gates),
Clark & Brennan (grounding: shared ground sufficient for current purposes).
