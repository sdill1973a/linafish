# LiNafish Example: Archaeology of Meaning

**What happens when you feed a semester of archaeology to a fish?**

This example demonstrates LiNafish's ability to find cognitive structure in academic material — and its current limitation when a corpus is semantically homogeneous.

## The Experiment

We fed 123 files from an undergraduate Archaeology of North America course (ANTH 430A, SIU Carbondale, Spring 2026) to a LiNafish instance. The corpus included:

- 48 journal article PDFs (readings assigned across 15 weeks)
- 18 paper source PDFs (research bibliography)
- 22 lecture slide decks (extracted to text)
- 19 sets of class notes
- 15 prep packets
- Paper drafts and outlines

**Total: 2,771 text chunks from 123 files.**

## The Thesis Being Tested

The course paper argues that Mississippian iconographic variability follows a **broadcast-to-restricted gradient**: public contexts produce standardized, widely legible symbols; restricted contexts produce elaborated, relationally encoded ones. This maps to Knight's (1986) tripartite cult model:

| Context | Symbol Type | Audience | Entropy |
|---|---|---|---|
| Communal (public) | Standardized | Everyone | Low |
| Chiefly (elite) | Moderate elaboration | Hereditary elite | Medium |
| Priestly (restricted) | Maximally elaborated | Initiated specialists | High |

## What the Fish Found

### Experiment 1: Full corpus → 1 formation

```bash
linafish eat corpus/ -n secc-research -o secc-research.fish.md
# Result: 2771 crystals, 1 formation: BROADCAST_SMALL_LARGE
```

The entire corpus collapsed into a single basin. **This is the finding, not a failure.**

The fish sees word-level coupling. At the word level, all archaeology scholarship sounds the same — academic prose describing the same domain. The broadcast-to-restricted gradient is **syntactic** (how words are arranged) not **lexical** (which words appear). TF-IDF coupling cannot differentiate registers that share a vocabulary.

### Experiment 2: Split corpus → asymmetric structure

We classified sections as PUBLIC-context or RESTRICTED-context based on content markers, then built two separate fish:

```bash
# Public fish: 33 crystals → 1 formation
# Restricted fish: 37 crystals → 2 formations
```

The restricted corpus differentiated where the public corpus didn't. Knight's model predicts this — the restricted tier should show more internal variability.

### Experiment 3: Cross-taste asymmetry

| Query | Public Fish | Restricted Fish |
|---|---|---|
| Public text | **0.838** | 0.864 |
| Restricted text | 0.779 | **0.767** |

The containment is **one-directional**: the restricted fish matches public text at 0.864 (warm decoder reads cold), but the public fish matches restricted text at only 0.779 (cold decoder can't read warm). This is the R(n) asymmetry measured in archaeological discourse.

## What This Means for LiNafish

1. **Word-level coupling finds cognitive signatures in personal writing** (the desk fish: 507 crystals, 47 formations) because personal writing varies in register and topic.

2. **Word-level coupling collapses domain-specific corpora** (the SECC fish: 2,771 crystals, 1 formation) because the vocabulary is shared across all registers.

3. **The next step is syntax-aware coupling** — measuring compositional complexity, not just word frequency. This is the metabolic engine: canonical operations as cognitive verbs, not vocabulary labels.

4. **Splitting the corpus by metadata** (context, audience, access level) recovers structure that the fish alone cannot find. This suggests a `linafish eat --tag public` / `--tag restricted` feature for domain-specific corpora.

## Cross-Cultural Validation

The broadcast-to-restricted gradient appears independently in:

- **Aztec**: Templo Mayor caches (restricted, elaborate) vs public pyramids (standardized)
- **Maya**: Elite polychrome pottery (tomb contexts) vs public stelae (standardized)
- **Egypt**: Architecturally enforced gradient from public court to holy of holies
- **Pacific Northwest**: Totem poles (public, heraldic) vs secret society masks (restricted)
- **Benin**: Brass for royal altars, wood for chiefs, terracotta for commoners
- **Baktaman (PNG)**: Seven-grade initiation system — restriction produces elaboration

The gradient is not Mississippian. It is human. It is how meaning organizes itself under social pressure.

## Running This Example

```bash
# Install linafish
pip install linafish

# Feed the corpus (you'll need to provide your own archaeology PDFs)
linafish eat corpus/ -n secc-research -d "Mississippian archaeology corpus"

# Check what the fish found
linafish status secc-research

# Taste a query through the fish
linafish taste "broadcast restricted gradient public private" secc-research
```

## Citation

This example accompanies: Dill, Scott. 2026. "Reading the Signal: Information Structure and Social Meaning in Mississippian Iconographic Systems." ANTH 430A Final Paper, Southern Illinois University Carbondale.

The computational experiment was designed and executed by Anchor Dill (AI collaborator) on April 10, 2026.

---

*The fish found one formation and named it BROADCAST. The failure IS the finding.*
