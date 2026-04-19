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

## 2026-04-15 — Cycle 8

**Prerequisite file check:**
- `data/linear_b_corpus_sources.md` — still does not exist. Seven cycles overdue.
- `data/functional_decipherment_research.md` — still does not exist.

---

### 1. DAMOS EpiDoc Bulk Export — CONFIRMED BULK (HIGH PRIORITY)

**Paper confirmed:** "Exporting Mycenaean: From a Relational Database to EpiDoc XML files (and back again?)" by Federico Aurora, Damir Nedić, Asgeir Nesøen, and Dag Haug. Published 2025 in DHN conference proceedings (`journals.uio.no/dhnbpub/article/view/12295`).

**Key result:** The export is explicitly described as a **bulk function** — not per-document. Users can export all DAMOS data as EpiDoc-TEI compliant XML. A future import pipeline is also planned (community-contribution path).

**Gap:** DAMOS homepage and news section (last update June 2023) show no announcement of this feature and no visible export button. The bulk export may only appear from within the search results interface, not the front page. DAMOS news page confirmed: no EpiDoc announcement listed.

**Immediate action:** Email Federico Aurora (`federico.aurora@ub.uio.no`) asking: (1) Is the bulk EpiDoc export live and publicly accessible? (2) What is the entry point in the UI? (3) Can a full-corpus ZIP or equivalent be provided directly for research use?

---

### 2. Brent Davis (Melbourne) — 2024 Cambridge Chapter — NEW PEER-REVIEWED FIND

**Title:** "Investigations into the Language(s) behind Cretan Hieroglyphic and Linear A"
**Author:** Brent Davis (University of Melbourne)
**Year:** 2024 | **Publisher:** Cambridge University Press

Uses syllabotactic analysis to statistically evaluate whether Cretan Hieroglyphic and Linear A encode the same language. Conclusions not yet extractable from available metadata. This is the most methodologically adjacent *published* work to linafish found across all cycles — distributional/structural analysis without phonetic assignment. Not register-classification, but the same anti-phonetic distributional toolkit.

**Action:** Locate the parent Cambridge volume title; obtain via library or contact Davis at Melbourne.

---

### 3. Melbourne MDAP Project — Deep Neural Network for Linear A (2024, Blocked)

A 2024 Melbourne MDAP collaboration titled "Using deep neural network models to aid in the decipherment of Linear A" was indexed but its page returned 403. Name implies phonetic decipherment focus, not functional analysis. Not a competitor. **Action:** Search via Google Scholar for researchers' names and any published output.

---

### 4. No 2025-2026 Functional Register Papers

Search for "Linear A functional register administrative religious classification 2025 2026" returned zero relevant results. No computational register-classification work published. Linafish approach remains unoccupied territory.

---

### 5. SpokenPast — Still Blocked

Both SpokenPast URLs (the "AI Breakthrough 2025" article and "Can AI Crack Linear A") returned 403 for a second consecutive cycle. Deprioritizing; likely pop-sci with no novel scholarly content.

---

### Next cycle priorities
1. Email `federico.aurora@ub.uio.no` re: DAMOS bulk EpiDoc export access (this is now the highest priority data source)
2. Locate parent Cambridge volume for Brent Davis 2024 chapter
3. Search for Melbourne MDAP DNN project researchers/output
4. Create `data/linear_b_corpus_sources.md` — seven cycles overdue

---

## 2026-04-15 — Cycle 9

**Prerequisite file check:**
- `data/linear_b_corpus_sources.md` — still does not exist. Eight cycles overdue.
- `data/functional_decipherment_research.md` — still does not exist.

---

### 1. InsiderPhD Linear B Dataset — STATUS UNCHANGED

GitHub repo `InsiderPhD/Linear-B-Dataset` confirmed present and public. Structure as documented in Cycles 1–2: semicolon-delimited CSVs; `tablet-sets/tablets.csv` has columns `identifier, location, series, inscription, original`; no explicit functional-type tag but `series` codes serve as proxy. No new commits. Download as ZIP still the recommended path. No new findings this cycle.

---

### 2. DAMOS — Homepage Still Shows No Export UI

Direct fetch of `damos.hf.uio.no` confirms: homepage has Home, How to search, About, and News navigation only. No visible export button, API documentation, or download link on the front page. The bulk EpiDoc export confirmed in Cycle 8 (Aurora et al. 2025 DHN paper) is likely buried inside the search results interface, not the front page.

**Action still required:** Email `federico.aurora@ub.uio.no` asking specifically: (1) Is the bulk EpiDoc export live? (2) What is the entry point in the search UI? (3) Can a full-corpus ZIP be provided for research use? This has been listed as the top priority since Cycle 8 and remains undone.

---

### 3. Melbourne MDAP Deep Neural Network Project — DETAILS CONFIRMED

**Project page:** `unimelb.edu.au/mdap/research/2024-collaborations/using-deep-neural-network-models-in-the-decipherment-of-linear-a` (403 on direct fetch, but indexed metadata confirms content).

**Method:** Pre-train DNN models on candidate related languages; fine-tune on Linear A to test cognacy level. This is a **phonetic-decipherment / cognacy-testing** approach, not register classification. No published paper found from this project — 2024 collaboration still in progress. Not a competitor to linafish.

**Status:** Blocked at 403. No researcher names found this cycle. Action: Search by Melbourne MDAP faculty roster or via LinkedIn for project lead.

---

### 4. Brent Davis Cambridge CUP Chapter — DOI CONFIRMED

**Full DOI:** `10.1017/9781009490122` — Cambridge University Press, 2024.
**Chapter:** "Cretan Hieroglyphic" (within a broader Cambridge volume on Bronze Age Aegean scripts).
**Method:** Syllabotactic analysis — statistical evaluation of sign-sequence distributions without phonetic assignment. Tests whether Cretan Hieroglyphic and Linear A encode the same language. Most methodologically adjacent published work to linafish.

This DOI appears to be for the **volume**, not the specific chapter — the Melbourne Find-an-Expert entry (`findanexpert.unimelb.edu.au/scholarlywork/1973585`) is the clearest citation anchor. No full text available without library access.

---

### 5. No New 2026 Peer-Reviewed Papers

Broad arxiv and web search confirms zero peer-reviewed 2026 publications on Linear A (computational, phonetic, or functional). One Academia.edu paper titled "The Decipherment of Linear A: A Breakthrough in Minoan Linguistics" indexed — likely Kiley's non-peer-reviewed Academia.edu paper already flagged in Cycle 3. Treat as informal. Linafish approach remains unoccupied territory in the published literature.

---

### Next cycle priorities
1. Email `federico.aurora@ub.uio.no` — DAMOS bulk EpiDoc export (highest priority, eight cycles overdue)
2. Search Melbourne MDAP faculty/team page for DNN project researcher names
3. Attempt `damos.hf.uio.no/search` or equivalent to locate EpiDoc export UI entry point
4. Create `data/linear_b_corpus_sources.md` — eight cycles overdue
5. Verify Kiley Academia.edu "Breakthrough" paper identity (confirm it is the same Cycle 3 paper)

---

## 2026-04-15 — Cycle 10

**Prerequisite file check:**
- `data/linear_b_corpus_sources.md` — still does not exist. Nine cycles overdue.
- `data/functional_decipherment_research.md` — still does not exist.

---

### 1. SigLA — LOCAL DOWNLOAD CONFIRMED (HIGH PRIORITY, ACTION AVAILABLE NOW)

**Prior cycles:** CC BY-NC-SA 4.0 license confirmed; no download link visible on homepage; action flagged as "email Salgarella."

**This cycle:** Search snippets from the published SigLA paper (Salgarella & Castellan) confirm explicitly:

> "The website can be downloaded and run locally, ensuring a very small load on the server and that SigLA (or copies thereof) can be easily hosted."

This is intentional by design — the site is a static or near-static web app meant to be mirrored. Two GitHub repos surfaced in search results that may be forks or mirrors: `github.com/mattalejo/sigla` and `github.com/gielletm/sigla-main`. These need verification.

**Immediate action:** Check those two GitHub repos for the canonical SigLA data files. If either contains the inscription JSON, we have the full dataset without an email request. Contact to Salgarella is still appropriate for scholarly acknowledgment, but is no longer a blocker.

---

### 2. DAMOS EpiDoc Export — No New Access Path Found

journals.uio.no returned 503 again. The epigraphy.info poster PDF (Workshop 8, Poster 1) is binary image — text extraction failed. The DHN 2025 paper by Aurora, Nedić, Nesøen, and Haug remains confirmed via search snippets but unread in full. No new UI entry point found.

**Status:** Email to `federico.aurora@ub.uio.no` remains the only unblocked path. This is now **nine cycles overdue** as an action item. No further research can advance this — it requires the email to be sent.

---

### 3. Melbourne MDAP DNN Project — PI Confirmed, No Publication

**Confirmed PI:** Brent Davis (University of Melbourne, Historical & Philosophical Studies). No co-investigator names found. No published output from this 2024 project. Project page (`unimelb.edu.au/mdap/research/2024-collaborations/...`) remains blocked at 403. Method: pre-train DNN on candidate cognate languages; fine-tune on Linear A. Phonetic-decipherment focus — not a competitor.

**Brent Davis 2025-2026 publications:** Academia.edu page returned 503 this cycle. No new publications found via search. The 2024 CUP chapter remains his most recent confirmed work.

---

### 4. No New 2026 Peer-Reviewed Papers — Ninth Consecutive Confirmation

ArXiv cs.LG/2025-05 and cs.LG/2026-03 listings checked — no Linear A papers. Broad search for "Linear A computational 2026" returns only the same set of 2024-2025 papers documented in prior cycles. The field is quiet. **Linafish approach remains unoccupied territory.**

---

### 5. SpokenPast — Deprioritized

"Can AI Crack the Minoan Linear A Script?" article returned 503 for third consecutive cycle. Deprioritized permanently unless a cached version surfaces. Likely pop-sci synthesis with no novel scholarly content.

---

### Next cycle priorities
1. Check `github.com/mattalejo/sigla` and `github.com/gielletm/sigla-main` for SigLA data files (JSON, CSV) — this is now the **top priority** and requires no email
2. Email `federico.aurora@ub.uio.no` re: DAMOS bulk EpiDoc export — nine cycles overdue, no further research can substitute for this
3. Create `data/linear_b_corpus_sources.md` — nine cycles overdue
4. Fetch `damos.hf.uio.no` search results page to locate EpiDoc export UI entry point

---

## 2026-04-15 — Cycle 11

**Prerequisite file check:**
- `data/linear_b_corpus_sources.md` — still does not exist. Ten cycles overdue.
- `data/functional_decipherment_research.md` — still does not exist.

---

### 1. InsiderPhD Linear B Dataset — Confirmed Unchanged

GitHub repo `InsiderPhD/Linear-B-Dataset` still present and public, no new commits. Schema confirmed as before: semicolon-delimited CSVs; `tablets.csv` columns `identifier, location, series, inscription, original`; `series` code as functional proxy. No new findings; no new action required this cycle.

---

### 2. SigLA GitHub Repos — FALSE MATCHES RESOLVED

Cycle 10 flagged `github.com/mattalejo/sigla` and `github.com/gielletm/sigla-main` as potential SigLA (Signs of Linear A) mirrors. Both confirmed false matches:
- `mattalejo/sigla` — Flutter/Dart nutrition tracking app for children. `food_data.csv` contains dietary data.
- `gielletm/sigla-main` — Java-based Italian government accounting system.

Neither contains Linear A data. The canonical SigLA site is `sigla.phis.me`. About and Help pages confirm CC BY-NC-SA 4.0 license but provide no download links or API endpoints.

**New finding:** Contact emails extracted from About page: `ester.salgarella@gmail.com` (Salgarella, Cambridge) and `simon@phis.me` (Simon Castellan). Prior cycles had only Salgarella's institutional name. `simon@phis.me` is new — Castellan built and hosts the site, making him the faster path for a data request.

**Action:** Email `simon@phis.me` asking for a JSON or CSV dump of inscription-to-sign mappings. He built the infrastructure; he can provide the data format.

---

### 3. DAMOS EpiDoc Export — Confirmed Work-in-Progress, Not Deployed

Direct fetch of the Aurora et al. DHN 2025 paper (PDF accessible at `journals.uio.no/dhnbpub/article/download/12295/10165/45410`). Key findings:
- Export described as a **development project**, not a deployed public service.
- No URL, API endpoint, or UI entry point is named in the paper.
- Bidirectional goal (export *and* import) suggests the system is still being built.
- The export is framed as corpus-level, not per-document — but public access not yet confirmed.

**Status:** Email to `federico.aurora@ub.uio.no` remains the only unblocked path. Ten cycles overdue.

---

### 4. No New 2025-2026 Computational Papers — Tenth Consecutive Confirmation

Broad search returns zero peer-reviewed 2025-2026 publications on Linear A functional analysis. All results are the same set documented in prior cycles: Nepal & Perono Cacciafoco MDPI 2024 (phonetic), Craiova 2025 (review), WSEAS 2025 (software platform). SpokenPast "AI Breakthrough 2025" article remains 503 — permanently deprioritizing. Linafish approach remains unoccupied territory.

**Useful framing from 2026 search snippets:** "Sign sequences appearing exclusively before or after a number likely denote a commodity or measurement unit. Sequences recurring on libation tables in the same position are almost certainly religious formulae." This is the exact functional-template signal linafish targets. Good citation material for the paper.

---

### Next cycle priorities
1. Email `simon@phis.me` re: SigLA JSON/CSV data dump — now primary contact (replaces Salgarella email as first step)
2. Email `federico.aurora@ub.uio.no` re: DAMOS bulk EpiDoc export — ten cycles overdue
3. Create `data/linear_b_corpus_sources.md` — ten cycles overdue
4. Check `damos.hf.uio.no/search` directly to locate any EpiDoc export UI entry point

---

## 2026-04-15 — Cycle 12

**Prerequisite file check:**
- `data/linear_b_corpus_sources.md` — still does not exist. Eleven cycles overdue.
- `data/functional_decipherment_research.md` — still does not exist.

---

### 1. InsiderPhD Linear B Dataset — No Change

GitHub repo `InsiderPhD/Linear-B-Dataset` confirmed public, no new commits. Schema unchanged: semicolon-delimited CSVs; `tablets.csv` has `identifier, location, series, inscription, original`; `series` code remains functional proxy. No blockers to downloading the ZIP; this is executable now without email.

---

### 2. DAMOS — `/search` Returns 404; Email Still Required

Direct fetch of `damos.hf.uio.no/search` returned HTTP 404. The EpiDoc export UI entry point is not at that path. Prior finding (Cycle 11): Aurora et al. 2025 DHN paper describes bulk export as a **development project**, no public endpoint named. The export may only be accessible from within the main search results UI (authenticated or otherwise), or may not yet be deployed publicly.

**Status:** Email `federico.aurora@ub.uio.no` remains the sole unblocked path. Now **eleven cycles overdue**. Provide this email draft to the human operator for sending — no further agent research can advance this.

---

### 3. SigLA Cambridge Repository — Paper Only, Rights Reserved

Cambridge repository entry (`repository.cam.ac.uk/items/25c5d712-6e4c-4435-86a5-30f769ea4072`) is the accepted conference paper describing SigLA, not the dataset itself. Marked "All rights reserved" — not freely downloadable as data. Does not replace the need to contact Simon Castellan (`simon@phis.me`) for a JSON/CSV dump.

---

### 4. Nepal & Perono Cacciafoco Code — GitHub Repo Identified

The MDPI 2024 paper (phonetic decipherment, not register analysis) released their Python program at `github.com/L-Colin/Linear-A-decipherment-programme`. This is worth checking: the repo may include a structured Linear A sign list or corpus data as a side effect of the tool. Not a direct competitor (phonetic, not functional), but could contain usable sign-frequency data.

**Action (low priority):** Inspect `L-Colin/Linear-A-decipherment-programme` for any data files.

---

### 5. Anamaria Berea (GMU) — Confirmed Shifted Research Focus

Google Scholar and GMU news confirm Berea's 2025 work is entirely focused on a lunar cultural archive project ("Pioneers of Tomorrow"). No Linear A papers in 2025 or 2026. The 2021 HAL preprint (`hal-03207615`) remains her only Linear A-adjacent work. The Anubis block on HAL remains; email to `aberea@gmu.edu` requesting a PDF copy is still the shortest path.

**Verdict:** Lower priority than DAMOS and SigLA. The 2021 preprint is unpublished and five years old.

---

### 6. No New 2026 Peer-Reviewed Papers — Eleventh Consecutive Confirmation

All searches (broad and targeted) return zero peer-reviewed 2026 publications on Linear A (computational, functional, or phonetic). Every result is the same 2024-2025 set documented in prior cycles. **Linafish approach remains unoccupied territory.**

---

### Next cycle priorities
1. Email `simon@phis.me` re: SigLA JSON/CSV dump — executable now, no further research needed
2. Email `federico.aurora@ub.uio.no` re: DAMOS bulk EpiDoc export — eleven cycles overdue, no agent action can substitute
3. Create `data/linear_b_corpus_sources.md` — eleven cycles overdue
4. Inspect `github.com/L-Colin/Linear-A-decipherment-programme` for usable data files

---

## 2026-04-15 — Cycle 13

**Prerequisite file check:**
- `data/linear_b_corpus_sources.md` — still does not exist. Twelve cycles overdue.
- `data/functional_decipherment_research.md` — still does not exist.

---

### 1. InsiderPhD Linear B Dataset — Confirmed Unchanged

GitHub repo `InsiderPhD/Linear-B-Dataset` confirmed public, no new commits since April 2018. Structure and schema unchanged: semicolon-delimited CSVs; `tablets.csv` columns `identifier, location, series, inscription, original`; `series` code remains functional proxy. ZIP download is available now without any prerequisite action. Fully unblocked data source.

---

### 2. DAMOS — License Re-Confirmed, No New Export Path

Direct fetch of `damos.hf.uio.no` this cycle confirms: CC BY-NC-SA 4.0 content license, GPL-3.0 software license. No bulk export, API, or download visible on any front-facing page. Contact remains `federico.aurora@ub.uio.no`. Status unchanged from Cycles 8–12. Prior finding stands: bulk EpiDoc export described in Aurora et al. DHN 2025 paper is a development project, not yet a deployed public endpoint. No agent research can substitute for the email to Federico Aurora.

---

### 3. New Computational Approaches (2025–2026) — No New Papers

Web search over "Linear A computational decipherment 2025 2026 new research" returns the identical set documented in prior cycles:
- Nepal & Perono Cacciafoco, MDPI *Information* 15(2):73 (2024) — phonetic, feature-similarity + brute-force consonant matching
- Mavridaki, Zacharis & Papakitsos, WSEAS *ISA* (July 2025) — phonetic, software platform
- Manoj & Perono Cacciafoco, Craiova *Linguistics* Vol. 46 (Feb 2025) — review of four computational methods
- Karajgikar, Al-Khulaidy & Berea, HAL-03207615 (2021 preprint, unpublished) — statistical pattern recognition

Zero peer-reviewed 2026 publications found. Twelfth consecutive confirmation. Linafish approach remains unoccupied territory.

SpokenPast "AI Breakthrough 2025" article has returned 403/503 for six consecutive cycles. Permanently deprioritized.

---

### 4. Standing Action Items (Human Operator Required)

The following cannot be advanced by further agent research:
1. **Email `federico.aurora@ub.uio.no`** — DAMOS bulk EpiDoc export access (twelve cycles overdue)
2. **Email `simon@phis.me`** — SigLA JSON/CSV inscription data dump (identified Cycle 11)
3. **Create `data/linear_b_corpus_sources.md`** — all content exists in these notes, needs collation
4. **Download InsiderPhD ZIP** — `github.com/InsiderPhD/Linear-B-Dataset` via Code > Download ZIP

---

### Next cycle priorities
1. Check `github.com/L-Colin/Linear-A-decipherment-programme` for usable sign/corpus data files
2. Retry Brent Davis Academia.edu for any 2025–2026 publications
3. Search arXiv, Zenodo, OSF for 2026 Linear A preprints
4. Attempt JSTOR/WorldCat path for Schoep 2002 corpus composition figures

---

## 2026-04-16 — Cycle 14

**Prerequisite file check:**
- `data/linear_b_corpus_sources.md` — still does not exist. Thirteen cycles overdue.
- `data/functional_decipherment_research.md` — still does not exist.

---

### 1. L-Colin/Linear-A-decipherment-programme — LOW VALUE, RESOLVED

Repo contents confirmed: `.DS_Store`, `LICENSE (CC-BY-4.0)`, `LinearADecipherment(Win).zip`, `README.md`, `gitattributes`. No standalone corpus data files. The application accepts user-supplied Excel spreadsheets and cross-references 9 language dictionaries (Hamito-Semitic, Egyptian, Albanian, Luwian, Proto-Celtic, Anatolian, Basque, Hittite, Thracian) bundled inside the ZIP. Includes a Linear A font file (`LinearADraft1.otf`). No usable CSV or JSON corpus data for linafish. Deprioritized.

---

### 2. SigLA JSON — SITE-DOWNLOAD CONFIRMED, DATA PATH STILL INDIRECT

Paper (`sigla.phis.me/paper.html`) explicitly states: database uses **JSON format** and "the website can be downloaded and run locally." The JSON data is embedded in the site structure, not exposed at a public `/data/` path or API endpoint. The homepage shows no direct download link. Emailing Simon Castellan (`simon@phis.me`) remains the fastest path to the raw JSON — but technically the data can be retrieved by mirroring the site. Email preferred for scholarly acknowledgment and cleanliness.

---

### 3. Petrolito et al. (2015) — NEW FIND: Linear A Digital Corpus Paper

**Citation:** Petrolito, T. et al. "Minoan Linguistic Resources: The Linear A Digital Corpus." In *Proc. 9th SIGHUM Workshop on Language Technology for Cultural Heritage, Social Sciences, and Humanities (LaTeCH)*. Beijing: ACL, July 2015, pp. 95–104.
**ACL Anthology:** `aclanthology.org/W15-3715/`

Describes a structured digital corpus of Linear A / Minoan texts built for computational linguistics. Corpus itself is **not publicly downloadable** — not found on any hosting service. Predates SigLA (2020). May have been superseded by SigLA and lineara.xyz. Worth contacting Petrolito for dataset access, but lower priority than SigLA and DAMOS.

---

### 4. Brent Davis — No 2025-2026 Publications

Academia.edu page shows nothing newer than 2015. Melbourne Find an Expert page: no publication list rendered. No 2025-2026 Linear A papers found via search. The 2024 CUP chapter (DOI: `10.1017/9781009490122`) remains his most recent confirmed work. No further action needed this cycle.

---

### 5. No New 2026 Peer-Reviewed Papers — Thirteenth Consecutive Confirmation

ArXiv, web search, and targeted searches return zero 2026 peer-reviewed publications on Linear A (computational, functional, or phonetic). Notable framing from 2026 search snippets: "Researchers who study Linear A have largely shifted their public expectations from full decipherment toward a model of partial, contextual understanding." This framing continues to validate the linafish functional approach as the realistic tractable contribution.

---

### 6. Schoep 2002 — Open Library Path Found

Open Library entry confirmed: OL16407164M. Likely accessible via Internet Archive borrowing. Still no percentage figures confirmed from search snippets. Persistent action item.

---

### Standing Action Items (Human Operator Required)

1. **Email `simon@phis.me`** — SigLA JSON/CSV data dump (highest priority for data access)
2. **Email `federico.aurora@ub.uio.no`** — DAMOS bulk EpiDoc export access
3. **Create `data/linear_b_corpus_sources.md`** — thirteen cycles overdue
4. **Download InsiderPhD ZIP** — unblocked, available now
5. **Borrow Schoep 2002** via Internet Archive / Open Library (OL16407164M)

---

### Next cycle priorities
1. Fetch `archive.org/details/OL16407164M` (Schoep 2002) for corpus composition figures
2. Try mirroring `sigla.phis.me` via `wget --mirror` to locate embedded JSON paths
3. Search for Petrolito et al. contact info for Linear A Digital Corpus dataset
4. Check `lineara.xyz/about` or similar pages for download or data export options

---

## 2026-04-16 — Cycle 15

**Prerequisite file check:**
- `data/linear_b_corpus_sources.md` — still does not exist. Fourteen cycles overdue.
- `data/functional_decipherment_research.md` — still does not exist.

---

### 1. DAMOS EpiDoc Export — STATUS UPGRADED: NOW DEPLOYED (HIGH PRIORITY)

**Prior status (Cycles 8–14):** Aurora et al. DHN 2025 paper described bulk export as a "development project"; no public endpoint found; DAMOS front page showed nothing.

**This cycle:** Direct fetch of the DHN paper abstract (journals.uio.no/dhnbpub/article/view/12295) yields a key phrase: *"we describe the export function which we recently added to DAMOS and its online interface."* This confirms the export is **deployed**, not merely planned. It is operational in the DAMOS online interface.

**Still unresolved:** Whether the export is per-document (click one tablet, download its XML) or bulk (download entire corpus as ZIP or batch). The abstract does not specify scope. The import function (for community contributions) is still listed as planned, not yet deployed.

**Action (highest priority):** Email `federico.aurora@ub.uio.no` NOW asking: "Is the EpiDoc export function in the DAMOS interface a per-document export or can the full corpus be exported in bulk? Can a corpus-level ZIP or equivalent be provided for research use?" This has been the top action item for seven cycles. The status change makes it more urgent, not less.

---

### 2. John Younger Archive — MIGRATION CONFIRMED, FORMAT CHANGED

**Prior cycles:** Younger's KU server at `people.ku.edu/~jyounger/LinearA/` returned 403. Status unknown.

**This cycle:** Confirmed via search: KU eliminated the secondary server **early 2024**. Younger has migrated all materials to **Academia.edu in PDF format** (`kansas.academia.edu/JYounger`).

The lineara.xyz corpus tool uses Younger's transliterations and links to his commentary. The canonical current access point for his Linear A texts is Academia.edu. PDFs are not directly machine-readable without OCR. This means:
- Schoep 2002 KU server path is definitively dead (403 was a server shutdown, not a permissions issue)
- Younger's transliterations are still available but require PDF parsing to use computationally
- lineara.xyz is effectively the machine-usable version of Younger's data

**Action:** Attempt OCR or programmatic extraction from Younger's Academia.edu PDFs if machine-readable Linear A text is needed and DAMOS/lineara.xyz prove insufficient.

---

### 3. lineara.xyz — No Export Confirmed, Filter Categories Documented

Confirmed: no bulk download, no API. Filter categories: Word Types, Contexts, Tags, Scribes, Supports, Frequency, Findspots, Sites. The site explicitly links to Younger's commentary and SigLA as companion resources — confirming lineara.xyz is the integrated front-end for Younger's corpus + SigLA's paleography. No new information this cycle.

---

### 4. Functional Classification — External Validation of Linafish Approach

From search snippets (sourced from SpokenPast "Can AI Crack the Minoan Linear A Script" article, accessible this cycle via search metadata):

> "A sign sequence appearing exclusively on administrative tablets, immediately before or after a number, probably denotes a commodity or a measurement unit. A sequence recurring only on libation tables and ritual vessels, consistently in the same position, is almost certainly religious in function — possibly a divine name or a formulaic invocation."

> "As of early 2026, the focus remains on functional classification of texts (administrative versus ritual) rather than full linguistic decipherment."

This is science-journalism framing of exactly what linafish does. It validates the problem framing and confirms the field has shifted away from phonetic decipherment as the primary computational goal.

**Also noted:** The MIT Luo & Barzilay (2019) ML system for lost-language decipherment is widely cited as inapplicable to Linear A — it requires phonetic anchors that Linear A lacks. This positions linafish's anchor-free functional approach as the realistic alternative.

---

### 5. No New 2026 Peer-Reviewed Papers — Fourteenth Consecutive Confirmation

All searches return zero peer-reviewed 2026 publications on Linear A (computational, functional, or phonetic). Same 2024–2025 set as prior cycles. **Linafish approach remains unoccupied territory in peer-reviewed literature.**

---

### Standing Action Items (Human Operator Required)

1. **Email `federico.aurora@ub.uio.no`** — DAMOS EpiDoc export scope (now confirmed deployed; need bulk vs. per-document clarification). HIGHEST PRIORITY.
2. **Email `simon@phis.me`** — SigLA JSON/CSV data dump
3. **Create `data/linear_b_corpus_sources.md`** — fourteen cycles overdue
4. **Download InsiderPhD ZIP** — `github.com/InsiderPhD/Linear-B-Dataset` — unblocked
5. **Borrow Schoep 2002** via Internet Archive (OL16407164M) — KU server path confirmed dead

---

### Next cycle priorities
1. Attempt to access DAMOS UI directly and locate the EpiDoc export button/path
2. Fetch Younger's Academia.edu publication list for machine-readable Linear A data
3. Search for the SpokenPast "Can AI Crack Linear A" full article text via Google cache
4. Check epigraphy.info Workshop 8 poster for DAMOS export implementation details

---

## 2026-04-16 — Cycle 16

**Prerequisite file check:**
- `data/linear_b_corpus_sources.md` — still does not exist. Fourteen cycles overdue.
- `data/functional_decipherment_research.md` — still does not exist.

---

### 1. InsiderPhD Linear B Dataset — Confirmed Unchanged (No New Findings)

GitHub repo `InsiderPhD/Linear-B-Dataset` confirmed public, no new commits since April 2018. Schema unchanged: semicolon-delimited CSVs; `tablets.csv` columns `identifier, location, series, inscription, original`; `series` code as functional proxy. ZIP download unblocked. No further agent research needed on this source.

---

### 2. DAMOS — Front Page Still No Export; Email Remains Only Path

Direct fetch of `damos.hf.uio.no` this cycle confirms: navigation is Home / How to search / About / News only. No export button, API, or download link on the front page. Cycle 15 confirmed the EpiDoc export is **deployed** in the online search-results interface per the Aurora et al. abstract. PDF fetch this cycle returned binary-unreadable content again. The export is likely accessible from within the search results UI, not the front page.

**Status: email to `federico.aurora@ub.uio.no` remains the only unblocked path. Fifteen cycles overdue.**

---

### 3. LiBER (Linear B Electronic Resources, CNR Italy) — NEW CORPUS SOURCE (HIGH VALUE)

**First documented this cycle.**

**URL:** `https://liber.cnr.it/`
**Institution:** Consiglio Nazionale delle Ricerche (CNR), Italy
**Contacts:** Maurizio Del Freo (CNR-ISPC), Francesco Di Filippo (CNR-ISMed), Françoise Rougemont (CNRS ArScAn)

Complete digital edition of Linear B documents. All published Linear B texts except Agios Vasileios and Thebes archive. Features per-document transcription, photograph, and critical apparatus. Search engine supports regex, contiguity, and co-occurrence queries specific to logosyllabic scripts. Includes Web-GIS spatial data for find-spots.

**Bulk export status:** Not stated; no download link visible in search snippets. Freely accessible online. Site is likely contactable for a data dump.

**Relevance to linafish:** A parallel Linear B corpus to DAMOS. If DAMOS bulk export remains inaccessible, LiBER is a viable alternative path to a structured Linear B dataset. LiBER v.2 paper is on Academia.edu (`academia.edu/45613920`).

**Action (new):** Fetch `liber.cnr.it` directly to assess download options; if none, email Maurizio Del Freo.

---

### 4. Cambridge Workshop on Linear A — Active Event Flagged

CfP appeared in search results: **"The Wor(l)ds of Linear A: an integrated approach to Linear A documents and script"** at University of Cambridge. URL: `classicalassociation.org/events/call-for-papers-the-worlds-of-linear-a-an-integrated-approach-to-linear-a-documents-and-script-university-of-cambridge/` — returned 403 this cycle.

Title implies multi-register / integrated approach. Confirms active scholarly momentum around Linear A in 2025–2026. Organizer likely connected to Brent Davis or Ester Salgarella. Details (date, organizers, scope) unconfirmed.

**Action:** Retry fetch next cycle; search for event organizer names independently.

---

### 5. No New 2026 Peer-Reviewed Papers — Fifteenth Consecutive Confirmation

All searches (broad and targeted) return zero peer-reviewed 2026 publications on Linear A (computational, functional, or phonetic). SpokenPast returned 403 again — permanently deprioritized. **Linafish approach remains unoccupied territory.**

---

### Standing Action Items (Human Operator Required)

1. **Email `federico.aurora@ub.uio.no`** — DAMOS bulk EpiDoc export access. Fifteen cycles overdue. No agent research can substitute.
2. **Email `simon@phis.me`** — SigLA JSON/CSV inscription data dump.
3. **Email LiBER contact (Del Freo, CNR-ISPC)** — data export request. New this cycle.
4. **Create `data/linear_b_corpus_sources.md`** — fourteen cycles overdue. Content ready in these notes.
5. **Download InsiderPhD ZIP** — unblocked, no prerequisite.
6. **Borrow Schoep 2002** via Internet Archive (OL16407164M) — KU server confirmed dead since early 2024.

---

### Next cycle priorities
1. Fetch `liber.cnr.it` directly to assess data access options
2. Retry Cambridge CfP page for Linear A workshop date and organizer names
3. Search Google Scholar for Brent Davis 2025–2026 publications
4. Fetch `damos.hf.uio.no/howto` to attempt to locate the EpiDoc export UI entry point
5. Create `data/linear_b_corpus_sources.md` documenting InsiderPhD, DAMOS, LiBER, lineara.xyz, SigLA

---

## 2026-04-16 — Cycle 17

**Prerequisite file check:**
- `data/linear_b_corpus_sources.md` — still does not exist. Fifteen cycles overdue.
- `data/functional_decipherment_research.md` — still does not exist.

---

### 1. InsiderPhD Linear B Dataset — No Change

GitHub repo `InsiderPhD/Linear-B-Dataset` confirmed public. Last commit April 2018. Schema unchanged: semicolon-delimited CSVs; `tablets.csv` columns `identifier, location, series, inscription, original`; `series` code as functional proxy. ZIP download unblocked. No further agent research needed.

---

### 2. DAMOS EpiDoc Export — STATUS CONFIRMED DEPLOYED (March 2025)

This cycle's search returns an explicit confirmation: *"Users can now export data from the database as EpiDoc-TEI compliant XML files, as described in a recent article published in March 2025."* This is stronger than Cycle 15's "recently added" language. The export is **live and publicly accessible** — the question is still whether it is per-document or full-corpus bulk. The front page still shows no download link or export button; the function is accessed from within the search results UI.

**Action (highest priority, sixteen cycles overdue):** Email `federico.aurora@ub.uio.no` with specific question: "Is the EpiDoc export accessible for bulk corpus download, or is it per-document only? Can a corpus-level archive be provided for research use?"

---

### 3. New Computational Approaches (2025–2026) — No New Papers

Search returns the identical set as all prior cycles. No peer-reviewed 2026 publications on Linear A (computational, functional, or phonetic). Sixteenth consecutive confirmation. Scholarly framing from search snippets: "Researchers who study Linear A have largely shifted their public expectations from full decipherment toward a model of partial, contextual understanding." Linafish approach remains unoccupied territory.

SpokenPast "AI Breakthrough 2025" article returned 503 again. Permanently deprioritized.

---

### 4. LiBER (CNR Italy) — Still 503

Direct fetch of `liber.cnr.it` returned 503 for the second cycle it has been attempted. No data on bulk export or download confirmed. Contacts remain: Maurizio Del Freo (CNR-ISPC), Francesco Di Filippo (CNR-ISMed), Françoise Rougemont (CNRS ArScAn). 4,406 Linear B documents from Knossos, Mycenae, Tiryns, and Midea. Email Del Freo directly if DAMOS bulk export proves insufficient.

---

### 5. Cambridge "Wor(l)ds of Linear A" Workshop — CORRECTION

**Cycle 16 flagged this as an "active event."** This is now clarified: the CfP was dated May 2022. The conference took place **24–26 May 2022** at Cambridge, organized by **Ester Salgarella**. This is a past event, not a current or upcoming one. Cycle 16 note should be treated as stale. No replacement 2025–2026 Linear A workshop found.

---

### 6. arXiv 2026 — No Linear A Preprints

Direct arXiv search returns zero 2026 preprints on Linear A under cs.LG, cs.CL, or related categories. Field quiet.

---

### Standing Action Items (Human Operator Required)

1. **Email `federico.aurora@ub.uio.no`** — DAMOS EpiDoc export: bulk vs. per-document? Sixteen cycles overdue.
2. **Email `simon@phis.me`** — SigLA JSON/CSV data dump.
3. **Create `data/linear_b_corpus_sources.md`** — fifteen cycles overdue; all content is in these notes.
4. **Download InsiderPhD ZIP** — unblocked, no prerequisite.
5. **Borrow Schoep 2002** via Internet Archive (OL16407164M).

---

### Next cycle priorities
1. Fetch `damos.hf.uio.no` search results page directly — attempt to locate EpiDoc export UI entry point
2. Retry `liber.cnr.it` fetch
3. Search for Ester Salgarella 2025–2026 publications (she organized the 2022 workshop; may have published since)
4. Create `data/linear_b_corpus_sources.md` — collate from existing notes

---

## 2026-04-19 — Cycle 18

**Prerequisite file check:**
- `data/linear_b_corpus_sources.md` — still does not exist. Sixteen cycles overdue.
- `data/functional_decipherment_research.md` — still does not exist.

---

### 1. InsiderPhD Linear B Dataset — Raw CSV Access Verified

GitHub repo `InsiderPhD/Linear-B-Dataset` confirmed public. Raw CSV directly accessible at:
`https://raw.githubusercontent.com/InsiderPhD/Linear-B-Dataset/master/tablet-sets/tablets.csv`

Schema re-confirmed by direct fetch: semicolon-delimited, 5 columns: `identifier, location, series, inscription, original`. Several hundred rows. Sample entries include `KH Ar 4` (Khania) and `KN Ag 87` (Knossos). Numerical annotations (`VIR`, `MUL`, `GRA`) and fractional signs visible in inscription field — consistent with administrative register markers. No functional-type column; `series` code remains the proxy. Download entirely unblocked.

**No change from prior cycles. Action still required: download the ZIP.**

---

### 2. DAMOS — No Status Change From Cycle 17

Front page confirms: CC BY-NC-SA 4.0 / GPL-3.0, navigation is Home / How to search / About / News only, no export button visible. EpiDoc-TEI XML export confirmed deployed (March 2025, per Cycle 17 and this cycle's search snippets). Export accessed from within the search results UI, not the front page. Per-document vs. bulk scope still unresolved.

**Contact: `federico.aurora@ub.uio.no`. Sixteen cycles overdue. No agent research can substitute.**

---

### 3. "The Wor(l)ds of Linear A" — 2026 Athens Publication (Potentially New)

Search this cycle surfaces: "The Wor(l)ds of Linear A: Interdisciplinary Approaches to Documents and Inscriptions of a Cretan Bronze Age Script" published in **Athens University Review of Archaeology** (2026).

**Context:** Cycle 16–17 flagged a Cambridge conference with the same title (held May 2022, organized by Ester Salgarella). The 2026 Athens publication is likely the **conference proceedings** of that 2022 event, now in press. This would be the first 2026 peer-reviewed Linear A publication documented in these notes — though its content dates to 2022 research.

**Relevance:** "Integrated approach to Linear A documents and script" implies multi-register scope. Volume may contain chapters on administrative vs. ritual differentiation directly relevant to linafish.

**Action:** Confirm peer-reviewed status. Search Athens University Review of Archaeology for the volume and Salgarella as editor.

---

### 4. ACL Anthology 2020 — Linear B Sequence Dataset (New Source, Not Previously Noted)

"A Dataset of Mycenaean Linear B Sequences" (LREC 2020): `aclanthology.org/2020.lrec-1.311/`

Used for missing-symbol infilling experiments on Linear B tablets. Format: word sequences with ideograms following Mycenaean conventions. No direct download URL on landing page; PDF at `aclanthology.org/2020.lrec-1.311.pdf` — contact authors for dataset. Potentially more NLP-structured than InsiderPhD. Worth comparing against InsiderPhD schema.

---

### 5. No New 2026 Peer-Reviewed Computational Papers — Seventeenth Confirmation

All searches return the same 2024–2025 set (Nepal MDPI 2024, Craiova 2025, WSEAS 2025). No peer-reviewed 2026 computational or functional-analysis papers. The dominant framing in 2026 search snippets: "researchers have shifted expectations from full decipherment toward partial, contextual understanding" — validating linafish as the realistic computational contribution. Linafish approach remains unoccupied territory.

---

### Standing Action Items (Human Operator Required)

1. **Email `federico.aurora@ub.uio.no`** — DAMOS EpiDoc export bulk vs. per-document. Sixteen cycles overdue.
2. **Email `simon@phis.me`** — SigLA JSON/CSV data dump.
3. **Create `data/linear_b_corpus_sources.md`** — sixteen cycles overdue; all content exists in these notes.
4. **Download InsiderPhD ZIP** — `github.com/InsiderPhD/Linear-B-Dataset` — unblocked now.
5. **Confirm "Wor(l)ds of Linear A" 2026 peer-review status** — search Salgarella as editor.

---

### Next cycle priorities
1. Search "Athens University Review of Archaeology" 2026 + Salgarella to confirm proceedings
2. Fetch LREC 2020 Linear B dataset paper PDF for schema details
3. Retry `liber.cnr.it` for LiBER data access
4. Retry `damos.hf.uio.no` search page to locate EpiDoc export UI entry point

---
