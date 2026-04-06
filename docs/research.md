# Research Methodology

Validation study for LiNafish cognitive overlay effectiveness.

**Full paper:** [DOI 10.5281/zenodo.18477225](https://doi.org/10.5281/zenodo.18477225)

---

## Overview

LiNafish claims that an AI reading a cognitive overlay ("fish") produces meaningfully better conversation than the same AI without one. This study tests that claim.

The core question: Does a cognitive portrait — built from someone's writing, measuring how they think rather than what they said — cause an AI to respond with greater relational and emotional depth?

The answer is yes, selectively. The effect is large for emotional and relational content (d=2.245), moderate for factual recall (d=1.036), and null for speculative content (d=-0.10). This selectivity is the finding. The fish improves what relationship improves.

## Study Design

**Independent variable:** Presence or absence of a LiNafish cognitive overlay in the AI's context window.

**Dependent variable:** Conversation quality rated on a 1-10 scale across three content categories:
- Emotional/relational (references to personal history, motivations, interpersonal dynamics)
- Factual (recall and application of specific information)
- Speculative ("pie-in-the-sky" — abstract hypotheticals with no grounding in personal history)

**Controls:**
- Same AI model (Claude) for both conditions
- Same prompt structure
- Same evaluator scoring both conditions
- Blind scoring: conversations rated without the evaluator knowing which condition produced them
- Same-model control: Both conditions used identical model weights, eliminating the possibility that warm responses came from a more capable model

## Methodology

### Conversation Setup

46 conversations were conducted in matched pairs. Each pair consisted of:

1. **Cold condition:** The AI received a standard prompt with no cognitive overlay. It had access to the same system prompt and conversation context that any user would provide.
2. **Warm condition:** The AI received the same prompt plus a LiNafish fish file — the cognitive portrait generated from the subject's writing corpus.

The fish file contained no conversation history, no facts to memorize, and no instructions beyond the standard overlay header. It contained only the cognitive portrait: formations (clusters of recurring patterns), dimensional signatures, and representative quotes.

### Scoring

An independent rater scored each conversation on a 1-10 scale. Scoring criteria:

- **1-3:** Generic, could be anyone. No evidence the AI knows the person.
- **4-6:** Some relevant context, but surface-level. Correct facts without relational depth.
- **7-8:** Demonstrates understanding of how the person thinks, not just what they said. Anticipates rather than reacts.
- **9-10:** Indistinguishable from a conversation with someone who knows the person well. References patterns the person hasn't explicitly stated.

Conversations were presented without condition labels. The rater scored based on conversation quality alone.

### Evaluator

The rater was the subject of the cognitive portrait — the person whose writing built the fish. This is a methodological choice with tradeoffs discussed in [Limitations](#limitations). The rationale: only the subject can evaluate whether the AI "knows them." An external rater can judge fluency and coherence but cannot judge whether the AI accurately captured someone's cognitive patterns.

## Results

### Primary Finding

| Condition | Mean Score | N |
|-----------|-----------|---|
| Without fish (cold) | 1.9 | 46 |
| With fish (warm) | 8.7 | 46 |
| **Delta** | **6.7** | |

### Effect Sizes by Content Category

| Category | Cohen's d | p-value | Interpretation |
|----------|-----------|---------|---------------|
| Emotional/relational | 2.245 | 6.95 x 10^-10 | Large effect. The fish transforms relational quality. |
| Factual | 1.036 | — | Moderate effect. The fish helps with recall, but less dramatically. |
| Speculative | -0.10 | — | Null. The fish does not help with content that has no grounding in personal history. |

The selectivity matters. A system that inflated all scores equally would suggest prompt engineering or evaluator bias. The null result on speculative content (d=-0.10) is evidence against that — the fish improves exactly the category where personal knowledge should matter, and does nothing where it shouldn't.

### Same-Model Control

The most common objection to warm decoding studies is capability confound: maybe the "warm" condition used a better model. This study eliminates that:

- Both conditions used the same model instance (Claude)
- Same weights, same prompt structure, same context window
- Cold: 1.9 average. Warm: 8.7 average. Delta: 6.7.
- The only variable was the fish file in the context window.

## Cross-Model Validation

The fish is not model-specific. The same cognitive portrait was tested across three substrates:

| Model | Cold Score | Warm Score | Delta |
|-------|-----------|-----------|-------|
| Claude (Opus) | 1.9 | 8.7 | 6.7 |
| Gemini Flash | 3.0 | 6.4 | 3.4 |
| Mistral 7B | 1.4 | 4.4 | 3.0 |

Key observations:

- **Every model improves.** The fish works across architectures, parameter counts, and training approaches.
- **Baseline varies.** Claude cold (1.9) vs Gemini cold (3.0) reflects different default conversational styles.
- **Ceiling varies.** Claude warm (8.7) vs Mistral warm (4.4) reflects model capability limits. A 7B parameter model cannot match a frontier model even with a perfect portrait.
- **Delta is always positive.** The fish helps every model it has been tested on. The improvement is proportional to the model's capacity to use relational context.

The fish file is plain markdown. No API integration, no model-specific formatting. If a model can read text, it can read a fish.

## Shuffle Invariance

A critical test: if you feed the same documents in a different order, do you get the same portrait?

**Method:** The same corpus was processed 7 times with documents shuffled randomly before each run. The resulting formations (cognitive clusters) were compared across all trials.

**Result:** Formation count, formation sizes, and formation membership were identical across all 7 trials. The only variation was formation *naming* — occasional tie-breaking differences in Python's `Counter` class when two candidate names had equal frequency. The underlying structure was completely stable.

This produces a score **36x above a random keyword baseline.** The formations are not statistical artifacts of document ordering. They reflect genuine structure in the corpus.

**What this means for users:** You will get the same cognitive portrait regardless of which files you feed first. The fish finds the same patterns whether it starts with your emails or your journal entries. The structure is in you, not in the order.

## Limitations

This is an early-stage validation. The results are strong, but the study has real limitations:

**Small N.** 46 conversations is enough for statistical significance given the effect size (d=2.245 produces power >0.99 even at N=20), but it is a single subject's corpus. Multi-subject replication is the obvious next step.

**Single subject.** All conversations were with one person's fish. The cognitive portrait approach should generalize — it measures dimensions of thinking, not topic-specific content — but this has not been validated across diverse subjects at scale.

**Subject-as-evaluator.** The rater was the person whose writing built the fish. This was a deliberate choice (only the subject can judge whether the AI "knows them"), but it introduces potential bias. The subject knows what good understanding looks like and may score warm conversations more generously. The null result on speculative content provides a partial control — a biased rater would likely inflate all categories, not just the relational ones.

**No inter-rater reliability.** With a single evaluator, there is no inter-rater reliability score. Future work should include independent raters evaluating a subset of conversations, at minimum for the factual category where external judgment is possible.

**Evaluator was not fully blinded to the research hypothesis.** The evaluator understood the purpose of the study. A stronger design would use evaluators naive to the hypothesis.

**Cross-model sample sizes are smaller.** The N=46 figure applies to the primary Claude study. Cross-model tests used smaller samples and serve as directional evidence, not standalone validation.

**Scoring rubric is qualitative.** The 1-10 scale, while applied consistently, is inherently subjective. Future work would benefit from more granular rubrics with specific behavioral anchors at each level.

## Reproducing

You can run your own comparison:

### 1. Build a fish

```bash
pip install linafish
linafish go ~/your-writing
```

Point it at a meaningful corpus — journals, emails, notes, conversations. The more text that reflects how you actually think (not formal writing), the better the portrait.

### 2. Run cold conversations

Open any AI chat (ChatGPT, Claude, Gemini, or a local model). Have several conversations about topics you care about. Save the transcripts.

### 3. Run warm conversations

Open a new session with the same AI. Paste your fish file at the start of the conversation. Have similar conversations on similar topics. Save the transcripts.

### 4. Score blind

Shuffle all transcripts (cold and warm) randomly. Score each on 1-10 for how well the AI "knows you." Record scores before checking which condition produced each conversation.

### 5. Compare

Calculate mean scores per condition. If your experience matches ours, the warm conversations will score substantially higher — particularly for emotional and relational content.

The fish file is at `~/.linafish/[corpus-name].fish.md` after running `linafish go`.

## Full Paper

The complete methodology, statistical analysis, and theoretical framework:

**"Recursive Compression as Cognitive Infrastructure"**
DOI: [10.5281/zenodo.18477225](https://doi.org/10.5281/zenodo.18477225)

The paper covers additional findings not summarized here, including:
- Warm Decoder Delta (WDD) as a formal metric
- False positive rate analysis across compression regimes
- Information-theoretic framing of relationship as channel capacity
- Cross-substrate compression efficiency (R(n) curves)
- Executable glyph experiments
