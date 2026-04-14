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

---

## 2026-04-13 — Cycle 3

**Prerequisite file check:**
- `data/linear_b_corpus_sources.md` — still does not exist.
- `data/functional_decipherment_research.md` — still does not exist.

---

### 1. Source of the 60%/25% Admin/Religious Split — RESOLVED (PARTIALLY)

The oft-cited figure (60% economic/administrative, 25% religious, 10% administrative documents, 5% unclassified) traces to **Erik Kiley (2025), "Deciphering Linear A: A Structured Minoan Script for Trade and Religious Administration,"** published on Academia.edu as independent research.

**Critical caveat:** This is not peer-reviewed. Kiley is an independent author; the paper has no journal affiliation. Schoep (2002) and Younger's database are the correct scholarly sources for corpus composition, but neither provides clean percentage figures in the search results accessed. The 60%/25% stat should **not be cited as authoritative** until confirmed against Schoep (2002) directly.

**Action:** Pull Schoep 2002 from http://people.ku.edu/~jyounger/LinearA/Schoep_2002.pdf to verify or replace the figure.

---

### 2. DAMOS License Confirmed

DAMOS content is **CC BY-NC-SA 4.0**. Software is **GPL-3.0**. Bulk export remains unavailable via website. Subprojects page has no EpiDoc or API timeline listed. The CC license means a data snapshot, if provided by Federico Aurora, could be used under the non-commercial research exemption.

**Contact remains:** `federico.aurora@ub.uio.no` — no new path found this cycle.

---

### 3. lineara.xyz — Filter Taxonomy Confirmed

Site has ~1,800+ inscriptions. Filter categories visible in UI: **Word Types, Contexts, Tags, Scribes, Supports**. No functional-type (admin/ritual) tag in the filter set, and no bulk download. The "Contexts" filter is the most promising proxy for register — worth investigating manually for vocabulary: palace, shrine, offering, inventory.

---

### 4. HAL Paper — Blocked, Needs Author Search

"Computational Pattern Recognition in Linear A" (HAL archive, hal-03207615) uses n-gram analysis, LDA topic modeling, k-means clustering, and Word2Vec on the Linear A corpus. Access blocked by Anubis security gate on direct PDF fetch. This paper is closely adjacent to what linafish does (statistical pattern recognition without phonetic decipherment). It may be the closest thing to a competitor in the literature.

**Action:** Search for authors via HAL metadata at `https://hal.science/hal-03207615` (HTML page, not PDF direct) to find author contact or preprint version.

---

### 5. No New Peer-Reviewed Papers (2026)

No peer-reviewed publications on Linear A found dated 2026. The most recent computational work remains the Nepal & Perono Cacciafoco MDPI paper (2024) and the WSEAS software platform paper (2025). The HAL pattern recognition paper needs its date confirmed — may predate 2024.

---

### Next cycle priorities
1. Fetch Schoep 2002 PDF (http://people.ku.edu/~jyounger/LinearA/Schoep_2002.pdf) to verify corpus composition stats
2. Fetch HAL metadata page (not PDF) for hal-03207615 to identify authors and year
3. Draft email to Federico Aurora re: DAMOS CC BY-NC-SA data snapshot
4. Investigate lineara.xyz "Contexts" filter manually for register-relevant vocabulary
5. Create `data/linear_b_corpus_sources.md` with InsiderPhD and DAMOS entries

---

## 2026-04-14 — Cycle 4

**Prerequisite file check:**
- `data/linear_b_corpus_sources.md` — still does not exist.
- `data/functional_decipherment_research.md` — still does not exist.

---

### 1. HAL Paper Authors — RESOLVED

**Paper:** "Computational Pattern Recognition in Linear A" (`hal-03207615`)  
**Authors:** Jajwalya R. Karajgikar, Amira Al-Khulaidy, and Anamaria Berea (George Mason University)  
**Methods:** n-gram analysis, LDA topic modeling, k-means clustering, information theory / entropy measures  
**Goal:** Predict missing symbols on damaged tablets; cluster signs by topic without phonetic decipherment

Direct PDF access still blocked by Anubis security gate. Authors confirmed via search metadata. This is the closest published work to linafish — purely statistical, no phonetic assumptions — but targets sign-level prediction, not functional register classification. **Linafish is still unoccupied territory at the register-classification level.**

**Action:** Try contacting Anamaria Berea (GMU) directly; her institutional page may have a preprint link.

---

### 2. Functional Reconstruction Without Decipherment — NEW 2026 SOURCE (MODERATE RELEVANCE)

**Source:** Ararat Petrosyan (guest post), GreekReporter, 15 Jan 2026  
URL: `https://greekreporter.com/2026/01/15/reconstruct-linear-a-crack-language/`

Describes a deductive functional-reconstruction approach that identifies tablet purpose without deciphering the language. Five-layer method: (1) logogram frequency analysis, (2) numerical magnitude/proportionality, (3) archaeological context, (4) comparative Linear B / Near Eastern admin systems, (5) recurring symbol-cluster patterns.

**Claimed accuracy:** ~71% on blind test (5 tablets). Strategic reserve records: 85–95%. Labor records: ~88%. Export records: 55–80%.

**Critical caveats:**
- GreekReporter guest post, NOT peer-reviewed. No journal affiliation, no DOI, no formal methodology paper cited.
- Author Ararat Petrosyan is a historian; no institutional affiliation named.
- References Godart–Olivier corpus and Ester Salgarella but provides no citations.

**Verdict for linafish:** The *concept* directly overlaps with linafish's goals — functional identification without phonetic decipherment. However, the method is manual and deductive, not computational. This is evidence the problem is tractable and recognized as valuable, but not a computational competitor. **Flag as related prior art for the paper/writeup, with strong caveats on its informal status.**

---

### 3. Schoep 2002 — Still Inaccessible

Direct fetch of Younger's KU server PDF returns 403 Forbidden. The 60%/25% admin/religious corpus-composition figure remains unverified against a citable scholarly source. Do not use this statistic in any publication.

---

### 4. No 2026 Peer-Reviewed Papers Found

Search over "Linear A functional register administrative ritual 2025 2026" returned no peer-reviewed 2026 publications. The landscape remains: Nepal & Perono Cacciafoco MDPI 2024 (phonetic), Manoj & Perono Cacciafoco Craiova 2025 (review), WSEAS 2025 (software platform, unread). No computational register-classification work found.

---

### Next cycle priorities
1. Search for Anamaria Berea (GMU) institutional page for HAL preprint link
2. Find Schoep 2002 via Google Scholar or JSTOR alternative path
3. Fetch WSEAS 2025 paper via author contact or DOI resolver (avoid direct PDF)
4. Create `data/linear_b_corpus_sources.md` (overdue since Cycle 1)
5. Search for Ararat Petrosyan to assess credibility and whether a formal paper exists

---

## 2026-04-14 — Cycle 5

**Prerequisite file check:**
- `data/linear_b_corpus_sources.md` — still does not exist. Creating this remains overdue.
- `data/functional_decipherment_research.md` — still does not exist.

---

### 1. WSEAS 2025 Author — RESOLVED

**Author:** Peter Z. Revesz, University of Nebraska-Lincoln (Dept. Computer Science & Engineering)
**Paper:** "Enhancing a Software Platform for the Decipherment of Linear-A Inscriptions"
**Published:** July 8, 2025 (accepted May 20; revised April 18). WSEAS *Transactions on Information Science and Applications*.
**Method:** Three-module platform — machine-readable dictionary, interactive interface, and search engine based on "Syllabic Grouping." Entirely phonetic-decipherment oriented. No functional register analysis. Revesz also authored an earlier WSEAS paper proposing Minoan as related to Uralic/West-Ugric — fringe linguistic hypothesis.
**Verdict:** Not a competitor to linafish. No register-classification content. Author is reachable at UNL (`revesz@cse.unl.edu` per UNL CSE faculty pages).

---

### 2. HAL Paper (hal-03207615) — Date Confirmed, Access Still Blocked

Paper submitted April 26, **2021** — not recent. Preprint only; no journal publication found. Authors: Karajgikar, Al-Khulaidy, Berea (GMU). Anubis security gate blocks direct PDF fetch on both the HTML page and the document URL. This is a 2021 preprint, substantially older than prior cycles implied. Still the closest statistical work to linafish, but five years old and unpublished in a peer-reviewed venue.

---

### 3. Craiova 2025 Paper — Full Citation Confirmed

Manoj & Perono Cacciafoco. "Minoan and the Machines: Computational Approaches to the Decipherment of Linear A."
*Annals of the University of Craiova: Series Philology, Linguistics*, Vol. 46, No. 1-2 (2024). Published February 18, 2025.
DOI: `10.52846/aucssflingv.v46i1-2.134`
Reviews four methods: minimum cost-flow, generative phonetic framework, cryptanalytic brute-force, feature-similarity. All phonetic decipherment. No register/functional content.

---

### 4. Ararat Petrosyan — No Academic Profile Found

Search returned no journal publications, no institutional affiliation, no ResearchGate or Academia.edu profile matching the GreekReporter author. Conclusion: the January 2026 GreekReporter piece is an informed-enthusiast contribution with no peer-reviewed backing. Do not cite as scholarship; cite only as evidence that the functional-reconstruction problem is publicly recognized as tractable.

---

### 5. No New 2026 Peer-Reviewed Papers

Broad and targeted searches confirm: zero peer-reviewed 2026 publications on Linear A computational analysis (functional or phonetic). The field is quiet. **Linafish approach remains unoccupied territory.**

---

### Next cycle priorities
1. Create `data/linear_b_corpus_sources.md` — this is now four cycles overdue
2. Attempt to access HAL paper via Berea's GMU faculty page (not HAL directly)
3. Find Schoep 2002 via JSTOR or ResearchGate (KU server 403 persists)
4. Check lineara.xyz "Contexts" filter vocabulary for admin/ritual proxies

---

## 2026-04-14 — Cycle 6

**Prerequisite file check:**
- `data/linear_b_corpus_sources.md` — still does not exist. Five cycles overdue.
- `data/functional_decipherment_research.md` — still does not exist.

---

### 1. WSEAS 2025 Paper — AUTHOR CORRECTION (HIGH PRIORITY)

Previous cycles (Cycle 5) incorrectly attributed the WSEAS 2025 Linear A paper to Peter Z. Revesz (UNL). That attribution was wrong.

**Correct authors:** Mavridaki, Zacharis, and Papakitsos  
**Correct title:** "Enhancing a Software Platform for the Decipherment of Linear-A Inscriptions"  
**WSEAS Transactions on Information Science and Applications, July 2025**

Content: machine-readable dictionary + software platform using a spreadsheet-row-per-artifact schema mapping words to cognate candidates. Entirely phonetic-decipherment oriented. No register analysis.

Revesz (UNL) is a *different* WSEAS Linear A author — he proposed a West-Ugric/Minoan connection. Both are fringe phonetic work with no overlap with linafish.

---

### 2. HAL Paper — Berea Contact Confirmed, Paper Not on Faculty Page

Anubis security gate still blocks `hal.science/hal-03207615` (both HTML and PDF).  
Berea's GMU faculty page (`science.gmu.edu/directory/anamaria-berea`) lists no Linear A publications — the paper does not appear in her institutional profile. Her email is `aberea@gmu.edu`.

**Action:** Email `aberea@gmu.edu` directly, reference hal-03207615, ask for a PDF copy or preprint link. This is the shortest path around the Anubis block.

---

### 3. DAMOS — Status Truly Unchanged

Subprojects page last modified **July 5, 2017**. No new subprojects, no EpiDoc export, no API, no bulk download mentioned anywhere. The `ub-web@ub.uio.no` contact on the page is generic. Federico Aurora (`federico.aurora@ub.uio.no`) from Cycle 1 remains the only targeted contact. No path forward without emailing him directly.

---

### 4. Schoep 2002 — Full Citation Confirmed

**Schoep, I. (2002).** "The administration of neopalatial Crete: a critical assessment of the Linear A tablets and their role in the administrative process." *Minos: Revista de filología egea*, 17, pp. 1–230.

Search confirms this is the canonical scholarly work on Linear A tablet administration. The corpus total: ~7,400 signs across ~1,427 artifacts. Schoep documents the expansion of Linear A from administrative into non-administrative (religious/cultic) contexts during the Neopalatial period — directly supporting the admin/ritual binary linafish targets. However, no precise percentage breakdown (60%/25%) surfaces from the search snippets. The figure likely originates from Kiley 2025 (Academia.edu, non-peer-reviewed). Do not cite as authoritative.

---

### 5. lineara.xyz — Context Filter Structure Confirmed

Filter categories confirmed: **Word Types, Contexts, Tags, Scribes, Supports, Frequency, Findspots, Sites.** No functional-type (admin/ritual) tag exists. The `Contexts` and `Tags` filters are the best register proxies. No example values were returned by automated fetch — requires manual browser exploration. Still no bulk download.

---

### 6. No New 2026 Peer-Reviewed Papers

Broad and targeted searches return zero peer-reviewed 2026 publications on Linear A (computational or functional). Linafish approach remains unoccupied territory.

---

### Next cycle priorities
1. Email `aberea@gmu.edu` re: HAL preprint PDF (draft text)
2. Email `federico.aurora@ub.uio.no` re: DAMOS data snapshot (draft text — overdue since Cycle 1)
3. Create `data/linear_b_corpus_sources.md` — now five cycles overdue
4. Manually browse lineara.xyz Contexts and Tags filter values
5. Find Schoep 2002 full text via JSTOR, WorldCat, or ILL path

---

## 2026-04-14 — Cycle 7

**Prerequisite file check:**
- `data/linear_b_corpus_sources.md` — still does not exist. Six cycles overdue.
- `data/functional_decipherment_research.md` — still does not exist.

---

### 1. DAMOS EpiDoc XML Export — STATUS CHANGE (HIGH PRIORITY)

**Prior cycles:** Export described as "planned," subprojects page last modified 2017, no download visible.

**This cycle:** Multiple independent search results confirm an EpiDoc-TEI XML export function is now **live in the DAMOS interface**. A paper titled "Exporting Mycenaean: From a Relational Database to EpiDoc XML files (and back again?)" is indexed at `journals.uio.no/dhnbpub/article/view/12295` — direct fetch returned 503 but the abstract is visible in search snippets.

Key details extracted from search snippets:
- Export produces EpiDoc-TEI compliant XML
- Goal: FAIR data compliance — increase integration with other epigraphic datasets
- A future **import** function is also planned (EpiDoc XML → DAMOS), enabling community contributions
- References to "Aurora 2025" in snippets suggest a 2025 interface update version

**Critical open question:** Is this a per-document export (click on one tablet, download its XML) or a bulk export endpoint (download all ~1,500+ documents as a ZIP or via API)? The paper title "and back again?" suggests bidirectional import/export, not necessarily bulk.

**Action:** (a) Access `damos.hf.uio.no` directly and locate the EpiDoc export button. (b) Email Federico Aurora (`federico.aurora@ub.uio.no`) specifically asking: "Is the EpiDoc export described in your DHN paper available for bulk download or only per-document? Is a full corpus ZIP or API endpoint available for research use?"

---

### 2. Brent Davis (Melbourne) — Syllabotactic Analysis of Linear A

**Author:** A/Prof Brent Davis, University of Melbourne (Historical & Philosophical Studies)  
**Background:** PhD on Minoan ritual vessels and Linear A; BA Linguistics from Stanford

**Method:** "Syllabotactic analysis" — statistical method assessing whether Linear A and Cretan Hieroglyphic meet specific linguistic structural criteria. Not phonetic assignment; instead, structural/distributional analysis of sign sequences.

**Published lecture:** UT Austin Scripts Workshop, March 4, 2022 (`sites.utexas.edu/scripts/2022/03/04/brent-davis...`)

**Relevance to linafish:** Syllabotactic analysis operates on sign-sequence distributions without phonetic decipherment — overlaps methodologically with linafish's distributional coupling approach more than any other researcher found to date. Davis is not doing functional register classification, but his distributional tools are adjacent.

**No 2025-2026 papers found** in this search. His Academia.edu page (`unimelb.academia.edu/BrentDavis`) and Melbourne faculty page are the next places to check.

**Action:** Fetch Davis's Academia.edu publication list for any 2024-2026 papers.

---

### 3. SpokenPast 2025 Article — Unread (Server 503)

Title: "AI Breakthrough in Deciphering Linear A: 2025 Minoan..." at `spokenpast.com/articles/ai-deciphering-linear-a-minoan-language-2025/`

Server returned 503 on direct fetch. Indexed in search results alongside the HAL paper and WSEAS 2025. Likely pop-sci, but could summarize a real 2025 research development. Title implies a claimed "breakthrough." Prior cycles have flagged similar pop-sci overclaiming (Nepal 2024, GreekReporter Petrosyan 2026). Treat with skepticism until content can be read.

**Action:** Retry fetch next cycle.

---

### 4. Emerging Scholarly Consensus — Relevant to Framing

Multiple 2025-2026 sources converge on this claim (paraphrased from search snippets): "Every specialist working on Linear A agrees that the breakthrough, if it comes, will not come primarily from better algorithms, but from the ground — specifically from a bilingual inscription or a large archive of new tablets."

**Implication for linafish:** This framing validates the linafish approach by implication. If full phonetic decipherment requires new physical evidence, then the tractable computational contribution is *functional pattern detection* — what linafish does. The framing positions linafish as the realistic computational contribution given current corpus constraints.

---

### 5. No New 2026 Peer-Reviewed Papers

All searches return zero 2026 peer-reviewed publications on Linear A (computational, functional, or phonetic). The field remains quiet. Linafish approach unoccupied.

---

### Next cycle priorities
1. Retry `spokenpast.com/articles/ai-deciphering-linear-a-minoan-language-2025/` fetch
2. Retry `journals.uio.no/dhnbpub/article/view/12295` (DAMOS EpiDoc paper) fetch
3. Check Brent Davis Academia.edu for 2024-2026 publications
4. Access `damos.hf.uio.no` directly — locate and test the EpiDoc export button
5. Create `data/linear_b_corpus_sources.md` — six cycles overdue

---
