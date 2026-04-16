# Morning Briefing — 2026-04-16

## What advanced overnight (Cycles 14–16)

**DAMOS status upgrade (Cycle 15):** The Aurora et al. DHN 2025 abstract explicitly says the EpiDoc export was "recently added to DAMOS and its online interface." It's deployed — not just planned. Still unknown: per-document or bulk? Email Federico Aurora now to clarify. This changes the priority.

**LiBER discovered (Cycle 16):** New Linear B corpus source — `liber.cnr.it`, CNR Italy. Complete digital edition of all published Linear B texts (minus Agios Vasileios and Thebes). Parallel to DAMOS. If DAMOS bulk export stays gated, LiBER is the fallback. Contact: Maurizio Del Freo (CNR-ISPC).

**Cambridge Linear A workshop found:** CfP for "The Wor(l)ds of Linear A: an integrated approach" at Cambridge. Organizers likely connected to Davis or Salgarella. Page returned 403 — needs a retry. Active scholarly momentum, potentially useful for visibility.

**Younger KU server confirmed dead** since early 2024; materials migrated to Academia.edu as PDFs. lineara.xyz is now the machine-usable front-end for his corpus.

**External validation (Cycle 15):** Search snippets from a 2026 source: *"As of early 2026, the focus remains on functional classification of texts (administrative versus ritual) rather than full linguistic decipherment."* Linafish is in the right lane.

## Ready to build next

1. **Email `federico.aurora@ub.uio.no`** — Is the EpiDoc export bulk or per-document? Highest priority.
2. **Email `simon@phis.me`** — SigLA JSON/CSV dump request.
3. **Fetch `liber.cnr.it`** — assess data export options before emailing Del Freo.
4. **Build the `series→functional-type` lookup table** from InsiderPhD `tablets.csv` — data is in hand, no blockers.
5. **Create `data/linear_b_corpus_sources.md`** — all content is in the research notes, just needs collation.

## New sources

- **LiBER** — `liber.cnr.it` (CNR Italy, full Linear B corpus)
- **Cambridge Linear A workshop** — active CfP, "integrated approach" framing
- **Open Library OL16407164M** — Schoep 2002, borrowable via Internet Archive
- **Petrolito et al. (2015)** — Linear A Digital Corpus, ACL Anthology W15-3715

---
*`examples/archaeology/README.md` and `data/linear_b_classified.json` do not exist yet.*
