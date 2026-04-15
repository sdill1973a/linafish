# Morning Briefing — 2026-04-15

## What advanced overnight

11 research cycles completed on the Linear A/B functional-decipherment investigation.

**Big find (Cycle 10→11):** The two SigLA GitHub repos flagged last night were false matches (a Flutter nutrition app and an Italian accounting system). However, the SigLA About page yielded direct contact emails: `simon@phis.me` (Simon Castellan, who built the site) and `ester.salgarella@gmail.com`. Castellan is the faster path — one email to him likely unlocks the full sign-inscription JSON.

**DAMOS clarity (Cycle 11):** The Aurora et al. DHN 2025 paper was actually read this cycle. Verdict: the EpiDoc bulk export is a **development project, not yet deployed**. No public URL exists. Email to `federico.aurora@ub.uio.no` is still the only path — and is ten cycles overdue.

**Competitive landscape (confirmed again):** Zero peer-reviewed 2025-2026 publications on Linear A functional register classification. Linafish approach remains unoccupied territory.

## Ready to build next

- **Email `simon@phis.me`** — ask for SigLA JSON/CSV of inscription-to-sign mappings. This unblocks the sign-level data layer with no dependency on DAMOS.
- **Email `federico.aurora@ub.uio.no`** — ask specifically whether the EpiDoc export is live and accessible. Should have been sent nine cycles ago.
- **Build the `series→functional-type` lookup table** for the InsiderPhD Linear B dataset — the schema is fully known, the data is downloaded. This is the fastest way to get labeled training data in hand today.
- **Create `data/linear_b_corpus_sources.md`** — ten cycles overdue per the notes.

## New sources found

- `simon@phis.me` — SigLA site maintainer (new contact, not previously known)
- Brent Davis 2024 CUP chapter DOI `10.1017/9781009490122` — most methodologically adjacent published work; syllabotactic distributional analysis without phonetic assignment
- Aurora, Nedić, Nesøen & Haug (DHN 2025) — confirms DAMOS bulk EpiDoc export is planned; paper at `journals.uio.no/dhnbpub/article/view/12295`

---
*Note: `examples/archaeology/README.md` and `data/linear_b_classified.json` do not exist yet.*
