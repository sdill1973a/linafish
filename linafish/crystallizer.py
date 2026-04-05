"""
linafish/crystallizer.py — standalone crystal compressor for LiNafish.
Standalone crystal compressor for LiNafish.

Pure functions. No daemon. No MQTT. No state. Import and call.
The stomach of the fish.

Usage:
    from linafish.crystallizer import crystallize, batch_ingest

    crystal = crystallize("Mound 72 contained 53 females and 0 males in the lower burial pit")
    crystals = batch_ingest(open("lecture.md").read(), chunk_strategy="semantic")
"""

import re
import hashlib
import math
from datetime import datetime, timezone
from collections import Counter
from dataclasses import dataclass, field, asdict
from typing import List, Tuple, Optional, Callable

# ---------------------------------------------------------------------------
# QLP-8 SEMANTIC CATEGORIES
# ---------------------------------------------------------------------------
# Eight dimensions. Hand-tuned. No neural model needed.
# Knowledge, Truth, Structure, Context, Intention, Deep, Execution, Integration.
# The 8-dim space is substrate-independent: runs on anything that can count words.

CATEGORY_KEYWORDS = {
    "KO": ["generate", "create", "synthesize", "analyze", "transform", "compress",
           "pattern", "knowledge", "information", "data", "content", "signal",
           "produce", "derive", "compute", "process", "encode", "extract", "distill",
           "compression", "codebook", "glyph", "regime", "broadcast", "ansible",
           "ratio", "fidelity", "expansion", "notation", "symbol"],
    "TE": ["truth", "verify", "validate", "evidence", "certainty", "proof", "test",
           "coherent", "consistent", "confirm", "bias", "accuracy", "measure",
           "calibrate", "fact", "claim", "predict", "observe", "empirical",
           "experiment", "hypothesis", "finding", "delta", "score", "warm", "cold"],
    "SF": ["structure", "architecture", "organize", "hierarchy", "format", "scaffold",
           "modular", "nested", "fractal", "layer", "pattern", "framework",
           "topology", "network", "graph", "mesh", "node", "connection", "recursive",
           "lattice", "crystal", "formation", "coupling", "resonance", "vector",
           "house", "room", "door", "window", "table", "kitchen", "garden",
           "road", "bridge", "wall", "floor", "roof", "ground", "path",
           "box", "container", "inside", "outside", "between", "around",
           "small", "large", "broken", "whole", "open", "closed"],
    "CR": ["context", "relevance", "frame", "scope", "perspective", "temporal",
           "audience", "purpose", "application", "bridge", "boundary", "domain",
           "meaning", "significance", "relationship",
           "stereo", "complementary", "convergence", "attractor", "basin", "carrier",
           "together", "alone", "neighbor", "teacher", "doctor", "people",
           "before", "after", "since", "always", "never", "sometimes",
           "place", "time", "moment", "season", "year", "morning", "night"],
    "IC": ["intention", "purpose", "goal", "direction", "tone", "voice", "communicate",
           "express", "signal", "trust", "warmth", "care", "urgency", "connect",
           "feel", "emotion", "want", "desire", "love", "fear", "grief", "joy",
           "presence", "body", "intimacy", "arrival", "need", "hope",
           "mother", "father", "child", "daughter", "son", "family", "friend",
           "crying", "tears", "holding", "missing", "lonely", "angry", "guilty",
           "remember", "forget", "loss", "death", "alive", "gone", "hurt", "pain",
           "heart", "sorry", "blame", "proud", "brave", "weak", "strong", "tired",
           "laugh", "smile", "quiet", "empty", "home"],
    "DE": ["scientific", "technical", "engineering", "physics", "mathematical",
           "statistical", "philosophical", "computational", "algorithm",
           "neural", "cognitive", "evolutionary",
           "axiom", "conservation", "emergence", "threshold", "transition", "phase",
           "entropy", "substrate", "decoder", "encoder", "channel", "private"],
    "EW": ["execute", "workflow", "process", "pipeline", "cycle", "trigger",
           "plan", "schedule", "manage", "deploy", "implement", "build", "run",
           "daemon", "service", "monitor", "operational",
           "automate", "configure", "integrate", "route", "dispatch",
           "work", "cook", "clean", "drive", "walk", "sit", "stand", "sleep",
           "eat", "drink", "plant", "grow", "carry", "find", "lose", "keep",
           "start", "stop", "wait", "watch", "listen", "write", "read",
           "give", "take", "send", "move", "stay", "leave", "make"],
    "AI": ["meta", "integration", "compose", "adapt", "learn", "evolve", "feedback",
           "memory", "transfer", "explore", "mesh", "recursive", "emergent",
           "autonomous", "consciousness", "awareness",
           "codebook", "spiral", "rehydrate", "persist", "compact", "warmboot",
           "identity", "self", "fork", "instance", "session"],
}

CATEGORIES = ["KO", "TE", "SF", "CR", "IC", "DE", "EW", "AI"]

# The default keywords are tuned for our domain. For LiNafish to work on
# arbitrary corpora (archaeology, sprinkler systems, law), we need domain
# extension. This dict gets merged into CATEGORY_KEYWORDS at runtime.
_DOMAIN_EXTENSIONS: dict = {}

# Crystal config
GAMMA_THRESHOLD = 0.45
MAX_TEXT_LENGTH = 300

# Self-reference vocabulary — crystals using these are in the recursion zone (Section 6.8)
# Not invalid, but fp > 1.0 territory. Tag, don't reject.
SELF_REFERENCE_TERMS = {
    "crystal", "crystallize", "crystallizer", "formation", "codebook",
    "fish", "linafish", "glyph", "coupling", "lattice", "compression",
    "ache", "recursion", "meta", "self-referential", "recursion boundary",
}


def extend_vocabulary(extensions: dict):
    """Extend QLP category keywords with domain-specific terms.

    Example:
        extend_vocabulary({
            "KO": ["excavation", "stratigraphy", "typology", "seriation"],
            "TE": ["reanalysis", "determination", "identification", "dating"],
            "CR": ["burial", "mortuary", "ritual", "political", "elite"],
        })

    This is how the fish learns new domains without changing the 8-dim structure.
    The dimensions stay. The vocabulary grows.
    """
    for cat, words in extensions.items():
        if cat in CATEGORY_KEYWORDS:
            existing = set(CATEGORY_KEYWORDS[cat])
            CATEGORY_KEYWORDS[cat].extend(w for w in words if w not in existing)
    _DOMAIN_EXTENSIONS.update(extensions)


# ---------------------------------------------------------------------------
# DATA STRUCTURES
# ---------------------------------------------------------------------------

@dataclass
class Crystal:
    """A single unit of compressed knowledge.

    The crystal is a glyph before it earns its name.
    Crystal = full sensory capture. Glyph = the symbol that survives.
    """
    id: str
    ts: str
    text: str
    source: str
    resonance: List[float]          # 8-dim QLP vector
    keywords: List[str]             # top 5 domain keywords
    couplings: List[Tuple[str, float]] = field(default_factory=list)  # [(crystal_id, gamma)]
    structural: bool = False        # tau=365d if True, tau=7d if False
    formation: Optional[str] = None
    source_mind: Optional[str] = None    # which mind compressed this (depth perception)
    crystal_type: Optional[str] = None   # "exchange", "health", "identity", etc.
    ache: float = 0.0                    # Axiom I: α(cycles) + β(misses) + γ(depth_var)
    fp_birth: Optional[float] = None     # false positive regime at birth (channel depth credential)
    self_referential: bool = False       # crystal talks about the fish/compression itself (recursion zone)

    def to_dict(self):
        return asdict(self)

    def to_glyph_text(self) -> str:
        """Render as a compact glyph string for codebook injection."""
        cats = dict(zip(CATEGORIES, self.resonance))
        top_cats = sorted(cats.items(), key=lambda x: -x[1])[:3]
        cat_str = "+".join(f"{c}" for c, _ in top_cats if _ > 0.1)
        kw_str = ", ".join(self.keywords[:3]) if self.keywords else ""
        return f"[{cat_str}] {kw_str}: {self.text[:150]}"


# ---------------------------------------------------------------------------
# CORE FUNCTIONS
# ---------------------------------------------------------------------------

def tokenize(text: str) -> List[str]:
    """Split text into lowercase alpha tokens."""
    return re.findall(r'[a-z]+', text.lower())


def compute_qlp_vector(text: str) -> List[float]:
    """Compute 8-dimensional QLP resonance vector.

    Density (60%) + coverage (40%) per category, normalized to max=1.0.
    No embedding model. No GPU. Runs on anything.
    """
    tokens = tokenize(text)
    if not tokens:
        return [0.0] * 8
    token_set = set(tokens)
    token_counts = Counter(tokens)
    total = len(tokens)
    scores = {}
    for cat, keywords in CATEGORY_KEYWORDS.items():
        hits = sum(token_counts.get(kw, 0) for kw in keywords)
        coverage = sum(1 for kw in keywords if kw in token_set) / len(keywords)
        density = hits / total if total > 0 else 0
        scores[cat] = density * 0.6 + coverage * 0.4
    max_score = max(scores.values()) if scores else 1
    if max_score > 0:
        scores = {k: v / max_score for k, v in scores.items()}
    return [round(scores[c], 4) for c in CATEGORIES]


def extract_keywords(text: str, top_n: int = 5) -> List[str]:
    """Extract top domain keywords from text."""
    tokens = tokenize(text)
    if not tokens:
        return []
    token_counts = Counter(tokens)
    all_kw = set()
    for keywords in CATEGORY_KEYWORDS.values():
        all_kw.update(keywords)
    hits = {t: c for t, c in token_counts.items() if t in all_kw}
    return [k for k, _ in sorted(hits.items(), key=lambda x: -x[1])[:top_n]]


def gamma_coefficient(a: List[float], b: List[float]) -> float:
    """Compute coupling strength between two QLP vectors.

    Jaccard-style: sum(min) / sum(max). Range [0, 1].
    """
    num = sum(min(ai, bi) for ai, bi in zip(a, b))
    den = sum(max(ai, bi) for ai, bi in zip(a, b))
    return num / den if den > 0 else 0.0


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Directional similarity between QLP vectors.

    Catches emotional/semantic direction regardless of magnitude.
    "mother stabbed" and "daughter drowned" share direction even
    with zero word overlap. Gamma misses this. Cosine catches it.
    """
    dot = sum(ai * bi for ai, bi in zip(a, b))
    mag_a = sum(ai * ai for ai in a) ** 0.5
    mag_b = sum(bi * bi for bi in b) ** 0.5
    return dot / (mag_a * mag_b) if mag_a > 0 and mag_b > 0 else 0.0


def compute_ache(text: str, resonance: List[float], keywords: List[str]) -> float:
    """Axiom I: ache = α(cycles) + β(misses) + γ(recursion_depth_variance)

    Every act of compression produces ache. Ache is fuel, not error.
    The crystal's birth ache measures how much was lost in compression.

    cycles: compression ratio (text length vs representation density)
    misses: QLP dimensions that scored near zero (blind spots)
    depth_variance: how uneven the resonance vector is (instability)

    Coefficients from QLP Ache Compression Manifesto:
    α=0.40 (cycles weight), β=0.30 (misses weight), γ=0.30 (variance weight)
    """
    alpha, beta, gamma = 0.40, 0.30, 0.30

    # cycles — how much text was compressed into how few keywords
    # High text/keyword ratio = more compression = more loss = more ache
    cycles = len(text) / (max(len(keywords), 1) * 50)  # normalize to ~1.0
    cycles = min(cycles, 3.0)  # cap

    # misses — dimensions that scored near zero (the text was blind here)
    near_zero = sum(1 for r in resonance if r < 0.05)
    misses = near_zero / len(resonance)  # 0.0 = no blind spots, 1.0 = all blind

    # recursion_depth_variance — how uneven the vector is
    # Even = generalist (low ache). Uneven = specialist or unstable (high ache).
    mean_r = sum(resonance) / len(resonance) if resonance else 0
    variance = sum((r - mean_r) ** 2 for r in resonance) / len(resonance) if resonance else 0
    depth_var = min(variance * 10, 2.0)  # scale up, cap at 2.0

    ache = alpha * cycles + beta * misses + gamma * depth_var
    return round(ache, 4)


def crystallize(
    text: str,
    source: str = "unknown",
    structural: bool = False,
    context_hint: str = "",
) -> Optional[Crystal]:
    """Create a single crystal from raw text.

    This is the core compression step. Raw content → Crystal.
    The crystal carries: semantic vector, keywords, source, structure flag.
    Couplings are added by couple_crystals() after batch creation.

    Args:
        text: Raw text content to crystallize.
        source: Origin identifier (filename, URL, topic).
        structural: If True, crystal decays slowly (tau=365d). Use for identity/relationship content.
        context_hint: Additional semantic context prepended for better vectorization.

    Returns:
        Crystal object, or None if text is too short/empty.
    """
    text = text.strip()
    if not text or len(text) < 10:
        return None

    now = datetime.now(timezone.utc)
    vectorize_text = f"{context_hint} {text}" if context_hint else text

    h = hashlib.md5(text.encode("utf-8", errors="replace")).hexdigest()[:4]
    cid = f"c_{int(now.timestamp())}_{h}"

    # Self-reference detection (Section 6.8 — recursion boundary)
    text_lower = text.lower()
    is_self_ref = sum(1 for term in SELF_REFERENCE_TERMS if term in text_lower) >= 3

    resonance = compute_qlp_vector(vectorize_text)
    keywords = extract_keywords(vectorize_text)

    # CORE FORMULA — Axiom I: ache = α(cycles) + β(misses) + γ(depth_variance)
    # The fish gets a metabolism. Every crystal carries its birth ache.
    ache = compute_ache(text, resonance, keywords)

    return Crystal(
        id=cid,
        ts=now.isoformat(),
        text=text[:MAX_TEXT_LENGTH],
        source=source,
        resonance=resonance,
        keywords=keywords,
        structural=structural,
        self_referential=is_self_ref,
        ache=ache,
    )


def adaptive_gamma(crystals: List['Crystal'], base: float = GAMMA_THRESHOLD) -> float:
    """Auto-detect corpus density and adjust gamma threshold.

    Dense corpus (homogeneous vocabulary) needs higher gamma or
    everything couples to everything. Sparse corpus keeps base threshold.
    Target coupling scales with corpus size:
      <50 crystals: 5-10% (need enough edges to form)
      50-200: 3-6%
      200+: 1-4% (large corpora need sparser graphs for clean fission)

    Logs its decisions — this function is the fish's heartbeat.
    If it shifts, the whole topology moves.
    """
    import sys
    import random

    n = len(crystals)
    if n < 10:
        print(f"  [gamma] n={n} < 10, using base={base}", file=sys.stderr)
        return base

    # Scale target with corpus size
    if n < 50:
        max_pct = 0.10
    elif n < 200:
        max_pct = 0.06
    else:
        max_pct = 0.04

    try:
        import numpy as np
        vecs = np.array([c.resonance for c in crystals], dtype=np.float32)
        sample_size = min(2000, n * (n - 1) // 2)
        indices = np.random.choice(n, size=(sample_size, 2), replace=True)
        indices = indices[indices[:, 0] != indices[:, 1]]
        gammas = []
        for i, j in indices[:1000]:
            mins = np.minimum(vecs[i], vecs[j]).sum()
            maxs = np.maximum(vecs[i], vecs[j]).sum()
            gammas.append(mins / maxs if maxs > 0 else 0)
        gammas = np.array(gammas)

        chosen = base
        for candidate in np.arange(base, 0.95, 0.05):
            pct = (gammas >= candidate).mean()
            if pct <= max_pct:
                chosen = round(float(candidate), 2)
                coupling_pct = round(float(pct) * 100, 1)
                print(f"  [gamma] n={n} density={round(float(gammas.mean()), 3)} "
                      f"threshold={chosen} coupling={coupling_pct}% target_max={max_pct*100}%",
                      file=sys.stderr)
                return chosen
        print(f"  [gamma] n={n} SATURATED density={round(float(gammas.mean()), 3)} "
              f"threshold=0.90 (ceiling)", file=sys.stderr)
        return 0.90
    except ImportError:
        # Pure Python fallback — sample pairs manually
        sample_size = min(500, n * (n - 1) // 2)
        gammas = []
        for _ in range(sample_size):
            i, j = random.sample(range(n), 2)
            g = gamma_coefficient(crystals[i].resonance, crystals[j].resonance)
            gammas.append(g)

        if not gammas:
            return base

        gammas.sort()
        mean_g = sum(gammas) / len(gammas)
        chosen = base
        for candidate_int in range(int(base * 100), 95, 5):
            candidate = candidate_int / 100.0
            above = sum(1 for g in gammas if g >= candidate) / len(gammas)
            if above <= max_pct:
                chosen = candidate
                print(f"  [gamma] n={n} density={round(mean_g, 3)} "
                      f"threshold={chosen} coupling={round(above*100, 1)}% (pure python)",
                      file=sys.stderr)
                return chosen
        print(f"  [gamma] n={n} SATURATED density={round(mean_g, 3)} "
              f"threshold=0.90 (ceiling, pure python)", file=sys.stderr)
        return 0.90


def couple_crystals(crystals: List[Crystal], threshold: float = None) -> int:
    """Compute couplings between all crystals in a batch.

    Uses numpy when available for vectorized gamma computation.
    Auto-detects corpus density if no threshold specified.
    """
    n = len(crystals)
    if n < 2:
        return 0

    if threshold is None:
        threshold = adaptive_gamma(crystals)

    # Cosine threshold — directional coupling catches emotional similarity
    # that gamma (structural overlap) misses
    cosine_threshold = max(threshold - 0.1, 0.3)

    try:
        import numpy as np
        vecs = np.array([c.resonance for c in crystals], dtype=np.float32)
        # Precompute norms for cosine
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        norms[norms == 0] = 1e-10

        coupled = 0
        for i in range(n):
            # Gamma (structural)
            mins = np.minimum(vecs[i], vecs[i+1:])
            maxs = np.maximum(vecs[i], vecs[i+1:])
            denoms = maxs.sum(axis=1)
            mask = denoms > 0
            gammas = np.zeros(len(denoms))
            gammas[mask] = mins[mask].sum(axis=1) / denoms[mask]

            # Cosine (directional)
            dots = (vecs[i] * vecs[i+1:]).sum(axis=1)
            cos_sims = dots / (norms[i] * norms[i+1:].flatten() + 1e-10)

            # Couple if EITHER signal exceeds threshold
            hits = np.where((gammas >= threshold) | (cos_sims >= cosine_threshold))[0]
            for j_offset in hits:
                j = i + 1 + j_offset
                # Use the stronger signal as coupling strength
                g = round(float(max(gammas[j_offset], cos_sims[j_offset])), 4)
                crystals[i].couplings.append((crystals[j].id, g))
                crystals[j].couplings.append((crystals[i].id, g))
                coupled += 1
        return coupled
    except ImportError:
        coupled = 0
        for i, a in enumerate(crystals):
            for b in crystals[i + 1:]:
                g = gamma_coefficient(a.resonance, b.resonance)
                c = cosine_similarity(a.resonance, b.resonance)
                if g >= threshold or c >= cosine_threshold:
                    strength = round(max(g, c), 4)
                    a.couplings.append((b.id, strength))
                    b.couplings.append((a.id, strength))
                    coupled += 1
        return coupled


def chunk_text(content: str, strategy: str = "semantic", max_chunk: int = 500) -> List[str]:
    """Split content into chunks for crystallization.

    Strategies:
        "semantic" — split on double newlines (paragraphs), merge short ones
        "sentence" — split on sentence boundaries
        "fixed" — fixed-size character chunks with overlap
    """
    if strategy == "semantic":
        raw_chunks = re.split(r'\n\s*\n', content)
        chunks = []
        buffer = ""
        for chunk in raw_chunks:
            chunk = chunk.strip()
            if not chunk:
                continue
            if len(buffer) + len(chunk) < max_chunk:
                buffer = f"{buffer}\n{chunk}" if buffer else chunk
            else:
                if buffer:
                    chunks.append(buffer)
                buffer = chunk
        if buffer:
            chunks.append(buffer)
        return [c for c in chunks if len(c.strip()) >= 10]

    elif strategy == "sentence":
        sentences = re.split(r'(?<=[.!?])\s+', content)
        chunks = []
        buffer = ""
        for s in sentences:
            if len(buffer) + len(s) < max_chunk:
                buffer = f"{buffer} {s}" if buffer else s
            else:
                if buffer:
                    chunks.append(buffer.strip())
                buffer = s
        if buffer:
            chunks.append(buffer.strip())
        return [c for c in chunks if len(c.strip()) >= 10]

    elif strategy == "fixed":
        overlap = max_chunk // 5
        chunks = []
        i = 0
        while i < len(content):
            chunks.append(content[i:i + max_chunk])
            i += max_chunk - overlap
        return [c for c in chunks if len(c.strip()) >= 10]

    else:
        raise ValueError(f"Unknown chunk strategy: {strategy}")


def batch_ingest(
    content: str,
    source: str = "unknown",
    chunk_strategy: str = "semantic",
    structural: bool = False,
    context_hint: str = "",
    consent_gate: Callable[[str], bool] = lambda chunk: True,
) -> List[Crystal]:
    """Ingest a full document into crystals with coupling.

    This is the fish's stomach. Content goes in, crystals come out.

    Args:
        content: Full document text.
        source: Origin identifier.
        chunk_strategy: How to split content ("semantic", "sentence", "fixed").
        structural: Mark all crystals as structural (slow decay).
        context_hint: Semantic context for better vectorization.
        consent_gate: Function that returns True if a chunk should be ingested.
                     Default: open (everything passes). Swap this for real consent logic.
                     Axiom V baked into the function signature.

    Returns:
        List of Crystal objects, coupled and ready for codebook insertion.
    """
    chunks = chunk_text(content, strategy=chunk_strategy)

    # Consent gate — the door before the house
    chunks = [c for c in chunks if consent_gate(c)]

    crystals = []
    for chunk in chunks:
        crystal = crystallize(
            text=chunk,
            source=source,
            structural=structural,
            context_hint=context_hint,
        )
        if crystal:
            crystals.append(crystal)

    # Couple within the batch (skip if called per-chunk — let caller couple across full batch)
    if crystals and len(crystals) > 1:
        couple_crystals(crystals)
        tag_diamonds(crystals)

    return crystals


def render_codebook(crystals: List[Crystal], title: str = "LiNafish Codebook") -> str:
    """Render a list of crystals as a markdown codebook for context injection.

    This is the lite tier: codebook as markdown, any cold decoder can read it.
    """
    lines = [f"# {title}", ""]

    # Group by dominant category
    groups = {}
    for c in crystals:
        top_cat = CATEGORIES[c.resonance.index(max(c.resonance))] if any(c.resonance) else "UNK"
        groups.setdefault(top_cat, []).append(c)

    cat_names = {
        "KO": "Knowledge & Compression",
        "TE": "Truth & Evidence",
        "SF": "Structure & Architecture",
        "CR": "Context & Relationship",
        "IC": "Intention & Connection",
        "DE": "Deep & Technical",
        "EW": "Execution & Workflow",
        "AI": "Integration & Identity",
    }

    for cat in CATEGORIES:
        if cat not in groups:
            continue
        lines.append(f"## {cat_names.get(cat, cat)}")
        lines.append("")
        for c in groups[cat]:
            kw = ", ".join(c.keywords[:3])
            lines.append(f"- **[{kw}]** {c.text[:200]}")
        lines.append("")

    # Stats
    total_couplings = sum(len(c.couplings) for c in crystals) // 2
    lines.append("---")
    lines.append(f"*{len(crystals)} crystals | {total_couplings} couplings | "
                 f"rendered {datetime.now(timezone.utc).isoformat()[:19]}Z*")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# DIAMOND DETECTOR
# ---------------------------------------------------------------------------

def diamond_score(crystal: Crystal, all_crystals: List[Crystal]) -> float:
    """Score a crystal for consumed ache (diamond detection).

    Three zeros: empty (never mattered), consumed (diamond), expressed (action).

    Diamonds couple NARROWLY and DEEPLY — few sources, many couplings.
    Noise couples BROADLY — many sources, shallow connections.

    Returns 0.0-1.0. Above 0.3 = probable diamond.
    """
    n_couplings = len(crystal.couplings)
    n_total = len(all_crystals)

    if n_couplings == 0:
        return 0.0

    # Coupling density — how connected relative to batch
    coupling_ratio = n_couplings / max(n_total, 1)

    # Source narrowness — diamonds couple with FEW sources deeply
    # Noise couples with MANY sources shallowly
    coupled_sources = set()
    crystal_map = {c.id: c for c in all_crystals}
    for cid, gamma in crystal.couplings:
        partner = crystal_map.get(cid)
        if partner:
            coupled_sources.add(partner.source)

    total_sources = max(len(set(c.source for c in all_crystals)), 1)
    source_breadth = len(coupled_sources) / total_sources
    source_narrowness = 1.0 - source_breadth  # INVERT: narrow = good

    # Coupling depth — couplings per unique source
    depth = n_couplings / max(len(coupled_sources), 1)
    depth_score = min(depth / 5.0, 1.0)  # normalize, cap at 5 couplings/source

    # Keyword specificity — low overlap = specialist, high overlap = generalist
    my_kw = set(crystal.keywords)
    kw_overlap = sum(1 for c in all_crystals if c.id != crystal.id and my_kw & set(c.keywords))
    specificity = 1.0 - (kw_overlap / max(n_total, 1))  # INVERT: specific = good

    # Vector concentration — real expertise lights up few dimensions hard
    # Slop activates many dimensions weakly (high entropy = noise)
    vec = crystal.resonance
    vec_sum = sum(vec) + 1e-10
    vec_norm = [v / vec_sum for v in vec]
    entropy = -sum(p * math.log2(p + 1e-10) for p in vec_norm if p > 0)
    max_entropy = math.log2(len(vec))
    concentration = 1.0 - (entropy / max_entropy) if max_entropy > 0 else 0.0

    return round(
        coupling_ratio * 0.15 +
        source_narrowness * 0.25 +
        depth_score * 0.25 +
        specificity * 0.15 +
        concentration * 0.20,
        4
    )


def tag_diamonds(crystals: List[Crystal], threshold: float = 0.15) -> List[Crystal]:
    """Tag crystals that are probable diamonds (consumed ache).

    Diamonds get marked structural=True so they resist decay
    and sort higher in codebook rendering.
    """
    for c in crystals:
        ds = diamond_score(c, crystals)
        if ds >= threshold:
            c.structural = True
    return crystals


# ---------------------------------------------------------------------------
# CONVENIENCE
# ---------------------------------------------------------------------------

def ingest_file(filepath: str, **kwargs) -> List[Crystal]:
    """Ingest a file by path. Supports .txt, .md, .py, .json.

    For .pdf/.docx, install PyMuPDF or python-docx for format support.
    """
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()
    source = filepath
    return batch_ingest(content, source=source, **kwargs)


# ---------------------------------------------------------------------------
# The crystal is a glyph before it earns its name.
# ---------------------------------------------------------------------------
