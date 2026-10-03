# exp: spirals — find the earlier turns of an idea (seed doc)

*Seed, 2026-10-03. Runs today as an external job (`spiral_links.py`) over our own fish and archive. Not a PR.*

## The idea

People don't have new ideas as often as they think. An idea comes back months apart, in other words, and
usually the person doesn't notice. A fish already holds the earlier turns. Spirals asks the fish, when a new idea
lands: **where has this been before, in this person's own record, dated before today?** Then it hands those earlier
turns back.

That is the difference between storage and memory. Storage finds what you ask for. Memory notices that you have
been here before.

## How the running version works

1. **An idea arrives** as the person's own words, with a date and a few search phrases.
2. **Candidates, cheap and local:** the person's own-words fish (recall), older archives (grep), the whole archive
   (semantic search). **Only text dated before the idea counts.**
3. **A second mind judges** (a local model): which numbered candidates are really an earlier turn of the same idea,
   and which other ideas this one quietly links to. It is asked *what else is live*, never *is this right*.
4. **The gate:** the judge may only cite candidate numbers that exist, and every quote in the output is the source's
   own text, never the judge's. A pick outside the range is dropped and counted.
5. **A person checks every pick against its text** and marks it HOLDS, weak, or false. Output is a plain file per
   idea (`SPIRALS.md`), with the quotes, dates and sources.

## The part that makes it an organ rather than a loop

**"No earlier turn found" is a real outcome, not an error**, and it is written down. A spiral finder that always
finds an earlier turn is broken (it is matching common words). One that never finds one is broken (the door is
blind or the date filter is wrong). Both counts are published.

## Findings so far (2026-09-28 → 10-03, one person's record)

- First full pass: 23 ideas. Of the judge's picks, **48 held, 10 were weak, 20 were false** after a human read each
  one against its text. The false ones were mostly literal word matches ("spin" in a playlist). The human check is
  load-bearing; the judge alone would have shipped a 26 % false rate.
- **The best finds were invisible at the time.** Several ideas turned out to have an earlier turn months before,
  in a different project and different words, that nobody had connected. Those are the finds worth the whole tool.
- Dated archives matter. One era of the record has no timestamps (copied files), so "dated before" needs an
  era ceiling or the filter quietly admits later text.
- Separate the person's own words from assistant-written text in their archive. Both can be an earlier turn of
  *their world*, but only the first is an earlier turn of *their idea*. The output labels which is which.

## What it would be inside linafish

`linafish spiral "<the idea in their words>" --since <date> -n <fish>` → earlier turns with dates and verbatim
quotes, plus a "none found" line when that is the truth. A school-wide version asks every fish in the school.

Open:
- Where the human check lives in a tool (a `--review` pass that writes HOLDS/weak/false back?).
- Whether the judge is required. Recall alone over-matches; a judge without the citation gate invents.
- How the idea is captured: explicit (`spiral` verb) or automatic on `eat` when a crystal looks like a new idea.

Related: `exp/kin-links` (kin is *similar now*; a spiral is *the same idea, earlier*), `exp/whose-and-when`.
