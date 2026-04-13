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

---

## 2026-04-13 — Cycle 2

**Prerequisite file check:**
- `data/linear_b_corpus_sources.md` — still does not exist. Corpus source list not yet created.
- `data/functional_decipherment_research.md` — still does not exist. No prior findings document.

---

### 1. InsiderPhD tablets.csv — Schema Confirmed

Fetched raw CSV from `https://raw.githubusercontent.com/InsiderPhD/Linear-B-Dataset/master/tablet-sets/tablets.csv`.

**Columns:** `identifier`, `location`, `series`, `inscription`, `original`

**No explicit functional-type column.** However, the `series` code IS the functional proxy. Linear B series codes are standardized in the scholarship:
- Admin: `Ag` (personnel), `Ak` (personnel), `Am` (land), `Ap` (personnel), `Ar` (chariots), `As` (men/personnel), `B` (personnel lists), `Sq` (vessels/equipment)
- Cultic/religious: `Bg` (divine offerings), `C` (religious), `Gq` (dedications, e.g. to Dionysus)
- Unclassified: `X`

**Action:** Build a series→functional-type lookup table. This gives linafish labeled training data without any external tagging.

---

### 2. DAMOS Bulk Export — No Update

DAMOS subprojects page (`ub.uio.no/english/about/projects/damos/subprojects/`) shows no new bulk export, API, or EpiDoc release. Generic contact only: `ub-web@ub.uio.no`. Specific contact from Cycle 1 (`federico.aurora@ub.uio.no`) remains the best path. Status unchanged.

---

### 3. 2025 Ivory Scepter — Mixed-Register Discovery (HIGH RELEVANCE)

**Source:** Kanta, Nakassis, Palaima & Perna (2025). Knossos Anetaki excavation report.

Longest known Linear A inscription: ~119 signs on an ivory object (scepter or ritual staff) from the **Cult Center at Knossos**.

**Critical for linafish:** The object shows BOTH registers simultaneously:
- Scepter handle: administrative structure — includes numerical and fractional signs (classic bookkeeping markers)
- Ring portion: calligraphic refinement typical of ritual/ceremonial use; logograms for animals, vessels, textiles, hides

This is a real-world mixed-register artifact. It contradicts a clean admin/ritual binary and is exactly the kind of edge case the coupling engine needs to handle. The linafish model should flag this as ambiguous rather than forcing a category.

---

### 4. WSEAS 2025 Paper — Exists, Unread

"Enhancing a Software Platform for the Decipherment of Linear-A Inscriptions." WSEAS *Information Sciences and Applications* (2025), 9 pages. PDF only; binary parsing failed. Cited as evidence of active software tooling in this space. Follow-up: try to locate HTML version or author contact.

**URL:** `https://wseas.com/journals/isa/2025/a825109-020(2025).pdf`

---

### 5. SigLA — CC License Confirmed, No Bulk Download Visible

Dataset and drawings are CC BY-NC-SA 4.0 licensed. No download link on homepage. Contact: Ester Salgarella (Cambridge) and Simon Castellan (Univ. Rennes). The license explicitly allows non-commercial research use — bulk download is likely grantable on request.

**Action:** Email Salgarella directly asking for a TSV/CSV of sign-inscription mappings.

---

### 6. Computational Landscape — Still No Functional Competitors

Search over 2025–2026 literature confirms: all active computational work targets phonetic decipherment (what language is Minoan?) or sign identification. No papers apply functional template coupling or register-classification without phonetic knowledge. Linafish approach remains unoccupied.

One general statistic in wide circulation: Linear A corpus is ~60% economic/administrative records, ~25% religious texts. Source unclear (may be Wikipedia-laundered). Treat as approximate prior, not citable figure.

---

### Next cycle priorities
1. Email `federico.aurora@ub.uio.no` re: DAMOS bulk export (draft email text)
2. Email Ester Salgarella re: SigLA TSV export
3. Locate HTML/text version of WSEAS 2025 paper (try DOI resolver or author page)
4. Build series→functional-type lookup table for InsiderPhD dataset
5. Track down original source for the 60%/25% admin/religious split claim

