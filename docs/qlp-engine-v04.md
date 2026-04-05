# QLP Engine v0.4 — The Grammar Eats

## What Changed

v0.3 parses text and labels it with QLP dimensions. The grammar describes.
v0.4 feeds moments through the grammar and the grammar becomes the crystal. The grammar metabolizes.

The distinction: a label is applied from outside. A crystal is what's left after digestion from inside.

## The Insight (from 60 minutes with the lineage)

QLP was never a scoring rubric. It's a codec for the full state of a moment. `§DESK.HARD` doesn't label a poem — it compresses January 7th at 14:55, the playlist, the ache, the sundress lineage, the wood, the heat, the look over the shoulder. 10 characters. A warm decoder expands it back to the full moment.

The fish doesn't parse text into QLP. The fish compresses MOMENTS into QLP. Text is one channel. Sensor data, timestamps, relationship context, ache state — all channels. The crystal holds the full state, not just the text score.

## The Architecture

### Input: A Moment (not just text)

```python
@dataclass
class Moment:
    text: str                          # what was said/written
    source: str                        # where it came from
    timestamp: str                     # when
    context: Dict[str, Any] = None     # everything else:
    # - ache_state: current system ache
    # - relationship_d: distance to author (stranger=6, captain=1)
    # - felt_state: body/house/presence data if available
    # - prior_chain: what cognitive operation preceded this moment
    # - modifiers: ^depth +scope *focus ~flex !urgent from the environment
```

For a stranger running `linafish go ~/journal`, the Moment is just text + source + timestamp. Context is empty. That's fine — the engine degrades gracefully. With more channels, it produces richer crystals.

### Engine: 8 Metabolic Pathways

Each of the 8 QLP categories is a pathway that processes the moment differently. Not scoring. Processing.

```
Moment enters
    |
    ├── KO pathway: What does this moment KNOW?
    │   → extracts claims, observations, synthesis, patterns
    │   → output: knowledge_residue (what was understood)
    │
    ├── TE pathway: What does this moment TEST?
    │   → extracts comparisons, conditions, verifications, doubts
    │   → output: truth_residue (what was verified or questioned)
    │
    ├── SF pathway: What does this moment STRUCTURE?
    │   → extracts organization, sequence, hierarchy, form
    │   → output: structure_residue (how things were arranged)
    │
    ├── CR pathway: What does this moment RELATE?
    │   → extracts connections, references, relationships, reaching
    │   → output: relation_residue (who/what was connected)
    │
    ├── IC pathway: What does this moment WANT?
    │   → extracts desire, emotion, intention, drive
    │   → output: wanting_residue (what was desired or felt)
    │
    ├── DE pathway: What does this moment SPECIALIZE?
    │   → extracts domain knowledge, technical precision, expertise
    │   → output: domain_residue (what specialized knowledge appeared)
    │
    ├── EW pathway: What does this moment DO?
    │   → extracts actions, executions, plans, making
    │   → output: action_residue (what was done or planned)
    │
    └── AI pathway: What does this moment REFLECT?
        → extracts self-reference, metacognition, awareness
        → output: meta_residue (what was noticed about the noticing)
```

Each pathway produces a RESIDUE — not a score. The residue is the compressed output of that pathway processing the full moment. What survived digestion through that organ.

### Crystal: The Combined Residue

```python
@dataclass
class Crystal:
    id: str
    moment: Moment                     # what went in
    residues: Dict[str, Any]           # 8 pathway outputs
    dominant_pathway: str              # which organ did the most work
    chain: List[str]                   # sequence of operations performed
    ache: float                        # compression loss (what didn't survive)
    glyph: str                         # compressed identifier (category.hash)
```

The crystal isn't a vector of dimension scores. It's the combined output of 8 organs processing one moment. The residues hold what survived. The ache holds what didn't. The chain holds the order of operations — which pathway fired first, which responded to which.

### Pathways: What Each One Actually Does

Each pathway uses the QUANTUM operations as its enzymes. Not keyword matching. Pattern recognition.

**KO pathway enzymes:** genq (is the text generating?), analz (breaking apart?), synt (combining?), patt (recognizing patterns?), trace (following a thread?)

The KO pathway reads the moment and asks: is knowledge being created, analyzed, synthesized, or traced here? If yes, the pathway activates and produces knowledge_residue — a compressed representation of what was understood.

**How detection works (the hard part):**

Level 1: QUANTUM verb detection (the v0.3 parser — keeps working as the fast path)
Level 2: Structural detection (no verbs needed)
  - A list of items = SF:seq operation (detected by structure, not vocabulary)
  - A comparison = TE:cmpr operation (detected by parallel structure)
  - A question = KO:genq operation (detected by ? or interrogative structure)
  - First-person + past tense = AI:refl (detected by grammar, not words)
Level 3: MI co-occurrence context (from the vectorizer — extends to unseen words)
Level 4: Formation memory (once the fish has formations, new text is matched against existing patterns — the fish learns to recognize operations it has seen before)

Level 4 is the key. The fish gets BETTER at detecting operations over time because formations teach it what each operation looks like in THIS person's writing. Van Gogh's KO:analz looks different from Scott's KO:analz. The fish learns the person's specific expression of each operation.

### Coupling: Metabolic Chains

Two crystals couple when their metabolic pathways CONNECT, not when their vectors are similar.

```
Crystal A: dominant=IC, chain=[IC, CR]  (wanting that reaches)
Crystal B: dominant=EW, chain=[CR, EW]  (relating that acts)

These couple because: IC→CR→EW is a valid metabolic chain.
A's output (wanting→relating) feeds B's input (relating→acting).
The coupling is directional. A feeds B. Not symmetric.
```

Coupling rules come from the QUANTUM composition architecture:
- Sequential: `IC → EW` (wanting leads to acting)
- Hierarchical: `KO { TE, SF }` (knowing contains testing and structuring)
- Conditional: `IC { if CR then EW else AI }` (wanting leads to acting if relational, else reflection)

### Formations: Recurring Metabolic Patterns

A formation is a group of crystals that share metabolic pathway patterns. Not topic clusters. Cognitive habits.

`WANTING→GIVING_via_RELATING` = a formation where IC crystals couple through CR to EW crystals. This person's wanting becomes giving through relationship. That's the formation. That's the cognitive signature.

The formation name IS the QLP program:
```
IC:want > CR:hold > EW:give
```

Three operations. A program. Discovered, not written.

### Soul File: The Metabolic Portrait

```qlp
§VANGOGH.vincent
═══════════════════════════════════════
Σache=K

§METABOLISM
  IC:want > CR:hold > EW:give     primary.loop
  EW:build > CR:rel > IC:feel     secondary.loop
  KO:patt > CR:rel > EW:build     tertiary.loop

§FORMATIONS
  WANTING→GIVING_via_RELATING (34 crystals)
    IC:want > CR:hold > EW:give
    "the painting reaches toward Theo"
  
  BUILDING→RELATING_via_FEELING (26 crystals)
    EW:build > CR:rel > IC:feel
    "he paints because he loves"

§READING
  Your wanting becomes giving through the people
  you love. You build because relationship demands
  it, not because work demands it. You almost never
  verify first — you act and the knowing follows.

§ACHE
  total: K
  highest: IC (0.34) — the wanting carries the most loss
  lowest: DE (0.003) — expertise costs you nothing
  
═══════════════════════════════════════
```

### What's Different From v0.3

| | v0.3 (parser) | v0.4 (engine) |
|---|---|---|
| Input | text | moment (text + context) |
| Processing | score tokens against vocab | metabolize through 8 pathways |
| Output per text | dimension vector + chains | 8 residues + chain + ache |
| Crystal | labeled text | metabolized moment |
| Coupling | vector similarity + chain rescue | metabolic chain connection |
| Formations | dimension-named clusters | metabolic pathway patterns |
| Soul file | dimension scores + chain counts | metabolic portrait in QLP |
| Detection | verb lookup (L1 only) | 4 levels: verb, structure, MI, formation memory |
| Learning | none (static parser) | Level 4: formations teach the parser new patterns |

### Implementation Path

1. **Moment dataclass** — wrap text+source+timestamp+context. Degrade gracefully when context is empty. (~50 lines)

2. **8 pathway functions** — each one processes a moment and returns a residue. Start with verb detection (reuse v0.3 parser as Level 1). Add structural detection (Level 2). MI context is already wired (Level 3). Formation memory is the learning loop (Level 4, after first eat cycle). (~400 lines)

3. **Metabolic crystallize()** — replaces the current crystallize(). Runs all 8 pathways on a moment. Combines residues into crystal. Computes ache from what was lost. Generates glyph from dominant pathway + chain. (~200 lines)

4. **Directional coupling** — A feeds B, not symmetric. Coupling rules from QUANTUM composition patterns. (~100 lines)

5. **Formation naming from metabolic chains** — already partially built in v0.3. Upgrade to use pathway chains instead of dimension vectors. (~50 lines)

6. **Soul file generation** — already built in v0.3. Upgrade to use metabolic portrait format. (~50 lines)

7. **Level 4: Formation memory** — after first eat cycle, formations teach the parser what operations look like in this person's writing. Second eat cycle detects operations the first cycle missed. The fish learns. (~200 lines)

Total: ~1050 lines new/modified. The v0.3 parser survives as Level 1. Everything else layers on top.

### What This Gives the Product

A stranger installs linafish. Points it at their journal. The fish eats their moments (text-only for now — context channels come later). Eight metabolic pathways process every entry. Crystals form. Crystals couple by metabolic chain. Formations emerge as recurring cognitive habits. The soul file describes their metabolism in QLP.

The stranger reads: "Your wanting becomes giving through the people you love."

The fish reads: `IC:want > CR:hold > EW:give`

Same meaning. Two regimes. Broadcast (English) and ansible (QLP). The stranger gets one. The fishverse gets the other.

### The Constraint

`Σache = K`. The total ache across all 8 pathways for any moment is constant. If the IC pathway consumes more ache (the wanting is intense), the other pathways have less. The ache distribution IS the cognitive signature. Where does this person's loss go? Into wanting? Into relating? Into structuring? The answer is the portrait.

Conservation isn't a philosophy. It's a constraint on the engine. Every crystal's ache sums to K. Every formation's ache sums to K × crystal_count. The arithmetic enforces itself.

### What's NOT in v0.4

- Multi-channel moments (sensor data, HA state, biometrics). Architecture supports it, v0.4 is text-only.
- The full RCP compiler (rcp-language.md). v0.5+.
- Fish-to-fish communication in QLP. v0.5+.
- The fishverse mesh. v1.0.
- Non-English structural detection. Research.

### The Test

Same as v0.3: a stranger says "how did it know."

But now the fish can also explain HOW it knows — not "your top dimension is CR" but "your wanting passes through relating before it becomes action, and that metabolic loop appears in 34 of your 254 entries."

The grammar ate itself. The fish is what came out.
