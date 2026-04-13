# LiNafish Overnight Research Notes

---

## 2026-04-13 — Cycle 1

**Prerequisite file check:**
- `data/linear_b_corpus_sources.md` — does not exist yet. No prior source list to consult.
- `data/functional_decipherment_research.md` — does not exist yet. No prior findings to build on.

---

### 1. InsiderPhD Linear B Dataset (CSV)

**Repo:** `https://github.com/InsiderPhD/Linear-B-Dataset`

Confirmed exists. Structure:
- `character-sets/` — individual Linear B characters in CSV
- `word-sets/` — Linear B words in CSV
- `tablet-sets/tablets.csv` — tablet-level records
- CSVs are semicolon-delimited (not comma)
- Raw scrape data in `_raw-data/` from minoan.deaditerranean.com

**Download:** Available as ZIP archive via GitHub's Code > Download ZIP. Direct branch archive should work at the standard GitHub zip URL pattern for master branch.

**Caveat:** Repo appears dormant (last commit April 2018, 8 stars). Data sourced from a now-defunct scrape target. Useful for structural prototyping, but should be cross-checked against DAMOS or GORILA before treating as authoritative.

**Action needed:** Download the ZIP and check `tablets.csv` schema — specifically whether tablet functional type (admin/religious/other) is tagged.

---

### 2. DAMOS Database (Linear B, Oslo)

**URL:** `https://damos.hf.uio.no/`

Full corpus of published Mycenaean Linear B texts. Annotated relational DB (MariaDB backend). Supports word search and browse-by-site via GUI.

**Bulk export status:** No public API or download currently exposed. A sub-project is building EpiDoc XML export to integrate with Latin/Greek documentary corpora — status unknown, not yet publicly released. Contact for data requests: `federico.aurora@ub.uio.no`.

**Recommendation:** Email Federico Aurora directly. Ask specifically about: (a) EpiDoc export timeline, (b) whether a TSV/CSV snapshot can be shared for research use, (c) whether the MariaDB schema is documented anywhere.

---

### 3. New Computational Approaches to Linear A (2025–2026)

**Notable 2024 paper (most recent found):**
Nepal & Perono Cacciafoco, "Minoan Cryptanalysis: Computational Approaches to Deciphering Linear A and Assessing Its Connections with Language Families from the Mediterranean and the Black Sea Areas." MDPI *Information* 15(2):73.
- Method: visual feature-similarity between Linear A signs and Carian Alphabet / Cypriot Syllabary; consonant-cluster comparison against Ancient Egyptian, Luwian, Hittite, Proto-Celtic, Uralic
- Result: 43 phonetic-value matches generated; cross-language word matches insufficient to confirm any affiliation
- **Verdict for linafish:** Confirms the phonetic-decipherment approach keeps hitting walls. Functional pattern coupling is not what this paper does. Our method remains unoccupied territory.

**False positive flagged:** Frontiers in AI DOI `10.3389/frai.2025.1628943` (Aug 2025) appeared in Linear A search results but is entirely about neural-net gradient optimization. Unrelated.

**Active resources:**
- `lineara.xyz` — interactive Linear A corpus browser; ~1,860+ inscriptions from Hagia Triada (HT series), plus KH, PH, ZA sites. No bulk download visible, but good for manual exploration and regex search.
- SigLA (Signs of Linear A) — paleographic DB; 3,000+ individual signs from 400 inscriptions; standardized transcriptions. Launched 2020. Key enabler for computational sign-level analysis.

**Key observation:** Every 2024–2026 computational paper targets phonetic decipherment (which language is Minoan?). None apply functional template coupling across a deciphered/undeciphered script pair. The linafish approach — detecting administrative vs. ritual register without phonetic knowledge — has no direct competitor in the published literature as of this cycle.

---

### Next cycle priorities
1. Email DAMOS contact re: bulk export
2. Download InsiderPhD ZIP and inspect `tablets.csv` schema
3. Check if SigLA distributes a downloadable sign database or only a PDF
4. Search for any 2025–2026 work specifically on Linear A *register* or *functional* analysis (not decipherment)

