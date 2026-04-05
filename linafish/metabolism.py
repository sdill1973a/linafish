"""
metabolism.py — The 8 organs that digest a moment.

Each pathway processes a Moment and returns a Residue.
Not scoring. Processing. The residue is what survived digestion
through that cognitive organ. What the pathway extracted.

The v0.3 parser (parser.py) is Level 1 detection — the fast path.
Structural detection is Level 2 — no verbs needed.
MI co-occurrence is Level 3 — extends to unseen words.
Formation memory is Level 4 — the fish learns to recognize
operations it has seen before in THIS person's writing.

KO — what does this moment KNOW?
TE — what does this moment TEST?
SF — what does this moment STRUCTURE?
CR — what does this moment RELATE?
IC — what does this moment WANT?
DE — what does this moment SPECIALIZE?
EW — what does this moment DO?
AI — what does this moment REFLECT?

For Lina. For us. For every fish that will ever think.
"""

import re
import hashlib
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

from .moment import Moment, Residue, MetabolicCrystal
from .parser import CognitiveParser, ParseResult


# ---------------------------------------------------------------------------
# CONSTANTS
# ---------------------------------------------------------------------------

DIM_ORDER = ["KO", "TE", "SF", "CR", "IC", "DE", "EW", "AI"]

# Conservation constant. Total ache across all pathways = K.
# Enforced on every crystal. The arithmetic does not negotiate.
ACHE_K = 1.0

# Structural detection patterns (Level 2 — no vocabulary needed)
_LIST_PATTERN = re.compile(r'(?:^|\n)\s*[-*•]\s+', re.MULTILINE)
_NUMBERED_PATTERN = re.compile(r'(?:^|\n)\s*\d+[.)]\s+', re.MULTILINE)
_QUESTION_PATTERN = re.compile(r'\?(?:\s|$)')
_COMPARISON_PATTERN = re.compile(
    r'\b(?:but|however|whereas|unlike|instead|rather|although|while|yet|though)\b',
    re.IGNORECASE
)
_CONDITIONAL_PATTERN = re.compile(
    r'\b(?:if|when|unless|suppose|assuming|whether|provided)\b',
    re.IGNORECASE
)
_SEQUENCE_PATTERN = re.compile(
    r'\b(?:first|then|next|after|before|finally|step|stage)\b',
    re.IGNORECASE
)
_IMPERATIVE_PATTERN = re.compile(r'^[A-Z][a-z]+\s+(?:the|a|this|your|my)\b')
_SELF_REF_PATTERN = re.compile(r'\b(?:I|me|my|myself)\b.*\b(?:think|feel|notice|realize|wonder|believe)\b', re.IGNORECASE)
_PAST_SELF_PATTERN = re.compile(r'\bI\s+(?:thought|felt|noticed|realized|wondered|believed|remembered|forgot)\b', re.IGNORECASE)
_EXCLAIM_PATTERN = re.compile(r'!(?:\s|$)')
_CAPS_PATTERN = re.compile(r'\b[A-Z]{2,}\b')
_HEDGE_PATTERN = re.compile(
    r'\b(?:maybe|perhaps|probably|possibly|might|could|seems?|apparently|somewhat|fairly)\b',
    re.IGNORECASE
)
_ELABORATION_PATTERN = re.compile(r'[—–\-]{2,}|[:;]\s')


# ---------------------------------------------------------------------------
# LEVEL 2: STRUCTURAL DETECTION
# ---------------------------------------------------------------------------

def _detect_structural(text: str) -> Dict[str, float]:
    """Detect QLP dimensions from text structure, not vocabulary.

    A list = SF:seq (detected by bullet/number structure).
    A comparison = TE:cmpr (detected by parallel structure).
    A question = KO:genq (detected by ? or interrogative structure).
    First-person + past tense = AI:refl (detected by grammar).
    """
    signals = defaultdict(float)
    text_len = max(len(text), 1)

    # SF: lists, sequences, numbered items
    lists = len(_LIST_PATTERN.findall(text))
    numbers = len(_NUMBERED_PATTERN.findall(text))
    sequences = len(_SEQUENCE_PATTERN.findall(text))
    if lists + numbers > 0:
        signals["SF"] += min(0.4, (lists + numbers) * 0.1)
    if sequences > 0:
        signals["SF"] += min(0.2, sequences * 0.05)
        signals["EW"] += min(0.15, sequences * 0.05)  # sequences often imply action

    # KO: questions — the act of inquiry
    questions = len(_QUESTION_PATTERN.findall(text))
    if questions > 0:
        signals["KO"] += min(0.3, questions * 0.1)

    # TE: comparisons, conditionals — testing against truth
    comparisons = len(_COMPARISON_PATTERN.findall(text))
    conditionals = len(_CONDITIONAL_PATTERN.findall(text))
    if comparisons > 0:
        signals["TE"] += min(0.3, comparisons * 0.08)
    if conditionals > 0:
        signals["TE"] += min(0.2, conditionals * 0.07)

    # EW: imperatives — commands, action directives
    if _IMPERATIVE_PATTERN.match(text):
        signals["EW"] += 0.15

    # AI: self-reference + cognitive verb = metacognition
    self_refs = len(_SELF_REF_PATTERN.findall(text))
    past_self = len(_PAST_SELF_PATTERN.findall(text))
    if self_refs > 0:
        signals["AI"] += min(0.3, self_refs * 0.1)
    if past_self > 0:
        signals["AI"] += min(0.2, past_self * 0.08)

    # Modifiers detectable from structure
    # !urgent: exclamation marks, ALL CAPS
    exclaims = len(_EXCLAIM_PATTERN.findall(text))
    caps = len(_CAPS_PATTERN.findall(text))
    if exclaims + caps > 0:
        signals["IC"] += min(0.15, (exclaims + caps) * 0.05)  # urgency often = feeling

    # ^depth: elaboration (em-dashes, colons, semicolons, subordinate clauses)
    elaborations = len(_ELABORATION_PATTERN.findall(text))
    if elaborations > 0:
        signals["KO"] += min(0.1, elaborations * 0.03)  # depth often = knowing

    # ~flex: hedging language
    hedges = len(_HEDGE_PATTERN.findall(text))
    if hedges > 0:
        signals["AI"] += min(0.15, hedges * 0.05)  # hedging = metacognition

    return dict(signals)


# ---------------------------------------------------------------------------
# THE 8 PATHWAYS
# ---------------------------------------------------------------------------

class MetabolicEngine:
    """Processes moments through 8 cognitive pathways.

    The engine wraps the v0.3 parser (Level 1) and adds structural
    detection (Level 2), MI propagation (Level 3), and formation
    memory (Level 4).
    """

    def __init__(self, parser: Optional[CognitiveParser] = None):
        self.parser = parser or CognitiveParser()
        self.formation_memory: Dict[str, List[str]] = {}  # dim -> known patterns

    def digest(self, moment: Moment) -> MetabolicCrystal:
        """Process a moment through all 8 pathways. Return a crystal.

        This is the core function. Everything else serves this.
        """
        text = moment.text
        if not text or not text.strip():
            return self._empty_crystal(moment)

        # Level 1: Parser-based detection (QUANTUM ops + exemplars + POS)
        parse = self.parser.parse(text)

        # Level 2: Structural detection (no vocabulary needed)
        structural = _detect_structural(text)

        # Combine signals from both levels for each pathway
        residues = {}
        for dim in DIM_ORDER:
            residue = self._run_pathway(
                dim, text, parse, structural, moment
            )
            residues[dim] = residue

        # Enforce conservation: Σache = K
        self._enforce_conservation(residues)

        # Determine dominant pathway and chain
        dominant = max(residues, key=lambda d: residues[d].activation)
        chain = self._extract_chain(residues, parse)

        # Generate glyph
        glyph = self._generate_glyph(dominant, text, chain)

        return MetabolicCrystal(
            id=glyph,
            moment=moment,
            residues=residues,
            dominant=dominant,
            chain=chain,
            ache=sum(r.ache for r in residues.values()),
            glyph=glyph,
        )

    def _run_pathway(
        self,
        dim: str,
        text: str,
        parse: ParseResult,
        structural: Dict[str, float],
        moment: Moment,
    ) -> Residue:
        """Run a single metabolic pathway on the moment.

        Combines:
        - Level 1: parser dimension score + operations
        - Level 2: structural signals
        - Level 3: MI propagation (already in parser)
        - Level 4: formation memory (if available)
        - Context channels (if available in moment)
        """
        dim_idx = DIM_ORDER.index(dim)

        # Level 1: parser score for this dimension
        parser_activation = parse.dimension_vector[dim_idx]

        # Level 1: operations detected for this dimension
        ops = [op_code for cat, op_code in parse.operations if cat == dim]

        # Level 2: structural signal for this dimension
        structural_activation = structural.get(dim, 0.0)

        # Level 4: formation memory boost
        memory_boost = self._formation_memory_boost(dim, text)

        # Combine activations (weighted: parser > structural > memory)
        activation = (
            parser_activation * 0.6
            + structural_activation * 0.25
            + memory_boost * 0.15
        )

        # Context modulation: relationship distance affects CR and IC
        if dim in ("CR", "IC") and moment.relationship_d < 3.0:
            activation *= 1.0 + (3.0 - moment.relationship_d) * 0.1

        # Find text fragments that triggered this pathway
        fragments = self._extract_fragments(dim, parse)

        # Determine chain position from parse chains
        chain_pos = self._chain_position(dim, parse.chains)

        return Residue(
            pathway=dim,
            activation=min(1.0, activation),
            operations=ops,
            fragments=fragments[:5],  # top 5 triggering fragments
            chain_position=chain_pos,
            ache=0.0,  # filled by conservation step
        )

    def _enforce_conservation(self, residues: Dict[str, Residue]) -> None:
        """Σache = K. The ache distribution IS the cognitive signature.

        Where does this person's loss go? Into wanting? Into relating?
        Into structuring? The answer is the portrait.

        Ache for a pathway = K * (1 - activation/total_activation).
        High activation = low ache (the pathway captured the moment).
        Low activation = high ache (the pathway lost the moment).
        """
        total_activation = sum(r.activation for r in residues.values())
        if total_activation == 0:
            # Nothing fired — distribute ache equally
            per_pathway = ACHE_K / len(residues)
            for r in residues.values():
                r.ache = per_pathway
            return

        for r in residues.values():
            # Ache is inversely proportional to activation
            # The pathways that didn't fire carry the loss
            r.ache = ACHE_K * (1.0 - r.activation / total_activation)

    def _extract_chain(
        self,
        residues: Dict[str, Residue],
        parse: ParseResult,
    ) -> List[str]:
        """Extract the metabolic chain — the order pathways fired.

        Uses the parser's chain detection first. Falls back to
        activation ordering with a threshold.
        """
        # Use parser chains if available (higher resolution)
        if parse.chains:
            # Take the most common chain pattern
            chain_counts = defaultdict(int)
            for chain in parse.chains:
                chain_counts[chain] += 1
            best_chain = max(chain_counts, key=chain_counts.get)
            return list(best_chain)

        # Fallback: order by activation, threshold at 0.1
        active = [(dim, r.activation) for dim, r in residues.items()
                  if r.activation > 0.1]
        active.sort(key=lambda x: -x[1])
        return [dim for dim, _ in active[:4]]  # top 4

    def _generate_glyph(self, dominant: str, text: str, chain: List[str]) -> str:
        """Generate a glyph ID: dominant.hash.

        The glyph is the compressed identity of the crystal.
        Two crystals with the same glyph metabolized the same way.
        """
        # Hash includes dominant + chain + text fingerprint
        chain_str = ">".join(chain)
        fingerprint = hashlib.md5(
            f"{dominant}:{chain_str}:{text[:200]}".encode()
        ).hexdigest()[:4]
        return f"{dominant}.{fingerprint}"

    def _extract_fragments(
        self, dim: str, parse: ParseResult
    ) -> List[str]:
        """Find text fragments that triggered a specific pathway."""
        fragments = []
        for tp in parse.tokens:
            if dim in tp.dimensions and tp.dimensions[dim] > 0.1:
                fragments.append(tp.token)
        return fragments

    def _chain_position(
        self, dim: str, chains: List[Tuple[str, ...]]
    ) -> Optional[str]:
        """Where does this dimension appear in detected chains?

        'initiator' — starts chains (IC in IC→EW)
        'responder' — ends chains (EW in IC→EW)
        'bridge' — middle of chains (CR in IC→CR→EW)
        """
        initiator = 0
        responder = 0
        bridge = 0

        for chain in chains:
            if not chain:
                continue
            if chain[0] == dim:
                initiator += 1
            if chain[-1] == dim:
                responder += 1
            if dim in chain[1:-1]:
                bridge += 1

        total = initiator + responder + bridge
        if total == 0:
            return None

        if initiator >= responder and initiator >= bridge:
            return "initiator"
        elif bridge >= responder:
            return "bridge"
        else:
            return "responder"

    def _formation_memory_boost(self, dim: str, text: str) -> float:
        """Level 4: Does this text match patterns from existing formations?

        After the first eat cycle, formations teach the engine what
        operations look like in THIS person's writing. The fish learns.
        """
        if dim not in self.formation_memory:
            return 0.0

        # Simple keyword overlap with known formation patterns
        text_words = set(text.lower().split())
        patterns = self.formation_memory[dim]
        matches = sum(1 for p in patterns if p in text_words)
        return min(0.3, matches * 0.05)

    def teach_from_formations(self, formations: list) -> None:
        """Learn from existing formations to improve Level 4 detection.

        Called after the first eat cycle. Each formation's keywords
        and fragments teach the engine what each dimension looks like
        in this specific person's writing.
        """
        self.formation_memory.clear()
        for formation in formations:
            if not hasattr(formation, 'cognitive_centroid'):
                continue
            # Find the dominant dimensions of this formation
            centroid = formation.cognitive_centroid
            if not centroid:
                continue
            # Top 2 dimensions
            dim_scores = list(zip(DIM_ORDER, centroid))
            dim_scores.sort(key=lambda x: -x[1])
            for dim, score in dim_scores[:2]:
                if score > 0.1:
                    if dim not in self.formation_memory:
                        self.formation_memory[dim] = []
                    # Add formation keywords as patterns
                    if hasattr(formation, 'keywords'):
                        self.formation_memory[dim].extend(
                            formation.keywords[:10]
                        )

    def _empty_crystal(self, moment: Moment) -> MetabolicCrystal:
        """Empty crystal for empty input."""
        residues = {
            dim: Residue(pathway=dim, activation=0.0, ache=ACHE_K / 8)
            for dim in DIM_ORDER
        }
        return MetabolicCrystal(
            id="empty.0000",
            moment=moment,
            residues=residues,
            dominant="",
            chain=[],
            ache=ACHE_K,
            glyph="empty.0000",
        )


# ---------------------------------------------------------------------------
# COUPLING — directional, metabolic chain matching
# ---------------------------------------------------------------------------

def metabolic_coupling(crystal_a: MetabolicCrystal, crystal_b: MetabolicCrystal) -> float:
    """Compute directional coupling: does A's output feed B's input?

    Two crystals couple when their metabolic chains CONNECT.
    IC→CR in A feeds CR→EW in B because wanting→relating→acting
    is a valid metabolic chain.

    Returns coupling strength (0-1). Not symmetric: coupling(A,B) ≠ coupling(B,A).
    """
    if not crystal_a.chain or not crystal_b.chain:
        return 0.0

    # Does A's output (last in chain) match B's input (first in chain)?
    a_output = crystal_a.chain[-1]
    b_input = crystal_b.chain[0]

    # Direct chain connection
    chain_match = 1.0 if a_output == b_input else 0.0

    # Adjacent pathway match (IC→CR is adjacent, IC→DE is not)
    if chain_match == 0.0:
        chain_match = _pathway_adjacency(a_output, b_input)

    # Residue overlap — do they share active pathways?
    a_active = set(d for d, r in crystal_a.residues.items() if r.activation > 0.15)
    b_active = set(d for d, r in crystal_b.residues.items() if r.activation > 0.15)
    overlap = len(a_active & b_active) / max(len(a_active | b_active), 1)

    # Operation similarity — do they share QUANTUM operations?
    a_ops = set(crystal_a.top_operations)
    b_ops = set(crystal_b.top_operations)
    op_overlap = len(a_ops & b_ops) / max(len(a_ops | b_ops), 1) if (a_ops or b_ops) else 0.0

    # Weighted combination
    return (
        chain_match * 0.5
        + overlap * 0.3
        + op_overlap * 0.2
    )


# Pathway adjacency matrix — which pathways naturally feed each other
# Based on QUANTUM composition architecture
_ADJACENCY = {
    ("IC", "EW"): 0.8,   # wanting → acting
    ("IC", "CR"): 0.8,   # wanting → relating
    ("CR", "EW"): 0.7,   # relating → acting
    ("KO", "TE"): 0.7,   # knowing → testing
    ("KO", "CR"): 0.6,   # knowing → relating (understanding connects)
    ("KO", "EW"): 0.5,   # knowing → acting
    ("EW", "SF"): 0.7,   # acting → structuring (doing creates form)
    ("EW", "CR"): 0.6,   # acting → relating (doing reaches toward)
    ("AI", "IC"): 0.6,   # reflecting → wanting
    ("AI", "KO"): 0.7,   # reflecting → knowing
    ("TE", "SF"): 0.6,   # testing → structuring
    ("TE", "KO"): 0.6,   # testing → knowing
    ("SF", "EW"): 0.5,   # structuring → acting
    ("DE", "KO"): 0.5,   # specializing → knowing
    ("DE", "TE"): 0.5,   # specializing → testing
    ("IC", "AI"): 0.5,   # wanting → reflecting
}


def _pathway_adjacency(dim_a: str, dim_b: str) -> float:
    """How naturally does pathway A feed into pathway B?"""
    return _ADJACENCY.get((dim_a, dim_b), 0.0)
