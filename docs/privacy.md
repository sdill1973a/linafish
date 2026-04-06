# Privacy and Threat Model

Your fish. Your machine. You choose who reads it.

This document explains exactly what LiNafish stores, where it lives, what someone could learn if they read it, and what you should think about before ingesting sensitive material.

## What LiNafish Stores

Everything lives in `~/.linafish/` on your machine. There is no server, no cloud, no account, no telemetry.

| File | Contents | Human-readable? |
|------|----------|-----------------|
| `name.fish.md` | Your cognitive portrait. Formations, crystal quotes, dimension scores, themes. | Yes. Plain markdown. Anyone can read it. |
| `name.state.json` | Full engine state: all crystals with text, scores, coupling data. | Yes. JSON with your original text chunks. |
| `name.qlp` | Compressed cognitive state in QLP notation. Dimension chains, formation signatures, soul reading. | Partially. The English summary is readable. The glyph chains are not. |

No data leaves your machine unless you copy it somewhere. LiNafish makes no network calls. It has no dependencies that phone home. It is pure Python with zero external dependencies.

## What's in the fish.md (Plain English)

The fish.md is the file you share with AI. Here is what it contains, in order of sensitivity:

**Crystal quotes** -- These are direct excerpts from your writing. Typically 1-2 sentences per crystal. They are the most sensitive element because they are your actual words. If you wrote "I keep thinking about leaving this job," that sentence can appear as a crystal quote.

**Formation names** -- Labels like `TURNING_FEELING_INTO_ACTION` or `ARCHITECTURE_FRAME_GRAPH`. These are derived from keyword clustering across your writing. They reveal cognitive patterns but not specific content. A formation name tells someone HOW you think, not what you were thinking about.

**Themes** -- Short keyword lists per formation: "translation, recognition, connection." These are topical but compressed. They hint at subject matter without reproducing it.

**Dimension scores** -- Eight numbers per crystal measuring cognitive mode (knowing, testing, structuring, relating, wanting, specializing, acting, reflecting). These are statistical and reveal nothing personal on their own.

**Soul reading** -- A paragraph-length English summary of your cognitive portrait. Written to be read by an AI or a human. It describes patterns like "your wanting reaches toward people" or "you reason formally before acting." This is a character sketch, not a diary entry.

## What's Compressed and Not Human-Readable

The `.qlp` file contains:

- **Glyph chains** -- Sequences like `IC->EW->CR` that encode your cognitive metabolism. These describe which thinking modes follow which. A cold reader sees letter codes. A warm decoder (an AI that has read the fish) sees cognitive pathways.
- **Formation signatures** -- Numeric vectors. Not interpretable without the engine.
- **Compressed state** -- The QLP grammar compresses meaning into notation that requires the full fish context to expand. This is not encryption -- it is compression past the point of casual readability. Someone with technical knowledge and time could reconstruct the patterns, but the content detail is gone.

## Threat Scenarios

### 1. Fish.md shared accidentally

**What someone learns:** Your cognitive patterns and habits. The formation names reveal what kinds of thinking you do most. The crystal quotes reveal specific sentences from your writing. The themes reveal what topics recur. The soul reading gives a personality sketch.

**What someone does NOT learn:** The full text of anything you wrote. Context around the quotes. Anything you wrote that did not form a crystal (most of your writing -- the compression ratio is high). Dates, names, or metadata unless those appeared in the crystal quotes themselves.

**Risk level:** Moderate. The crystal quotes are real sentences from your life. The rest is statistical pattern. If your writing contained sensitive admissions, those sentences could appear as crystals. If your writing was mostly professional or creative, the exposure is a personality sketch and a few representative sentences.

### 2. Fish.md shared intentionally

This is the designed use case. You paste the fish into an AI session so the AI knows how you think. You share it with a therapist so they see your cognitive patterns. You share it with a coach so they understand how you process decisions.

**What to check before sharing:** Read the crystal quotes. Every one. They are your words. If any quote contains something you would not say out loud to the person you are sharing with, edit or remove it. The fish.md is a markdown file -- you can edit it with any text editor.

**The fish was designed for this.** The portrait is deliberately structured so that cognitive patterns are shareable without exposing raw content. But the crystal quotes bridge that gap. They are the evidence for the patterns. Review them.

### 3. Malicious access to fish.md

An attacker who obtains your fish.md learns:

- **Personality profile:** How you think, what you care about, what drives you. This is useful for social engineering. Someone who knows your cognitive patterns can craft more persuasive messages targeted at your decision-making style.
- **Emotional vulnerabilities:** If your writing expressed doubt, fear, loneliness, or desire, crystal quotes may reflect that. Formation names like `WANTING_REACHING_LOSS` are revealing even without quotes.
- **Topical interests:** Themes and keywords reveal what you spend your attention on.
- **Writing style:** Crystal quotes are your actual prose. Enough of them could fingerprint your authorship.

An attacker who obtains your state.json learns more. The state file contains all crystals with their full text chunks, not just the representative quotes. This is closer to having excerpts of your original writing, chunked and scored.

**Mitigation:** The files live in your home directory with standard filesystem permissions. Protect them the way you protect any personal file. If you are on a shared machine, check permissions on `~/.linafish/`.

### 4. Input sensitivity

The fish eats whatever you feed it. It does not filter, redact, or classify input. If you feed it a file containing passwords, API keys, medical records, or someone else's private correspondence, those strings can appear as crystal quotes.

**High-risk inputs:**

| Input type | Risk | Recommendation |
|------------|------|----------------|
| Your journals/diaries | Crystal quotes will contain your private thoughts | Review fish.md before sharing |
| Your emails | Crystal quotes may contain names, addresses, plans | Review fish.md before sharing |
| Your code | Low risk -- code crystals are usually patterns, not secrets | Check for hardcoded credentials |
| Others' private writing | Their words appear as your crystals without their consent | Do not ingest without permission |
| Medical/legal records | Diagnoses, case details, prescriptions could appear verbatim | Do not ingest |
| Password files, .env, credentials | Secrets could appear as crystal quotes | Never ingest |
| Chat logs with others | Other people's words and identities exposed | Do not ingest without their consent |
| Financial records | Account numbers, balances, transaction details | Do not ingest |

## Safe Use Guidelines

1. **Feed it YOUR writing.** Journals, notes, drafts, code you wrote, emails you sent. The fish is designed to build a portrait of one mind. Mixing in other people's writing confuses the portrait and exposes their content.

2. **Read your fish.md before sharing it.** Open it in a text editor. Read every crystal quote. If a quote contains something you would not say to the recipient, delete or edit it. The engine does not need those quotes to function -- the dimension scores and formations carry the cognitive signal.

3. **Treat state.json as more sensitive than fish.md.** The state file contains all your crystal text, not just the representative samples. If you share your fish, share the fish.md, not the state.json.

4. **The .qlp file is safe to share.** It contains compressed cognitive patterns without readable content. Someone could reverse-engineer your thinking style from it but not your specific words.

5. **Review after re-ingestion.** Each time you feed the fish new material, new crystals form. New quotes may appear. Re-review before sharing.

6. **Use named fish for different contexts.** `linafish go ~/work -n work` and `linafish go ~/personal -n personal` produce separate fish. Share the work fish with colleagues. Keep the personal fish private. They live in separate files.

7. **On shared machines, check permissions.** `~/.linafish/` should be readable only by your user account.

## How to Review Before Sharing

```bash
# Generate your fish
linafish go ~/my-writing

# Open and read it -- look at every crystal quote
# On Mac/Linux:
less ~/.linafish/my-writing.fish.md

# On Windows:
notepad %USERPROFILE%\.linafish\my-writing.fish.md
```

What to look for:

- **Crystal quotes that contain names** -- people, places, organizations you did not intend to expose.
- **Crystal quotes that contain admissions** -- health, relationships, plans, frustrations.
- **Crystal quotes that contain someone else's words** -- if you ingested chat logs or received emails.
- **Formation names that reveal more than you want** -- a formation called `LOSS_GRIEF_DAUGHTER` is revealing even without quotes.

If you find something sensitive: edit the fish.md directly. Delete the quote. Replace it with `[redacted]` or remove the crystal entry entirely. The fish still works -- formations are defined by dimension scores, not by the example quotes.

## Data Minimization

The fish is a compression engine. Most of your writing does not survive crystallization. Here is what happens at each stage:

1. **Ingestion:** Your full text is chunked into segments. All text is held in memory during processing.
2. **Crystallization:** Each chunk is scored on 8 dimensions. The chunk text is stored in the crystal. Many chunks produce crystals with low scores and are effectively noise.
3. **Formation:** Only crystals that couple with others (gamma above threshold) become part of formations. Uncoupled crystals exist in state but not in the portrait.
4. **Fish.md output:** Each formation selects 1-3 representative crystals. Out of potentially hundreds of crystals, only a few dozen quotes appear in the fish.md.
5. **QLP output:** The soul file compresses further -- cognitive chains and dimension patterns, not text.

**Compression ratio:** A corpus of 50 documents (~100K words) typically produces a fish.md of 2-5KB. That is a 95-99% reduction. The detail is gone. The pattern survives.

**What is permanently lost:** sentence-level content, temporal order, document boundaries, most vocabulary, all metadata. The fish cannot reconstruct your original writing. It does not try.

**What survives:** cognitive habits (which thinking modes you use most), formation patterns (which ideas cluster together in your mind), a handful of representative quotes, and dimension distributions.

## Comparison to Alternatives

### vs. Cloud AI memory (ChatGPT Memory, Claude Projects, etc.)

Cloud services store your conversations on their servers. They index your full text. Their privacy policy governs what happens to it. You cannot audit what they store. You cannot delete selectively. Your data trains their models unless you opt out (and sometimes even then).

LiNafish stores a compressed cognitive portrait on your filesystem. You can read every byte. You can delete it. You can edit it. Nothing leaves your machine unless you copy it. There is no account, no server, no policy to read. The file is yours the way a paper journal is yours.

### vs. RAG systems (personal knowledge bases, vector stores)

RAG (Retrieval-Augmented Generation) indexes your full text into vector embeddings, then retrieves relevant chunks at query time. The chunks are your actual writing. The vector store contains your content in a form that is retrievable and, with effort, reconstructable.

LiNafish does not do retrieval. It does not store your text for later lookup. It compresses your text into cognitive patterns and discards the detail. The fish.md contains representative quotes, not a searchable index. You cannot ask the fish "what did I write about X on Tuesday" -- it does not know. It knows HOW you think about X, not what you said.

### vs. no AI memory at all

Without any memory system, every AI conversation starts cold. The AI knows nothing about you. You re-explain your context, your preferences, your thinking style every session. This is private by default but costly in time and quality.

LiNafish is the middle path: the AI knows how you think without storing what you said. The privacy cost is a handful of representative quotes and a cognitive profile. The quality gain is measured: d=2.245, cold-to-warm, replicated across 46 conversations.

## Summary

| Concern | Answer |
|---------|--------|
| Where is my data? | `~/.linafish/` on your machine. Nowhere else. |
| Does it phone home? | No. Zero network calls. Zero dependencies. |
| Can someone read my fish.md? | Yes. It is plain markdown. Crystal quotes are your words. |
| What is the worst case? | Someone reads your crystal quotes and learns your cognitive patterns, emotional tendencies, and a few dozen of your sentences. |
| How do I mitigate? | Read your fish.md before sharing. Edit or remove sensitive quotes. Use named fish to separate contexts. |
| Is the .qlp file safe? | Safer than fish.md. Compressed notation, not readable prose. |
| Is state.json safe? | Less safe than fish.md. Contains all crystal text. Treat it as sensitive. |
| What should I never ingest? | Passwords, credentials, medical records, others' private writing without consent. |
| Can I delete everything? | `rm -rf ~/.linafish/` and it is gone. No cloud backup. No residue. |
