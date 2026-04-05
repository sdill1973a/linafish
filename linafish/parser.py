"""
LiNafish Cognitive Parser — the grammar thinks.

The 8 QLP dimensions are not keyword bins. They are cognitive lenses.
This parser assigns dimensions to tokens based on their ROLE in the
sentence — what they DO, not what they ARE.

"Mother held dying child" scores IC (wanting/feeling) and CR (relating)
not because "mother" or "held" appear in a keyword list, but because
a care-verb with a relational object is IC+CR by grammatical role.

No spaCy. No NLTK. No GPU. Runs on a Pentium 75 in a barn.
The canonical seed words are training examples, not dictionaries.
The parser generalizes from them using co-occurrence context.

The 8 dimensions (from qlp_is_cognitive_architecture_2026-01-14):
  KO = Know — what is understood, synthesized, analyzed
  TE = Transform/Verify — what is tested against truth
  SF = Structure — how things are organized
  CR = Relate — how things connect to each other
  IC = Want/Feel — intention and emotion
  DE = Domain — specialized knowledge
  EW = Act — execution and doing
  AI = Meta — thinking about thinking
"""

import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple


# ============================================================================
# DIMENSION DEFINITIONS — what each dimension SOUNDS LIKE
# ============================================================================
# These are not keyword lists. They are exemplar sets that teach the parser
# what context each dimension creates. The parser uses co-occurrence from
# the MI vectorizer to extend recognition beyond these seeds.

DIMENSION_EXEMPLARS = {
    "KO": {
        # Cognitive verbs — the act of knowing
        "verbs": {"know", "understand", "realize", "recognize", "discover",
                  "learn", "notice", "see", "find", "remember", "recall",
                  "analyze", "synthesize", "comprehend", "grasp", "perceive"},
        # Causal connectors — how knowledge chains
        "connectors": {"because", "therefore", "since", "thus", "hence",
                       "consequently", "so", "means", "implies", "proves"},
        # Evidence markers
        "markers": {"clearly", "obviously", "evidently", "apparently",
                    "indeed", "actually", "fact", "true", "certain"},
    },
    "TE": {
        # Comparison/testing verbs
        "verbs": {"compare", "test", "verify", "measure", "check",
                  "confirm", "validate", "prove", "disprove", "examine",
                  "evaluate", "assess", "judge", "question", "doubt"},
        # Conditional structures
        "connectors": {"if", "whether", "unless", "suppose", "assuming",
                       "hypothetically", "alternatively", "whereas", "unlike"},
        # Evidence language
        "markers": {"evidence", "data", "result", "finding", "proof",
                    "experiment", "observation", "hypothesis", "theory"},
    },
    "SF": {
        # Organizational verbs
        "verbs": {"organize", "arrange", "structure", "categorize", "group",
                  "sort", "order", "rank", "classify", "divide", "separate",
                  "combine", "merge", "nest", "contain", "include"},
        # Structural markers
        "connectors": {"first", "second", "third", "finally", "next",
                       "then", "above", "below", "within", "between",
                       "inside", "outside", "under", "over", "among"},
        "markers": {"layer", "level", "tier", "hierarchy", "framework",
                    "system", "network", "architecture", "pattern", "topology"},
    },
    "CR": {
        # Relational verbs
        "verbs": {"relate", "connect", "share", "meet", "join",
                  "belong", "accompany", "involve", "associate", "link",
                  "hold", "embrace", "touch", "carry", "tend"},
        # Relational prepositions — HIGH SIGNAL
        "connectors": {"with", "between", "together", "among", "alongside",
                       "toward", "for", "against", "beside", "through"},
        # Relational nouns
        "markers": {"mother", "father", "sister", "brother", "friend",
                    "daughter", "son", "child", "family", "partner",
                    "relationship", "bond", "connection", "people", "person"},
    },
    "IC": {
        # Wanting/feeling verbs — the act of desire and emotion
        "verbs": {"want", "need", "love", "fear", "hope", "wish",
                  "desire", "crave", "long", "miss", "ache", "grieve",
                  "hate", "adore", "cherish", "dread", "yearn", "feel"},
        # Emotional intensifiers
        "connectors": {"deeply", "fiercely", "desperately", "passionately",
                       "intensely", "overwhelmingly", "terribly", "madly"},
        # Emotional state markers
        "markers": {"heart", "soul", "pain", "joy", "grief", "anger",
                    "sadness", "happiness", "anxiety", "peace", "ache",
                    "love", "fear", "hope", "loss", "lonely", "alive"},
    },
    "DE": {
        # Technical/specialized verbs
        "verbs": {"implement", "configure", "deploy", "compute", "calculate",
                  "optimize", "compile", "execute", "debug", "refactor",
                  "diagnose", "prescribe", "formulate", "derive", "quantify"},
        # Technical connectors
        "connectors": {"specifically", "technically", "precisely", "formally",
                       "mathematically", "empirically", "statistically"},
        # Domain markers (detected by density, not individual words)
        "markers": {"algorithm", "equation", "variable", "parameter",
                    "function", "coefficient", "threshold", "vector",
                    "matrix", "protocol", "specification", "schema"},
    },
    "EW": {
        # Action verbs — doing, making, carrying
        "verbs": {"do", "make", "build", "create", "write", "give",
                  "take", "move", "carry", "bring", "send", "put",
                  "start", "stop", "run", "work", "try", "go",
                  "fight", "push", "pull", "break", "fix", "open"},
        # Sequential markers
        "connectors": {"then", "next", "after", "before", "while",
                       "during", "until", "once", "when", "immediately"},
        # Action nouns
        "markers": {"step", "action", "task", "plan", "goal",
                    "effort", "attempt", "work", "project", "mission"},
    },
    "AI": {
        # Metacognitive verbs — thinking about thinking
        "verbs": {"think", "wonder", "reflect", "consider", "ponder",
                  "contemplate", "reconsider", "question", "doubt",
                  "suspect", "believe", "assume", "suppose", "guess"},
        # Self-reference + hedging
        "connectors": {"actually", "honestly", "really", "perhaps",
                       "maybe", "probably", "possibly", "apparently",
                       "seemingly", "essentially", "fundamentally"},
        # Metacognitive markers
        "markers": {"myself", "self", "mind", "thought", "awareness",
                    "consciousness", "identity", "perspective", "meta",
                    "insight", "realization", "reflection", "memory"},
    },
}

# Flatten for quick lookup: word -> set of dimensions it exemplifies
_EXEMPLAR_INDEX: Dict[str, Set[str]] = defaultdict(set)
for _dim, _groups in DIMENSION_EXEMPLARS.items():
    for _group_words in _groups.values():
        for _word in _group_words:
            _EXEMPLAR_INDEX[_word].add(_dim)


def _stem_simple(word: str) -> str:
    """Minimal stemmer — strips common English inflections for exemplar lookup.
    NOT a full stemmer. Just enough to match 'realized' -> 'realize',
    'loving' -> 'love', 'connected' -> 'connect'.
    """
    w = word.lower()
    if len(w) <= 4:
        return w
    # -ing (but not 'ring', 'king', 'thing')
    if w.endswith("ing") and len(w) > 5:
        base = w[:-3]
        # loving -> lov -> love (add e)
        if base + "e" in _EXEMPLAR_INDEX:
            return base + "e"
        # running -> run (double consonant)
        if len(base) > 2 and base[-1] == base[-2]:
            stripped = base[:-1]
            if stripped in _EXEMPLAR_INDEX:
                return stripped
        if base in _EXEMPLAR_INDEX:
            return base
    # -ed
    if w.endswith("ed") and len(w) > 4:
        base = w[:-2]
        if base in _EXEMPLAR_INDEX:
            return base
        # realized -> realiz -> realize (add e)
        if base + "e" in _EXEMPLAR_INDEX:
            return base + "e"
        # carried -> carri -> carry (not handled, acceptable loss)
    # -s / -es
    if w.endswith("es") and len(w) > 4:
        base = w[:-2]
        if base in _EXEMPLAR_INDEX:
            return base
    elif w.endswith("s") and len(w) > 4:
        base = w[:-1]
        if base in _EXEMPLAR_INDEX:
            return base
    # -ly (strip for adverb -> adjective check)
    if w.endswith("ly") and len(w) > 5:
        base = w[:-2]
        if base in _EXEMPLAR_INDEX:
            return base
    return w


# ============================================================================
# LIGHTWEIGHT POS TAGGER — suffix/position heuristics
# ============================================================================
# No external deps. English-focused but degrades gracefully on other langs
# (unknown words get dimension from context, not from POS).

# Verb suffixes (high confidence)
_VERB_SUFFIXES = ("ing", "ed", "ize", "ise", "ify", "ate")
# Noun suffixes
_NOUN_SUFFIXES = ("tion", "sion", "ment", "ness", "ity", "ence", "ance",
                  "ism", "ist", "dom", "ship", "hood")
# Adjective suffixes
_ADJ_SUFFIXES = ("ful", "less", "ous", "ive", "able", "ible", "ical", "ial")
# Adverb suffix
_ADV_SUFFIX = "ly"

# Common auxiliary/modal verbs (function words, not content)
_AUXILIARIES = frozenset({
    "is", "am", "are", "was", "were", "be", "been", "being",
    "has", "have", "had", "having",
    "do", "does", "did",
    "will", "would", "shall", "should",
    "can", "could", "may", "might", "must",
})

# Pronouns by type
_SELF_PRONOUNS = frozenset({"i", "me", "my", "mine", "myself",
                             "we", "us", "our", "ours", "ourselves"})
_OTHER_PRONOUNS = frozenset({"you", "your", "yours", "yourself",
                              "he", "him", "his", "she", "her", "hers",
                              "they", "them", "their", "theirs",
                              "it", "its"})

# Relational prepositions — strong CR signal
_RELATIONAL_PREPS = frozenset({"with", "between", "among", "beside",
                                "alongside", "toward", "towards", "against",
                                "together", "for"})

# Stopwords that carry no cognitive signal
_STOPWORDS = frozenset({
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to",
    "of", "not", "no", "this", "that", "these", "those",
    "very", "just", "also", "too", "so", "as", "than",
})


def _guess_pos(token: str) -> str:
    """Guess part-of-speech from suffix patterns.
    Returns: 'verb', 'noun', 'adj', 'adv', 'pron_self', 'pron_other',
             'prep_rel', 'aux', 'stop', 'unknown'
    """
    t = token.lower()

    if t in _STOPWORDS:
        return "stop"
    if t in _AUXILIARIES:
        return "aux"
    if t in _SELF_PRONOUNS:
        return "pron_self"
    if t in _OTHER_PRONOUNS:
        return "pron_other"
    if t in _RELATIONAL_PREPS:
        return "prep_rel"

    # Suffix heuristics (only for words long enough)
    if len(t) > 4:
        if t.endswith(_ADV_SUFFIX) and len(t) > 5:
            return "adv"
        for suffix in _VERB_SUFFIXES:
            if t.endswith(suffix):
                return "verb"
        for suffix in _NOUN_SUFFIXES:
            if t.endswith(suffix):
                return "noun"
        for suffix in _ADJ_SUFFIXES:
            if t.endswith(suffix):
                return "adj"

    return "unknown"


# ============================================================================
# PARSE RESULT
# ============================================================================

@dataclass
class TokenParse:
    """A single token with its cognitive dimension assignments."""
    token: str
    pos: str  # guessed POS tag
    dimensions: Dict[str, float]  # dim -> score (0-1)


@dataclass
class ParseResult:
    """Full parse of a text through the cognitive grammar."""
    tokens: List[TokenParse]
    # Aggregated 8-dim vector (sum of all token dimension scores, normalized)
    dimension_vector: List[float]  # [KO, TE, SF, CR, IC, DE, EW, AI]
    # Detected thought chains (sequences of dimension transitions)
    chains: List[Tuple[str, ...]]  # e.g. [("IC", "EW"), ("KO", "CR")]
    # Modifier scores
    modifiers: Dict[str, float]  # ^depth, +scope, *focus, ~flex, !urgent
    # QUANTUM operations detected (category:op_code pairs)
    operations: List[Tuple[str, str]] = field(default_factory=list)  # e.g. [("CR", "rel"), ("IC", "grief")]
    # Operation chains (higher resolution than dimension chains)
    op_chains: List[str] = field(default_factory=list)  # e.g. ["CR:rel>IC:grief>EW:build"]

    # Dimension names in canonical order
    DIM_ORDER = ["KO", "TE", "SF", "CR", "IC", "DE", "EW", "AI"]


# ============================================================================
# THE PARSER
# ============================================================================


# ============================================================================
# QUANTUM OPERATIONS — full cognitive grammar at operation level
# ============================================================================
# Import the QUANTUM operation set. This gives us verb -> (category, op_code)
# mapping for ~400 english verbs across 8 categories. The parser detects these
# in natural text to assign operation-level precision (CR:rel not just CR).

try:
    from .quantum_operations import VERB_TO_OPS, QUANTUM_OPS
    _HAS_QUANTUM = True
except ImportError:
    VERB_TO_OPS = {}
    QUANTUM_OPS = {}
    _HAS_QUANTUM = False


class CognitiveParser:
    """Parses text through the 8 QLP dimensions.

    Uses four signals:
    1. QUANTUM operation match — token maps to a specific operation (CR:rel, IC:grief)
    2. Direct exemplar match — token is in a dimension's exemplar set
    3. POS-based role inference — a verb near relational nouns = CR
    4. MI context propagation — tokens that co-occur with known
       dimension tokens inherit partial dimension scores

    The QUANTUM Framework (April 2025) is the origin grammar.
    The canonical seed trains the parser. Co-occurrence extends it.
    """

    def __init__(self, mi_context: Optional[Dict[str, Counter]] = None):
        """
        Args:
            mi_context: Optional co-occurrence data from MIVectorizer.
                Maps token -> Counter of neighbor tokens with MI scores.
                If provided, enables dimension propagation to unknown words.
        """
        self.mi_context = mi_context or {}
        # Cache: token -> dimension scores (from MI propagation)
        self._propagation_cache: Dict[str, Dict[str, float]] = {}

    def update_mi_context(self, vectorizer) -> None:
        """Extract co-occurrence context from an MIVectorizer instance.

        Builds a map: for each known-dimension exemplar word, find its
        top co-occurring tokens and their MI scores. This teaches the
        parser what unknown words "sound like" dimensionally.
        """
        if not hasattr(vectorizer, 'pair_counts') or not vectorizer.pair_counts:
            return

        # For each exemplar word, find its strongest co-occurrences
        context = defaultdict(Counter)
        for (t1, t2), count in vectorizer.pair_counts.items():
            mi = vectorizer.mi(t1, t2)
            if mi > 0:
                if t1 in _EXEMPLAR_INDEX:
                    context[t1][t2] = mi
                if t2 in _EXEMPLAR_INDEX:
                    context[t2][t1] = mi

        self.mi_context = dict(context)
        self._propagation_cache.clear()

    def _propagate_dimensions(self, token: str) -> Dict[str, float]:
        """Infer dimension scores for an unknown token via MI context.

        If 'token' co-occurs strongly with IC exemplars like 'love' and
        'desire', it gets IC signal even though it's not in any list.
        This is how the grammar generalizes beyond the seed.
        """
        if token in self._propagation_cache:
            return self._propagation_cache[token]

        scores: Dict[str, float] = defaultdict(float)
        total_mi = 0.0

        # Check every exemplar word's co-occurrence with this token
        for exemplar, neighbors in self.mi_context.items():
            if token in neighbors:
                mi_score = neighbors[token]
                if mi_score > 0:
                    for dim in _EXEMPLAR_INDEX[exemplar]:
                        scores[dim] += mi_score
                    total_mi += mi_score

        # Normalize to 0-1 range
        if total_mi > 0:
            max_score = max(scores.values()) if scores else 1.0
            for dim in scores:
                scores[dim] /= max_score

        result = dict(scores)
        self._propagation_cache[token] = result
        return result

    def _detect_operation(self, token: str) -> Optional[Tuple[str, str]]:
        """Check if a token (or its stem) maps to a QUANTUM operation.
        Returns (category, op_code) or None.
        """
        if not _HAS_QUANTUM:
            return None

        t = token.lower()
        # Direct match
        if t in VERB_TO_OPS:
            return VERB_TO_OPS[t][0]  # first match (highest priority category)
        # Stemmed match
        stemmed = _stem_simple(t)
        if stemmed != t and stemmed in VERB_TO_OPS:
            return VERB_TO_OPS[stemmed][0]
        return None

    def _score_token(self, token: str, pos: str,
                     prev_token: Optional[str] = None,
                     next_token: Optional[str] = None) -> Dict[str, float]:
        """Score a single token across all 8 dimensions.

        Four layers:
        1. QUANTUM operation match (highest confidence — maps to specific op)
        2. Direct exemplar match (high confidence)
        3. POS + context inference (medium confidence)
        4. MI propagation (lower confidence, but catches unknown words)
        """
        t = token.lower()
        scores: Dict[str, float] = defaultdict(float)

        # Layer 0: QUANTUM operation match
        op = self._detect_operation(t)
        if op:
            cat, op_code = op
            scores[cat] += 1.0  # strong signal — matched a specific operation

        # Layer 1: Direct exemplar match (try raw token, then stemmed)
        lookup = t
        if t not in _EXEMPLAR_INDEX:
            stemmed = _stem_simple(t)
            if stemmed in _EXEMPLAR_INDEX:
                lookup = stemmed

        if lookup in _EXEMPLAR_INDEX:
            for dim in _EXEMPLAR_INDEX[lookup]:
                # Check which group it's in (verb/connector/marker)
                dim_data = DIMENSION_EXEMPLARS[dim]
                if lookup in dim_data.get("verbs", set()):
                    scores[dim] += 1.0  # verbs are strongest signal
                elif lookup in dim_data.get("connectors", set()):
                    scores[dim] += 0.7  # connectors are structural
                elif lookup in dim_data.get("markers", set()):
                    scores[dim] += 0.5  # markers are contextual

        # Layer 2: POS + context inference
        if not scores:  # only if Layer 1 didn't fire
            if pos == "verb":
                # Unknown verb near relational words = CR
                if prev_token and prev_token.lower() in _RELATIONAL_PREPS:
                    scores["CR"] += 0.4
                # Unknown verb with self-pronoun = IC or AI
                if prev_token and prev_token.lower() in _SELF_PRONOUNS:
                    scores["IC"] += 0.3
                    scores["AI"] += 0.2
                # Default: unknown verbs lean EW (action)
                if not scores:
                    scores["EW"] += 0.3

            elif pos == "pron_self":
                # Self-reference = IC + AI
                scores["IC"] += 0.3
                scores["AI"] += 0.3

            elif pos == "pron_other":
                # Other-reference = CR
                scores["CR"] += 0.4

            elif pos == "prep_rel":
                # Relational preposition = strong CR
                scores["CR"] += 0.6

            elif pos == "noun":
                # Nouns get dimension from context neighbors
                if prev_token:
                    prev_look = _stem_simple(prev_token.lower())
                    if prev_look in _EXEMPLAR_INDEX:
                        for dim in _EXEMPLAR_INDEX[prev_look]:
                            scores[dim] += 0.3
                if next_token:
                    next_look = _stem_simple(next_token.lower())
                    if next_look in _EXEMPLAR_INDEX:
                        for dim in _EXEMPLAR_INDEX[next_look]:
                            scores[dim] += 0.3

            elif pos == "adj":
                # Adjectives inherit from what they modify (next token)
                if next_token:
                    next_look = _stem_simple(next_token.lower())
                    if next_look in _EXEMPLAR_INDEX:
                        for dim in _EXEMPLAR_INDEX[next_look]:
                            scores[dim] += 0.3
                # Emotional adjectives lean IC
                scores["IC"] += 0.1

            elif pos == "adv":
                # Adverbs are modifiers — slight IC lean (intensity)
                scores["IC"] += 0.1

        # Layer 3: MI propagation (if available and Layers 1-2 gave little)
        if sum(scores.values()) < 0.3 and self.mi_context:
            propagated = self._propagate_dimensions(t)
            for dim, score in propagated.items():
                scores[dim] += score * 0.5  # attenuated — lower confidence

        return dict(scores)

    def _detect_chains(self, token_parses: List[TokenParse]) -> List[Tuple[str, ...]]:
        """Detect thought chains — dimension transitions within the text.

        A chain is a sequence of dominant dimensions across content tokens.
        IC → EW means "wanting leads to action."
        KO → CR means "knowing leads to relating."

        Chains are the cognitive signature. Two texts with the same chain
        pattern think the same way even if they use different words.
        """
        # Extract dominant dimension sequence (skip tokens with no signal)
        dim_sequence = []
        for tp in token_parses:
            if not tp.dimensions:
                continue
            dominant = max(tp.dimensions, key=tp.dimensions.get)
            # Only add if score is meaningful
            if tp.dimensions[dominant] >= 0.3:
                dim_sequence.append(dominant)

        if len(dim_sequence) < 2:
            return []

        # Collapse consecutive duplicates (IC IC IC EW → IC EW)
        collapsed = [dim_sequence[0]]
        for dim in dim_sequence[1:]:
            if dim != collapsed[-1]:
                collapsed.append(dim)

        # Extract bigram chains
        chains = []
        for i in range(len(collapsed) - 1):
            chain = (collapsed[i], collapsed[i + 1])
            if chain not in chains:
                chains.append(chain)

        # Also extract trigram chains if long enough
        if len(collapsed) >= 3:
            for i in range(len(collapsed) - 2):
                chain = (collapsed[i], collapsed[i + 1], collapsed[i + 2])
                if chain not in chains:
                    chains.append(chain)

        return chains

    def _detect_modifiers(self, text: str, tokens: List[str]) -> Dict[str, float]:
        """Detect QLP modifiers from text structure.

        ^depth: subordinate clauses, elaboration, nested structures
        +scope: conjunctions, lists, breadth markers
        *focus: specificity, precision, narrow reference
        ~flex: hedging, qualification, uncertainty
        !urgent: exclamation, emphasis, urgency markers
        """
        n = len(tokens)
        if n == 0:
            return {"^depth": 0, "+scope": 0, "*focus": 0, "~flex": 0, "!urgent": 0}

        lower = text.lower()

        # ^depth — subordination and elaboration
        depth_markers = {"because", "although", "whereas", "while", "since",
                        "therefore", "however", "moreover", "furthermore",
                        "specifically", "particularly", "essentially"}
        depth = sum(1 for t in tokens if t.lower() in depth_markers) / max(n, 1)
        # Also: long sentences = more depth
        depth += min(n / 50.0, 0.5)

        # +scope — breadth and conjunction
        scope_markers = {"and", "or", "also", "both", "either", "neither",
                        "various", "many", "several", "multiple", "all"}
        scope = sum(1 for t in tokens if t.lower() in scope_markers) / max(n, 1)
        # Lists (commas in non-trivial text)
        comma_count = text.count(",")
        scope += min(comma_count / max(n / 5, 1), 0.5)

        # *focus — specificity
        focus_markers = {"specifically", "exactly", "precisely", "only",
                        "particular", "certain", "specific", "this", "that"}
        focus = sum(1 for t in tokens if t.lower() in focus_markers) / max(n, 1)
        # Named entities (capitalized mid-sentence) = focus
        caps_mid = sum(1 for i, t in enumerate(tokens)
                      if i > 0 and t[0:1].isupper() and len(t) > 1)
        focus += min(caps_mid / max(n, 1), 0.3)

        # ~flex — hedging and uncertainty
        flex_markers = {"maybe", "perhaps", "possibly", "might", "could",
                       "probably", "somewhat", "rather", "quite", "seems",
                       "apparently", "roughly", "approximately"}
        flex = sum(1 for t in tokens if t.lower() in flex_markers) / max(n, 1)

        # !urgent — emphasis
        urgent = 0.0
        if "!" in text:
            urgent += 0.3
        # ALL CAPS words
        caps_words = sum(1 for t in tokens if t.isupper() and len(t) > 1)
        urgent += min(caps_words / max(n, 1), 0.4)
        # Repetition (same word 3+ times)
        word_counts = Counter(t.lower() for t in tokens if len(t) > 2)
        repeated = sum(1 for c in word_counts.values() if c >= 3)
        urgent += min(repeated * 0.15, 0.3)

        return {
            "^depth": min(depth, 1.0),
            "+scope": min(scope, 1.0),
            "*focus": min(focus, 1.0),
            "~flex": min(flex, 1.0),
            "!urgent": min(urgent, 1.0),
        }

    def parse(self, text: str) -> ParseResult:
        """Parse text through the 8 QLP dimensions.

        Returns dimension vector, thought chains, and modifier scores.
        This is the cognitive parse — not what words appear, but what
        cognitive operations the text performs.
        """
        # Tokenize (same as MIVectorizer for consistency)
        raw_tokens = re.findall(r'[a-zA-Z]+', text)
        if not raw_tokens:
            return ParseResult(
                tokens=[],
                dimension_vector=[0.0] * 8,
                chains=[],
                modifiers={"^depth": 0, "+scope": 0, "*focus": 0,
                          "~flex": 0, "!urgent": 0},
            )

        # Tag and score each token, collecting QUANTUM operations
        token_parses = []
        detected_ops = []  # (category, op_code) for each content token
        for i, token in enumerate(raw_tokens):
            pos = _guess_pos(token.lower())

            # Skip stopwords and auxiliaries for dimension scoring
            # (they still exist in the token list for context)
            if pos in ("stop", "aux"):
                token_parses.append(TokenParse(
                    token=token, pos=pos, dimensions={}
                ))
                continue

            prev_t = raw_tokens[i - 1] if i > 0 else None
            next_t = raw_tokens[i + 1] if i < len(raw_tokens) - 1 else None

            # Check for QUANTUM operation
            op = self._detect_operation(token)
            if op:
                detected_ops.append(op)

            dims = self._score_token(token.lower(), pos, prev_t, next_t)
            token_parses.append(TokenParse(
                token=token, pos=pos, dimensions=dims
            ))

        # Aggregate dimension vector
        dim_sums = defaultdict(float)
        dim_count = 0
        for tp in token_parses:
            for dim, score in tp.dimensions.items():
                dim_sums[dim] += score
            if tp.dimensions:
                dim_count += 1

        # Normalize: divide by content token count, clamp to [0, 1]
        divisor = max(dim_count, 1)
        dim_vector = []
        for dim in ParseResult.DIM_ORDER:
            val = dim_sums.get(dim, 0.0) / divisor
            dim_vector.append(min(val, 1.0))

        # Detect chains
        chains = self._detect_chains(token_parses)

        # Detect modifiers
        modifiers = self._detect_modifiers(text, raw_tokens)

        # Build operation chains (higher resolution than dimension chains)
        # Deduplicate consecutive same-category ops
        op_chains = []
        if len(detected_ops) >= 2:
            collapsed_ops = [detected_ops[0]]
            for op in detected_ops[1:]:
                if op != collapsed_ops[-1]:
                    collapsed_ops.append(op)
            # Build chain strings: "CR:rel>IC:grief>EW:build"
            if len(collapsed_ops) >= 2:
                chain_parts = [f"{cat}:{code}" for cat, code in collapsed_ops]
                op_chains.append(">".join(chain_parts))

        return ParseResult(
            tokens=token_parses,
            dimension_vector=dim_vector,
            chains=chains,
            modifiers=modifiers,
            operations=detected_ops,
            op_chains=op_chains,
        )


# ============================================================================
# CHAIN SIMILARITY — for coupling
# ============================================================================

def chain_similarity(chains_a: List[Tuple[str, ...]],
                     chains_b: List[Tuple[str, ...]]) -> float:
    """Similarity between two texts' thought chain signatures.

    Returns 0-1. Two texts with identical chain patterns score 1.0.
    Two texts with no overlapping chains score 0.0.

    This enables coupling based on HOW texts think, not WHAT they say.
    """
    if not chains_a or not chains_b:
        return 0.0

    set_a = set(chains_a)
    set_b = set(chains_b)

    # Jaccard on chain sets
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)

    return intersection / union if union > 0 else 0.0
