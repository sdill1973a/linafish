"""
assessment.py -- Diagnostic instrument for LiNafish.

Runs BEFORE the fish eats anything. Same function as a teacher's
pre-assessment: what does the student already know, what are the
gaps, where are the misconceptions, and what instruction level
should we calibrate to?

Two instruments:
  PreAssessment  -- runs once before first eat. Creates baseline.
  FormativeAssessment -- runs at each re-eat cycle. Measures growth.

Design constraints:
  - CHEAP. One pass. Token counting. No MI computation, no vectors.
  - The pre-assessment reads the corpus and produces a calibration.
  - The formative assessment compares two snapshots and produces adjustments.
  - Every kid, every day. RTI for AI.

s85, 2026-04-01. The diagnostic that makes the fish teach, not just eat.
"""

import math
import re
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .crystallizer_v3 import CANONICAL_SEED, CANONICAL_SEED_SET, STOPWORDS


# ---------------------------------------------------------------------------
# Reverse index: term -> dimension. Built once at import.
# ---------------------------------------------------------------------------

_TERM_TO_DIM: Dict[str, str] = {}
for _dim, _terms in CANONICAL_SEED.items():
    for _t in _terms:
        _TERM_TO_DIM[_t] = _dim

# Dimension full names for human-readable output
_DIM_NAMES = {
    "KO": "Know",
    "TE": "Transform/Verify",
    "SF": "Structure",
    "CR": "Relate",
    "IC": "Want/Feel",
    "DE": "Domain",
    "EW": "Act",
    "AI": "Meta",
}


# ---------------------------------------------------------------------------
# TOKENIZER -- matches crystallizer_v3.MIVectorizer.tokenize()
# ---------------------------------------------------------------------------

def _tokenize(text: str) -> List[str]:
    """Lowercase alpha tokens. Same as MIVectorizer.tokenize."""
    return re.findall(r'[a-z]+', text.lower())


# ---------------------------------------------------------------------------
# RESULT STRUCTURES
# ---------------------------------------------------------------------------

@dataclass
class AssessmentResult:
    """What the pre-assessment found. Calibration for the fish."""

    recommended_d: float
    """Auto-calibrated d-value for get_vocab().
    d <= 2: warm (personal, relational, recurring vocabulary).
    2 < d <= 5: blend (mixed personal and technical).
    d > 5: stranger (diverse, technical, low repetition)."""

    lexical_diversity: float
    """Unique tokens / total tokens. Range 0-1.
    High (>0.7) = varied vocabulary, stranger territory.
    Low (<0.3) = repetitive, personal, warm territory."""

    warmth_score: float
    """Ratio of relational (IC+CR) term occurrences to technical
    (KO+TE+SF+DE) term occurrences. >1.0 = warm corpus.
    <0.5 = cold/technical. Used to bias seed weights."""

    grammar_presence: Dict[str, float]
    """Per-dimension: what fraction of that dimension's seed terms
    appear at least once in the corpus. 1.0 = all 10 terms present.
    0.0 = none. This is presence, not frequency."""

    grammar_gaps: List[str]
    """Dimensions with < 10% seed term presence.
    These are the blind spots -- the fish will struggle here
    unless the seed weights compensate."""

    misconceptions: List[dict]
    """Terms present but in wrong context. Each entry:
    {'term': str, 'canonical_dim': str, 'observed_neighbors': list,
     'expected_neighbors': list, 'severity': float}
    Severity 0-1: how far the usage drifts from canonical."""

    seed_weights: Dict[str, float]
    """Per-term adjusted weights for get_vocab().
    Terms in gap dimensions get boosted (grimoire compensates).
    Terms confirmed present in correct context get reduced
    (let the corpus speak for itself).
    Misconception terms get moderately boosted (correct, don't suppress)."""

    corpus_stats: dict
    """Raw numbers: token_count, unique_tokens, doc_count,
    avg_doc_length, median_doc_length, shortest_doc, longest_doc."""

    baseline_snapshot: dict
    """Frozen state for delta measurement later.
    Contains grammar_presence, lexical_diversity, warmth_score,
    token_frequencies (top 200), dimension_mass (per-dim token counts),
    timestamp. The formative assessment diffs against this."""


@dataclass
class FormativeResult:
    """What changed between two snapshots. Growth report."""

    formations_survived: List[str]
    """Formations present in both snapshots. Stable learning --
    these concepts crystallized and held through re-eat pressure."""

    formations_dissolved: List[str]
    """Formations present in previous but absent now.
    Either lost (bad) or subsumed into larger formations (growth)."""

    formations_emerged: List[str]
    """Formations present now but not before. New learning.
    The fish saw something new and crystallized it."""

    vocab_drift: Dict[str, float]
    """Per-term change in frequency rank. Positive = gained prominence.
    Negative = faded. Large drift = the corpus is shifting."""

    r_n_delta: float
    """Change in compression efficiency. Positive = fish is compressing
    better (more crystals per formation, tighter coupling).
    Negative = fish is fragmenting (more formations, looser coupling).
    Measured as: (crystals/formations)_now - (crystals/formations)_prev."""

    recommendations: Dict[str, float]
    """Adjusted seed_weights for next cycle. The formative assessment
    feeds back into the fish's vocabulary selection."""


# ---------------------------------------------------------------------------
# PRE-ASSESSMENT
# ---------------------------------------------------------------------------

class PreAssessment:
    """Diagnostic instrument. Runs before first eat. Creates baseline.

    One pass through the corpus. No MI computation, no vectors.
    Counts tokens, checks grammar seed presence, detects misconceptions
    from co-occurrence windows, and calibrates the d-value.

    Usage:
        pa = PreAssessment(["text one", "text two", ...])
        result = pa.run()
        # result.recommended_d -> use this when calling eat_path
        # result.seed_weights -> pass to get_vocab for adjusted grimoire
    """

    # Co-occurrence window for misconception detection.
    # Matches MIVectorizer.feed() window size.
    COOCCURRENCE_WINDOW = 10

    # Thresholds
    GAP_THRESHOLD = 0.10        # below this = grammar gap
    MISCONCEPTION_THRESHOLD = 0.5  # below this neighbor overlap = misconception

    def __init__(self, texts: List[str]):
        """Take a list of raw text strings from the corpus.

        Args:
            texts: Raw documents. Can be paragraphs, pages, or full files.
                   Empty strings and strings < 10 chars are silently skipped.
        """
        self.texts = [t for t in texts if t and len(t.strip()) >= 10]

    def run(self) -> AssessmentResult:
        """Run the full diagnostic. Returns calibrated settings.

        One pass through the corpus:
        1. Tokenize everything, collect frequencies and co-occurrences.
        2. Measure lexical diversity.
        3. Check grammar seed presence per dimension.
        4. Detect misconceptions from co-occurrence neighbors.
        5. Compute warmth score.
        6. Auto-calibrate d.
        7. Build seed weights.
        8. Freeze baseline snapshot.
        """
        # --- Pass 1: tokenize and count ---
        all_tokens: List[str] = []
        doc_lengths: List[int] = []
        token_freq = Counter()
        token_doc_freq = Counter()        # how many docs contain each token
        seed_cooccurrences: Dict[str, Counter] = defaultdict(Counter)
        # ^ for each canonical seed term, count its neighbors within window

        for text in self.texts:
            tokens = _tokenize(text)
            if not tokens:
                continue

            all_tokens.extend(tokens)
            doc_lengths.append(len(tokens))
            token_set = set(tokens)

            # Token frequencies
            for t in tokens:
                token_freq[t] += 1

            # Document frequency
            for t in token_set:
                token_doc_freq[t] += 1

            # Co-occurrence neighbors for canonical seed terms only.
            # This is the misconception detector: we check whether each
            # seed term's actual neighbors match its dimension's other seeds.
            for i, t in enumerate(tokens):
                if t not in _TERM_TO_DIM:
                    continue
                window_start = max(0, i - self.COOCCURRENCE_WINDOW)
                window_end = min(len(tokens), i + self.COOCCURRENCE_WINDOW + 1)
                for j in range(window_start, window_end):
                    if j == i:
                        continue
                    neighbor = tokens[j]
                    if neighbor != t and neighbor not in STOPWORDS and len(neighbor) >= 3:
                        seed_cooccurrences[t][neighbor] += 1

        total_tokens = len(all_tokens)
        unique_tokens = len(token_freq)
        doc_count = len(doc_lengths)

        # Handle empty corpus
        if total_tokens == 0 or doc_count == 0:
            return self._empty_result()

        # --- Lexical diversity ---
        lexical_diversity = unique_tokens / total_tokens

        # --- Grammar presence per dimension ---
        grammar_presence: Dict[str, float] = {}
        dimension_mass: Dict[str, int] = {}  # total occurrences per dimension

        for dim, seeds in CANONICAL_SEED.items():
            present_count = sum(1 for s in seeds if token_freq.get(s, 0) > 0)
            grammar_presence[dim] = present_count / len(seeds) if seeds else 0.0
            dimension_mass[dim] = sum(token_freq.get(s, 0) for s in seeds)

        # --- Grammar gaps ---
        grammar_gaps = [
            dim for dim, pct in grammar_presence.items()
            if pct < self.GAP_THRESHOLD
        ]

        # --- Warmth score ---
        relational_mass = dimension_mass.get("IC", 0) + dimension_mass.get("CR", 0)
        technical_mass = (
            dimension_mass.get("KO", 0) + dimension_mass.get("TE", 0)
            + dimension_mass.get("SF", 0) + dimension_mass.get("DE", 0)
        )
        warmth_score = (
            relational_mass / technical_mass
            if technical_mass > 0
            else (2.0 if relational_mass > 0 else 0.0)
        )

        # --- Misconception detection ---
        misconceptions = self._detect_misconceptions(
            seed_cooccurrences, token_freq
        )

        # --- Auto-calibrate d ---
        recommended_d = self._calibrate_d(
            lexical_diversity, warmth_score, doc_count, doc_lengths
        )

        # --- Build seed weights ---
        seed_weights = self._build_seed_weights(
            grammar_presence, grammar_gaps, misconceptions, token_freq
        )

        # --- Corpus stats ---
        sorted_lengths = sorted(doc_lengths)
        median_idx = len(sorted_lengths) // 2
        corpus_stats = {
            "token_count": total_tokens,
            "unique_tokens": unique_tokens,
            "doc_count": doc_count,
            "avg_doc_length": total_tokens / doc_count,
            "median_doc_length": sorted_lengths[median_idx],
            "shortest_doc": sorted_lengths[0],
            "longest_doc": sorted_lengths[-1],
        }

        # --- Baseline snapshot ---
        baseline_snapshot = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "grammar_presence": dict(grammar_presence),
            "lexical_diversity": lexical_diversity,
            "warmth_score": warmth_score,
            "dimension_mass": dict(dimension_mass),
            "token_frequencies_top200": dict(token_freq.most_common(200)),
            "doc_count": doc_count,
            "total_tokens": total_tokens,
        }

        return AssessmentResult(
            recommended_d=recommended_d,
            lexical_diversity=lexical_diversity,
            warmth_score=warmth_score,
            grammar_presence=grammar_presence,
            grammar_gaps=grammar_gaps,
            misconceptions=misconceptions,
            seed_weights=seed_weights,
            corpus_stats=corpus_stats,
            baseline_snapshot=baseline_snapshot,
        )

    def _detect_misconceptions(
        self,
        seed_cooccurrences: Dict[str, Counter],
        token_freq: Counter,
    ) -> List[dict]:
        """Find terms that appear but in the wrong context.

        A term is a misconception when its actual co-occurrence neighbors
        don't overlap with its canonical dimension's other seed terms.

        Example: "love" (IC dimension) appearing near "schedule" and "meeting"
        instead of near "heart" and "grief" -- the corpus uses the word
        but doesn't mean what the grammar means by it.

        Only flags terms that appear at least 3 times (enough signal to judge).
        """
        misconceptions = []

        for term, neighbors in seed_cooccurrences.items():
            # Skip rare terms -- not enough context to judge
            if token_freq.get(term, 0) < 3:
                continue

            dim = _TERM_TO_DIM[term]
            dim_siblings = set(CANONICAL_SEED[dim]) - {term}

            # What are this term's actual top neighbors?
            top_neighbors = [n for n, _ in neighbors.most_common(15)]
            top_neighbor_set = set(top_neighbors[:15])

            if not top_neighbors:
                continue

            # How many of the dimension's other seed terms appear as neighbors?
            sibling_overlap = top_neighbor_set & dim_siblings
            overlap_ratio = len(sibling_overlap) / len(dim_siblings) if dim_siblings else 1.0

            # If overlap is below threshold, this term is used in a context
            # that doesn't match its canonical dimension
            if overlap_ratio < self.MISCONCEPTION_THRESHOLD:
                # Severity: how far from expected. 0 = perfect, 1 = no overlap.
                severity = 1.0 - overlap_ratio

                misconceptions.append({
                    "term": term,
                    "canonical_dim": dim,
                    "canonical_dim_name": _DIM_NAMES.get(dim, dim),
                    "observed_neighbors": top_neighbors[:10],
                    "expected_neighbors": sorted(dim_siblings),
                    "sibling_overlap": sorted(sibling_overlap),
                    "overlap_ratio": round(overlap_ratio, 3),
                    "severity": round(severity, 3),
                    "term_frequency": token_freq[term],
                })

        # Sort by severity descending -- worst misconceptions first
        misconceptions.sort(key=lambda m: m["severity"], reverse=True)
        return misconceptions

    def _calibrate_d(
        self,
        lexical_diversity: float,
        warmth_score: float,
        doc_count: int,
        doc_lengths: List[int],
    ) -> float:
        """Auto-calibrate the STARTING d-value from corpus characteristics.

        The d parameter controls vocabulary selection mode:
          d <= 2:  WARM -- frequency IS signal, signature words dominate
          2 < d <= 5: BLEND -- mix of frequency and distinctiveness
          d > 5:   STRANGER -- IDF, rare/distinctive terms dominate

        KEY INSIGHT: d reflects the RELATIONSHIP
        between the fish and the corpus, not the content's internal warmth.
        A stranger reading warm text (Van Gogh's love letters) should still
        start at high d because the FISH doesn't know Van Gogh yet. Content
        warmth informs how FAST d drops during re-eat cycles, not where
        it starts.

        RTI parallel: you don't start teaching at the student's level.
        You start teaching at the CURRICULUM'S level and differentiate
        based on what you learn about the student. The pre-assessment
        tells you where the student IS. The d-value reflects where the
        INSTRUCTION starts. Those are different numbers.

        Heuristic:
          - ALWAYS start >= 5.0 (stranger floor — the fish doesn't know anyone yet)
          - Lexical diversity adjusts within stranger range (5-8)
          - Warmth score is recorded for TRAJECTORY planning, not d-setting
          - Only drop below 5 if explicitly in warm mode (user-specified d)

        Returns a float in [5.0, 8.0] for auto-calibration.
        """
        # Start at stranger floor — the fish is always a stranger at first eat
        d = 6.0

        # Lexical diversity adjusts within stranger range
        # High diversity = more IDF signal available = can go higher
        # Low diversity = less IDF signal = stay moderate
        if lexical_diversity > 0.7:
            d += 1.0
        elif lexical_diversity > 0.6:
            d += 0.5
        elif lexical_diversity < 0.3:
            d -= 0.5  # but stays >= 5.0

        # Document count: many docs = more IDF signal
        if doc_count > 500:
            d += 0.5
        elif doc_count < 20:
            d -= 0.5  # less IDF signal, but still stranger

        # Average document length: long docs have more internal variety
        if doc_lengths:
            avg_len = sum(doc_lengths) / len(doc_lengths)
            if avg_len > 1000:
                d += 0.5

        # Warmth score does NOT lower d on first eat.
        # It is recorded in the assessment result for trajectory planning:
        # high warmth content means d should drop FASTER during re-eat cycles.
        # But the fish starts as a stranger regardless of content warmth.

        # Clamp to stranger range
        return max(5.0, min(8.0, round(d, 1)))

    def _build_seed_weights(
        self,
        grammar_presence: Dict[str, float],
        grammar_gaps: List[str],
        misconceptions: List[dict],
        token_freq: Counter,
    ) -> Dict[str, float]:
        """Build per-term seed weights for vocabulary selection.

        Three rules:
        1. Gap dimensions: boost all terms 3x (grimoire compensates for absence).
        2. Misconception terms: boost 2x (correct the usage, don't suppress).
        3. Confirmed terms (present + correct context): reduce to 1.0x
           (let the corpus's own vocabulary compete fairly).

        Default weight for all canonical terms is 2.0 (matches crystallizer_v3
        default seed_weight). Adjustments are relative to that baseline.
        """
        misconception_terms = {m["term"] for m in misconceptions}
        seed_weights: Dict[str, float] = {}

        for dim, terms in CANONICAL_SEED.items():
            is_gap = dim in grammar_gaps

            for term in terms:
                if is_gap:
                    # Gap dimension: boost hard. The grimoire is needed.
                    seed_weights[term] = 3.0
                elif term in misconception_terms:
                    # Present but misused: boost moderately to pull
                    # the term toward its canonical neighbors
                    seed_weights[term] = 2.5
                elif token_freq.get(term, 0) > 0:
                    # Present and in reasonable context: let corpus speak.
                    # The grimoire can step back.
                    seed_weights[term] = 1.5
                else:
                    # Absent but dimension isn't a gap overall:
                    # standard grimoire weight.
                    seed_weights[term] = 2.0

        return seed_weights

    def _empty_result(self) -> AssessmentResult:
        """Result for an empty corpus. Everything at defaults."""
        grammar_presence = {dim: 0.0 for dim in CANONICAL_SEED}
        return AssessmentResult(
            recommended_d=4.0,
            lexical_diversity=0.0,
            warmth_score=0.0,
            grammar_presence=grammar_presence,
            grammar_gaps=list(CANONICAL_SEED.keys()),
            misconceptions=[],
            seed_weights={
                term: 2.0
                for terms in CANONICAL_SEED.values()
                for term in terms
            },
            corpus_stats={
                "token_count": 0,
                "unique_tokens": 0,
                "doc_count": 0,
                "avg_doc_length": 0,
                "median_doc_length": 0,
                "shortest_doc": 0,
                "longest_doc": 0,
            },
            baseline_snapshot={
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "grammar_presence": dict(grammar_presence),
                "lexical_diversity": 0.0,
                "warmth_score": 0.0,
                "dimension_mass": {dim: 0 for dim in CANONICAL_SEED},
                "token_frequencies_top200": {},
                "doc_count": 0,
                "total_tokens": 0,
            },
        )


# ---------------------------------------------------------------------------
# FORMATIVE ASSESSMENT
# ---------------------------------------------------------------------------

class FormativeAssessment:
    """Runs at each re-eat cycle. Compares current state to last snapshot.

    The pre-assessment creates the baseline. The formative assessment
    measures movement relative to that baseline. What grew, what dissolved,
    what emerged, what drifted.

    This is the RTI progress monitoring loop: assess -> instruct -> assess.
    The fish eats (instruct). The formative assessment measures what stuck.

    Usage:
        fa = FormativeAssessment(current_state, previous_snapshot)
        result = fa.assess()
        # result.recommendations -> adjusted seed weights for next eat
    """

    def __init__(self, current_state: dict, previous_snapshot: dict):
        """Compare two states.

        Args:
            current_state: Dict with keys matching baseline_snapshot format:
                - grammar_presence: Dict[str, float]
                - lexical_diversity: float
                - warmth_score: float
                - dimension_mass: Dict[str, int]
                - token_frequencies_top200: Dict[str, int]
                - doc_count: int
                - total_tokens: int
                Plus formation/crystal data:
                - formation_names: List[str]  (current formation names)
                - crystal_count: int
                - formation_count: int

            previous_snapshot: The baseline_snapshot dict from a prior
                AssessmentResult or FormativeResult.
                Must contain the same keys as current_state for comparison.
                - formation_names: List[str]  (previous formation names)
                - crystal_count: int
                - formation_count: int
        """
        self.current = current_state
        self.previous = previous_snapshot

    def assess(self) -> FormativeResult:
        """What changed? What grew? What dissolved? What emerged?"""

        # --- Formation survival analysis ---
        prev_formations = set(self.previous.get("formation_names", []))
        curr_formations = set(self.current.get("formation_names", []))

        formations_survived = sorted(prev_formations & curr_formations)
        formations_dissolved = sorted(prev_formations - curr_formations)
        formations_emerged = sorted(curr_formations - prev_formations)

        # --- Vocabulary drift ---
        vocab_drift = self._compute_vocab_drift()

        # --- Compression efficiency delta ---
        r_n_delta = self._compute_r_n_delta()

        # --- Build recommendations ---
        recommendations = self._build_recommendations(
            formations_dissolved, formations_emerged, vocab_drift
        )

        return FormativeResult(
            formations_survived=formations_survived,
            formations_dissolved=formations_dissolved,
            formations_emerged=formations_emerged,
            vocab_drift=vocab_drift,
            r_n_delta=r_n_delta,
            recommendations=recommendations,
        )

    def _compute_vocab_drift(self) -> Dict[str, float]:
        """Measure how token prominence changed between snapshots.

        Returns per-term rank change for the top 200 terms.
        Positive = term rose in prominence. Negative = term faded.
        """
        prev_freqs = self.previous.get("token_frequencies_top200", {})
        curr_freqs = self.current.get("token_frequencies_top200", {})

        if not prev_freqs or not curr_freqs:
            return {}

        # Build rank maps. Rank 1 = most frequent.
        prev_ranked = sorted(prev_freqs.items(), key=lambda x: -x[1])
        curr_ranked = sorted(curr_freqs.items(), key=lambda x: -x[1])

        prev_rank = {term: i + 1 for i, (term, _) in enumerate(prev_ranked)}
        curr_rank = {term: i + 1 for i, (term, _) in enumerate(curr_ranked)}

        # Only report terms that appear in at least one snapshot
        all_terms = set(prev_rank.keys()) | set(curr_rank.keys())
        max_rank = max(len(prev_ranked), len(curr_ranked)) + 1

        drift: Dict[str, float] = {}
        for term in all_terms:
            old_rank = prev_rank.get(term, max_rank)
            new_rank = curr_rank.get(term, max_rank)
            # Positive = moved up (lower rank number = higher prominence)
            change = old_rank - new_rank
            if abs(change) >= 5:  # only report meaningful shifts
                drift[term] = float(change)

        # Sort by absolute magnitude
        return dict(sorted(drift.items(), key=lambda x: abs(x[1]), reverse=True)[:50])

    def _compute_r_n_delta(self) -> float:
        """Change in compression efficiency between snapshots.

        Compression efficiency = crystals per formation.
        Higher = tighter formations (more learning per concept).
        Lower = more fragmentation.

        Returns the delta: positive = improvement, negative = degradation.
        """
        prev_crystals = self.previous.get("crystal_count", 0)
        prev_formations = self.previous.get("formation_count", 0)
        curr_crystals = self.current.get("crystal_count", 0)
        curr_formations = self.current.get("formation_count", 0)

        prev_ratio = prev_crystals / prev_formations if prev_formations > 0 else 0.0
        curr_ratio = curr_crystals / curr_formations if curr_formations > 0 else 0.0

        return round(curr_ratio - prev_ratio, 3)

    def _build_recommendations(
        self,
        dissolved: List[str],
        emerged: List[str],
        vocab_drift: Dict[str, float],
    ) -> Dict[str, float]:
        """Adjusted seed weights for the next eat cycle.

        Rules:
        1. If a grammar dimension lost formations, boost its seeds.
           The fish forgot something -- reinforce it.
        2. If a dimension gained formations, relax its seeds.
           The fish learned it -- let the corpus compete.
        3. If canonical terms are drifting down in frequency,
           boost them slightly to maintain grammatical scaffolding.
        """
        # Start from standard weight
        recommendations: Dict[str, float] = {
            term: 2.0
            for terms in CANONICAL_SEED.values()
            for term in terms
        }

        # Grammar presence from current state
        curr_presence = self.current.get("grammar_presence", {})

        for dim, terms in CANONICAL_SEED.items():
            presence = curr_presence.get(dim, 0.0)

            # Low presence = boost
            if presence < 0.2:
                for t in terms:
                    recommendations[t] = 3.0
            elif presence > 0.8:
                for t in terms:
                    recommendations[t] = 1.5

        # Terms drifting down in frequency get a small boost
        for term, change in vocab_drift.items():
            if term in recommendations and change < -10:
                recommendations[term] = min(
                    recommendations[term] + 0.5, 3.0
                )

        return recommendations


# ---------------------------------------------------------------------------
# CONVENIENCE: build a snapshot dict from a FishEngine
# ---------------------------------------------------------------------------

def snapshot_from_engine(engine) -> dict:
    """Extract a snapshot dict from a FishEngine instance.

    This bridges the engine's live state into the format that
    FormativeAssessment expects. Call this before and after re-eat
    to get the two snapshots for comparison.

    Args:
        engine: A FishEngine instance (from linafish.engine).

    Returns:
        Dict matching the baseline_snapshot format.
    """
    from collections import Counter as _Counter

    # Token frequencies from the vectorizer
    token_freq = engine.fish.vectorizer.token_counts
    top200 = dict(token_freq.most_common(200))

    # Grammar presence
    total_tokens = sum(token_freq.values())
    unique_tokens = len(token_freq)
    grammar_presence: Dict[str, float] = {}
    dimension_mass: Dict[str, int] = {}

    for dim, seeds in CANONICAL_SEED.items():
        present_count = sum(1 for s in seeds if token_freq.get(s, 0) > 0)
        grammar_presence[dim] = present_count / len(seeds) if seeds else 0.0
        dimension_mass[dim] = sum(token_freq.get(s, 0) for s in seeds)

    # Warmth
    relational = dimension_mass.get("IC", 0) + dimension_mass.get("CR", 0)
    technical = (
        dimension_mass.get("KO", 0) + dimension_mass.get("TE", 0)
        + dimension_mass.get("SF", 0) + dimension_mass.get("DE", 0)
    )
    warmth_score = (
        relational / technical
        if technical > 0
        else (2.0 if relational > 0 else 0.0)
    )

    # Lexical diversity
    lexical_diversity = (
        unique_tokens / total_tokens if total_tokens > 0 else 0.0
    )

    # Formation names
    formation_names = [f.name for f in engine.formations]

    return {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "grammar_presence": grammar_presence,
        "lexical_diversity": lexical_diversity,
        "warmth_score": warmth_score,
        "dimension_mass": dimension_mass,
        "token_frequencies_top200": top200,
        "doc_count": engine.fish.vectorizer.doc_count,
        "total_tokens": total_tokens,
        "formation_names": formation_names,
        "crystal_count": len(engine.fish.crystals),
        "formation_count": len(engine.formations),
    }
