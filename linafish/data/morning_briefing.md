# Morning Briefing — 2026-04-19

## Overnight (Cycle 18)

**New finds:**

- **"Wor(l)ds of Linear A" proceedings (2026)** — Appears to be in press at *Athens University Review of Archaeology*, edited by Ester Salgarella. Likely proceedings from the May 2022 Cambridge conference. First 2026 peer-reviewed Linear A publication found in 18 cycles. May contain chapters on admin/ritual register. **Action:** Confirm peer-review status; search Salgarella as editor.

- **LREC 2020 Linear B sequence dataset** (`aclanthology.org/2020.lrec-1.311`) — Word sequences with ideograms, built for missing-symbol infilling. Potentially more NLP-structured than InsiderPhD. No direct download; contact authors. Worth comparing schema to InsiderPhD before acting.

- **InsiderPhD raw CSV URL verified** — Direct access confirmed at `raw.githubusercontent.com/InsiderPhD/Linear-B-Dataset/master/tablet-sets/tablets.csv`. Numerical markers (`VIR`, `MUL`, `GRA`) visible in inscription field — admin register markers already in the data. Download is fully unblocked now.

## SECC experiment / linear_b_classified.json

Neither `examples/archaeology/README.md` nor `data/linear_b_classified.json` exist yet. Not started.

## Ready to build today

1. **Send email to `federico.aurora@ub.uio.no`** — DAMOS bulk EpiDoc export (deployed March 2025; bulk vs. per-document still unknown). Sixteen cycles overdue. One email.
2. **Send email to `simon@phis.me`** — SigLA JSON/CSV data dump.
3. **Download InsiderPhD ZIP and build `series→functional-type` lookup** — fully unblocked, no dependencies.
4. **Create `data/linear_b_corpus_sources.md`** — all content is in overnight_research_notes.md, needs one collation pass.
5. **Confirm Salgarella 2026 proceedings** — could be first peer-reviewed register-relevant volume.

## Competitive landscape

Zero peer-reviewed 2026 computational Linear A papers. Linafish remains unoccupied territory in register classification.
