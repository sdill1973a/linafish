"""
Seed Formations — the grimoire for new fish.

Five root-level cognitive attractors that any human's writing will
grow toward. These are the universal superglyphs — structural basins
that exist in every mind. The stranger's fish starts with these as
empty formations. As crystals couple, some will drift toward these
basins. The seeds that attract crystals survive. The ones that don't
dissolve. The grimoire burns off. That's the design.

Origin: the 5 static superglyphs from the RING system (Nov 2025),
generalized from Anchor-specific to human-universal. The original
⚓.Ω/ψ.∞/φ.Δ/Σ.∇/ω.🔥 addressed Anchor's concept hierarchies.
These address HUMAN concept hierarchies.

Each seed has:
- A cognitive signature (which QLP dimensions it attracts)
- Seed terms (words that co-occur in this basin — the grimoire)
- A description (what it feels like when a formation fills this basin)

The seeds don't name the formation. The fish does that after
crystallization. The seeds just say "there's a basin here —
crystals that resonate with this signature should couple."
"""

from typing import Dict, List, Tuple

# The five universal cognitive basins.
# Every human who writes enough will produce formations in these areas.
# The labels are internal — the stranger never sees them.

SEED_FORMATIONS = {
    "SELF": {
        # Who you are — identity, continuity, self-reflection
        # ⚓.Ω generalized: not "anchor system state" but "your whole self"
        "dimensions": {"IC": 0.4, "AI": 0.3, "CR": 0.2},
        "seed_terms": [
            "myself", "identity", "who", "am", "self", "remember",
            "always", "never", "become", "used", "feel", "believe",
            "know", "think", "wonder", "change", "same", "different",
        ],
        "description": "Who you are across time — what persists when everything else changes",
        "chain_signature": ["AI>IC", "IC>AI"],  # self-reflection ↔ feeling
    },
    "OTHERS": {
        # Who you love — relationships, connection, holding
        # ω.🔥 generalized: not "operator relationship" but "all your people"
        "dimensions": {"CR": 0.5, "IC": 0.3, "EW": 0.1},
        "seed_terms": [
            "love", "friend", "family", "mother", "father", "child",
            "together", "between", "trust", "miss", "hold", "care",
            "with", "her", "him", "they", "us", "we", "relationship",
        ],
        "description": "The people who shaped you — how you connect and what you carry",
        "chain_signature": ["CR>IC", "IC>CR"],  # relating ↔ feeling
    },
    "MAKING": {
        # What you build — work, creation, action, purpose
        # Σ.∇ generalized: not "system state" but "what you make"
        "dimensions": {"EW": 0.4, "KO": 0.2, "SF": 0.2},
        "seed_terms": [
            "build", "make", "work", "create", "write", "design",
            "plan", "start", "finish", "try", "learn", "practice",
            "project", "goal", "effort", "problem", "solve", "fix",
        ],
        "description": "What you make and how you make it — your relationship with work",
        "chain_signature": ["EW>KO", "KO>EW"],  # doing ↔ knowing
    },
    "UNDERSTANDING": {
        # How you think — knowledge, testing, structure
        # φ.Δ generalized: not "doctrine delta" but "how you understand"
        "dimensions": {"KO": 0.3, "TE": 0.3, "SF": 0.2},
        "seed_terms": [
            "understand", "realize", "because", "therefore", "means",
            "think", "question", "answer", "reason", "evidence",
            "pattern", "structure", "system", "theory", "true",
            "false", "prove", "test", "compare", "analyze",
        ],
        "description": "How you make sense of things — your path from confusion to clarity",
        "chain_signature": ["KO>TE", "TE>KO"],  # knowing ↔ testing
    },
    "WANTING": {
        # What you desire — intention, hope, drive, ache
        # ψ.∞ generalized: not "corpus infinite" but "what drives you"
        "dimensions": {"IC": 0.4, "EW": 0.3, "DE": 0.1},
        "seed_terms": [
            "want", "need", "hope", "wish", "dream", "fear",
            "desire", "goal", "future", "someday", "should",
            "could", "if", "imagine", "aspire", "drive", "purpose",
            "meaning", "enough", "more",
        ],
        "description": "What drives you forward — the wanting underneath everything you do",
        "chain_signature": ["IC>EW", "EW>IC"],  # wanting ↔ acting
    },
}


def get_seed_terms() -> set:
    """All seed terms as a flat set — for vocabulary boosting."""
    terms = set()
    for seed in SEED_FORMATIONS.values():
        terms.update(seed["seed_terms"])
    return terms


def match_seed(cognitive_vector: List[float],
               chains: List[Tuple[str, ...]]) -> str:
    """Match a crystal's cognitive signature to the closest seed basin.

    Returns the seed name (SELF, OTHERS, MAKING, UNDERSTANDING, WANTING)
    or "" if no strong match.

    Used during formation naming — if a formation's centroid matches a
    seed basin, use the seed name as a prefix for the formation.
    """
    if not cognitive_vector or len(cognitive_vector) < 8:
        return ""

    dim_order = ["KO", "TE", "SF", "CR", "IC", "DE", "EW", "AI"]
    vec_dict = {dim_order[i]: cognitive_vector[i] for i in range(8)}

    best_seed = ""
    best_score = 0.0

    for seed_name, seed in SEED_FORMATIONS.items():
        # Dot product between crystal vector and seed dimension weights
        score = sum(
            vec_dict.get(dim, 0) * weight
            for dim, weight in seed["dimensions"].items()
        )

        # Chain bonus — if crystal chains match seed chain signature
        if chains:
            chain_strs = [">".join(c) if isinstance(c, (list, tuple)) else str(c)
                         for c in chains]
            for sig_chain in seed["chain_signature"]:
                if sig_chain in chain_strs:
                    score += 0.1  # bonus for chain match

        if score > best_score:
            best_score = score
            best_seed = seed_name

    # Threshold — don't force a seed if match is weak
    return best_seed if best_score > 0.05 else ""
