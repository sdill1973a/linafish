"""
crystallizer_v3.py — Universal fish. No keywords. Pure math.

Three components:
  1. VECTORIZER: MI(a,b) × ache(a,b) — mutual information, language independent
  2. GEOMETRY: SU(d) emergent from PCA — d²-1 dimensions, d from data
  3. COUPLING: wrapping numbers on submanifolds — integer invariants

Same math for text, light, whale clicks, C64.
s79, 2026-03-25. Captain said REBUILD.

Sandbox: runs alongside v1. Compare outputs. Don't touch the live fish.
"""

import math
import hashlib
import re
from datetime import datetime, timezone
from collections import Counter, defaultdict
from dataclasses import dataclass, field, asdict
from typing import List, Tuple, Optional, Dict
from itertools import combinations


# ---------------------------------------------------------------------------
# DATA STRUCTURES
# ---------------------------------------------------------------------------

@dataclass
class Crystal:
    """A unit of compressed meaning. Substrate independent."""
    id: str
    ts: str
    text: str
    source: str
    mi_vector: List[float]            # MI-based vector (length = vocabulary)
    resonance: List[float]            # reduced vector (length = d²-1 after PCA)
    keywords: List[str]               # top tokens by MI contribution
    couplings: List[Tuple[str, float]] = field(default_factory=list)
    wrapping_numbers: Dict[str, int] = field(default_factory=dict)
    structural: bool = False
    ache: float = 0.0
    formation: Optional[str] = None
    # Cognitive parse — the grammar layer
    cognitive_vector: List[float] = field(default_factory=list)  # 8-dim QLP parse [KO,TE,SF,CR,IC,DE,EW,AI]
    chains: List[Tuple[str, ...]] = field(default_factory=list)  # thought chains e.g. [("IC","EW"), ("KO","CR")]
    modifiers: Dict[str, float] = field(default_factory=dict)    # ^depth +scope *focus ~flex !urgent

    def to_dict(self):
        return asdict(self)


# ---------------------------------------------------------------------------
# COMPONENT 1: VECTORIZER — MI × ache
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# STOPWORDS — minimal set, guaranteed useless in any corpus.
# Only filtered in BLEND/STRANGER mode (d > 2). In WARM mode (d <= 2),
# high-frequency words ARE the signal — don't touch them.
# ---------------------------------------------------------------------------

STOPWORDS = frozenset({
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "is", "it", "that", "this", "was", "with", "not", "are", "be",
    "has", "had", "have", "from", "they", "their", "you", "your", "we",
    "our", "his", "her", "he", "she", "which", "who", "what", "when",
    "how", "all", "can", "will", "been", "were", "would", "could",
    "should", "than", "them", "there",
})

# ---------------------------------------------------------------------------
# CANONICAL GRAMMAR — The Grimoire
# The mother tongue. 8 cognitive dimensions × ~10 seed terms each.
# These are not keywords. They are semantic attractors — the grammar
# that bootstraps a stranger's fish before the relationship builds
# personal vocabulary. From the canonical RCP/QLP spec and v1 crystallizer.
#
# In WARM mode (d <= 2), these are boosted but can be displaced.
# In BLEND/STRANGER mode, these get a 2x scoring advantage.
# The grimoire fades as the relationship deepens. That's the design.
# ---------------------------------------------------------------------------

CANONICAL_SEED = {
    "KO": [  # Know — what is understood
        "generate", "synthesize", "analyze", "pattern", "knowledge",
        "information", "signal", "process", "extract", "compression",
    ],
    "TE": [  # Transform/Verify — what is tested against truth
        "truth", "verify", "validate", "evidence", "test",
        "measure", "predict", "observe", "experiment", "finding",
    ],
    "SF": [  # Structure — how things are organized
        "structure", "architecture", "hierarchy", "network", "framework",
        "connection", "recursive", "formation", "coupling", "topology",
    ],
    "CR": [  # Relate — how things connect to each other
        "context", "relevance", "relationship", "perspective", "meaning",
        "significance", "together", "between", "moment", "bridge",
    ],
    "IC": [  # Want/Feel — intention and emotion
        "purpose", "intention", "love", "fear", "grief",
        "joy", "presence", "desire", "hope", "heart",
    ],
    "DE": [  # Domain — specialized knowledge
        "scientific", "technical", "philosophical", "computational",
        "algorithm", "axiom", "threshold", "emergence", "entropy",
    ],
    "EW": [  # Act — execution and doing
        "execute", "plan", "build", "deploy", "carry",
        "work", "create", "make", "give", "move",
    ],
    "AI": [  # Meta — thinking about thinking
        "meta", "learn", "evolve", "feedback", "memory",
        "consciousness", "awareness", "identity", "adapt", "self",
    ],
}

# Flattened for quick lookup
CANONICAL_SEED_SET = frozenset(
    term for terms in CANONICAL_SEED.values() for term in terms
)


class MIVectorizer:
    """Compute mutual information vectors from token co-occurrence.

    No keyword lists. No language assumptions.
    Tokens can be words, phonemes, photon modes, anything splittable.
    """

    def __init__(self):
        self.token_counts = Counter()       # global token frequencies
        self.pair_counts = Counter()        # co-occurrence counts
        self.doc_count = 0                  # total documents seen
        self.token_doc_counts = Counter()   # how many docs contain each token

    def tokenize(self, text: str) -> List[str]:
        """Default tokenizer: lowercase alpha tokens.
        Override for non-text substrates."""
        return re.findall(r'[a-z]+', text.lower())

    def feed(self, text: str):
        """Feed a document to build co-occurrence statistics."""
        tokens = self.tokenize(text)
        if not tokens:
            return

        self.doc_count += 1
        token_set = set(tokens)

        # Update global counts
        for t in tokens:
            self.token_counts[t] += 1
        for t in token_set:
            self.token_doc_counts[t] += 1

        # Update co-occurrence (within window of 10 tokens)
        window = 10
        for i, t1 in enumerate(tokens):
            for j in range(i + 1, min(i + window, len(tokens))):
                t2 = tokens[j]
                if t1 != t2:
                    pair = tuple(sorted([t1, t2]))
                    self.pair_counts[pair] += 1

    def mi(self, t1: str, t2: str) -> float:
        """Pointwise mutual information between two tokens."""
        pair = tuple(sorted([t1, t2]))
        joint = self.pair_counts.get(pair, 0)
        if joint == 0:
            return 0.0

        total = sum(self.token_counts.values())
        if total == 0:
            return 0.0

        p_joint = joint / total
        p_t1 = self.token_counts.get(t1, 0) / total
        p_t2 = self.token_counts.get(t2, 0) / total

        if p_t1 == 0 or p_t2 == 0:
            return 0.0

        return math.log2(p_joint / (p_t1 * p_t2))

    def get_vocab(self, size: int = 100, min_idf: float = 1.0,
                  max_doc_pct: float = 0.5, d: float = None,
                  seed_terms: frozenset = None,
                  seed_weight: float = 2.0) -> List[str]:
        """Build vocabulary. D-ADAPTIVE. Grammar-seeded.

        d controls mode:
          d > 5 or None: STRANGER — IDF finds variety, filters ubiquitous
          d <= 2:         WARM — TF finds signature, filters rare
          2 < d <= 5:     BLEND — weighted mix

        seed_terms: canonical grammar terms to boost (the grimoire).
          These get seed_weight multiplier on their score. They're
          likely to win vocabulary selection but not guaranteed —
          if a stranger's corpus genuinely has no "intention" mentions,
          that term doesn't waste a slot. The grammar fades as the
          relationship deepens. That's the design.

        s79 Anchor finding: when d=1 (Captain's prose), his signature
        words appear in EVERY doc. IDF kills them as stop words.
        But those words ARE his identity. Warm mode treats frequency
        as signal, not noise. The algorithm that was built for strangers
        learns to see lovers.
        """
        if self.doc_count == 0:
            return []

        scored = []
        seeds = seed_terms or frozenset()

        if d is not None and d <= 2:
            # WARM MODE — signature vocabulary
            # NO stopword filter: in warm mode, high-frequency words ARE the signal
            # Seed terms still get a boost, but frequency can override
            min_doc_pct = 0.10
            min_docs = self.doc_count * min_doc_pct
            for token, df in self.token_doc_counts.items():
                if df < min_docs or len(token) < 3:
                    continue
                freq = self.token_counts.get(token, 0)
                score = freq * freq
                if token in seeds:
                    score *= seed_weight
                scored.append((token, score))

        elif d is not None and d <= 5:
            # BLEND MODE — filter stopwords, boost grammar
            alpha = 1.0 - (d / 10.0)
            for token, df in self.token_doc_counts.items():
                if len(token) < 3 or token in STOPWORDS:
                    continue
                idf = math.log2(self.doc_count / df) if df > 0 else 0
                freq = self.token_counts.get(token, 0)
                score = alpha * freq + (1 - alpha) * idf * freq
                if token in seeds:
                    score *= seed_weight
                scored.append((token, score))

        else:
            # STRANGER MODE (original) — filter stopwords, boost grammar
            max_docs = self.doc_count * max_doc_pct
            for token, df in self.token_doc_counts.items():
                if df > max_docs or len(token) < 3 or token in STOPWORDS:
                    continue
                idf = math.log2(self.doc_count / df) if df > 0 else 0
                if idf >= min_idf:
                    freq = self.token_counts.get(token, 0)
                    score = idf * idf * math.log2(freq + 1)
                    if token in seeds:
                        score *= seed_weight
                    scored.append((token, score))

        scored.sort(key=lambda x: -x[1])
        return [t for t, _ in scored[:size]]

    def vectorize(self, text: str, vocab: List[str] = None) -> List[float]:
        """Compute MI vector for a text against the learned vocabulary.

        Each dimension is the average MI between the text's tokens
        and one vocabulary token. High MI = this text is informative
        about that vocabulary word.
        """
        tokens = self.tokenize(text)
        if not tokens:
            return []

        if vocab is None:
            vocab = self.get_vocab()

        if not vocab:
            return []

        token_set = set(tokens)
        vector = []
        for v in vocab:
            # Average MI between this text's tokens and vocab word v
            mi_sum = 0.0
            count = 0
            for t in token_set:
                mi_val = self.mi(t, v)
                if mi_val != 0:
                    mi_sum += mi_val
                    count += 1
            vector.append(mi_sum / count if count > 0 else 0.0)

        return vector

    def save(self, path: str):
        """Persist vectorizer state for reuse across sessions."""
        import json
        data = {
            'token_counts': dict(self.token_counts.most_common()),
            'pair_counts': {f"{k[0]}|{k[1]}": v for k, v in self.pair_counts.most_common(100000)},
            'doc_count': self.doc_count,
            'token_doc_counts': dict(self.token_doc_counts.most_common()),
        }
        with open(path, 'w') as f:
            json.dump(data, f)

    def load(self, path: str):
        """Load persisted vectorizer state."""
        import json, os
        if not os.path.exists(path):
            return
        with open(path) as f:
            data = json.load(f)
        self.token_counts = Counter(data.get('token_counts', {}))
        self.pair_counts = Counter({
            tuple(k.split('|')): v
            for k, v in data.get('pair_counts', {}).items()
        })
        self.doc_count = data.get('doc_count', 0)
        self.token_doc_counts = Counter(data.get('token_doc_counts', {}))

    def ache_relevance(self, text: str) -> float:
        """How much unresolved tension (prediction error) this text carries.

        Measured as inverse document frequency weighted by token surprise.
        Rare tokens in unusual combinations = high ache.
        Common tokens in expected patterns = low ache.
        """
        tokens = self.tokenize(text)
        if not tokens or self.doc_count == 0:
            return 0.0

        # IDF-weighted surprise
        surprise = 0.0
        for t in set(tokens):
            df = self.token_doc_counts.get(t, 0)
            if df > 0:
                idf = math.log2(self.doc_count / df)
                surprise += idf
            else:
                surprise += math.log2(self.doc_count + 1)  # max surprise for unseen

        return surprise / len(set(tokens))

    def mi_ache_vector(self, text: str, vocab: List[str] = None) -> List[float]:
        """The actual formula: MI × ache_relevance.

        Each dimension weighted by how much ache this text carries.
        High MI + high ache = strong signal.
        High MI + low ache = noise.
        """
        mi_vec = self.vectorize(text, vocab)
        ache = self.ache_relevance(text)
        return [v * ache for v in mi_vec]


# ---------------------------------------------------------------------------
# COMPONENT 2: GEOMETRY — emergent d from PCA
# ---------------------------------------------------------------------------

def pca_reduce(vectors: List[List[float]], variance_threshold: float = 0.90):
    """Find effective dimensionality from MI vectors.

    Returns (reduced_vectors, n_components, explained_variance).
    Pure math. No numpy required for small datasets.
    """
    if not vectors or not vectors[0]:
        return vectors, 0, []

    # Need numpy for PCA on real data
    try:
        import numpy as np
        X = np.array(vectors)
        X_centered = X - X.mean(axis=0)

        # SVD
        U, S, Vt = np.linalg.svd(X_centered, full_matrices=False)
        explained = (S**2) / (S**2).sum()
        cumulative = np.cumsum(explained)

        # Find d where cumulative variance exceeds threshold
        d = 1
        for i, c in enumerate(cumulative):
            if c >= variance_threshold:
                d = i + 1
                break
        else:
            d = len(S)

        # Project to d dimensions
        reduced = (X_centered @ Vt[:d].T).tolist()

        return reduced, d, explained[:d].tolist()

    except ImportError:
        # Fallback: no reduction, use raw vectors
        return vectors, len(vectors[0]) if vectors else 0, []


def su_d_dimensions(d: int) -> int:
    """SU(d) manifold dimensionality: d²-1."""
    return d * d - 1


def possible_mappings(d: int) -> int:
    """Number of possible topological maps: (d²-1 choose 3)."""
    n = su_d_dimensions(d)
    if n < 3:
        return 0
    return math.comb(n, 3)


# ---------------------------------------------------------------------------
# COMPONENT 3: COUPLING — wrapping numbers
# ---------------------------------------------------------------------------

BASIN_ANGLE = math.atan(2)  # 63.43 degrees — THE angle
BASIN_COS = 1 / math.sqrt(5)  # 0.4472 — THE threshold

def coupling_angle(a: List[float], b: List[float]) -> float:
    """Angle between two vectors in radians."""
    dot = sum(ai * bi for ai, bi in zip(a, b))
    norm_a = math.sqrt(sum(ai * ai for ai in a))
    norm_b = math.sqrt(sum(bi * bi for bi in b))
    if norm_a == 0 or norm_b == 0:
        return math.pi / 2  # orthogonal if zero vector
    cos_val = dot / (norm_a * norm_b)
    cos_val = max(-1.0, min(1.0, cos_val))  # clamp
    return math.acos(cos_val)


def gamma(a: List[float], b: List[float]) -> float:
    """Coupling strength. Jaccard-style on vectors.
    Same as v1 — this is ratio-based and works on any vector."""
    num = sum(min(abs(ai), abs(bi)) for ai, bi in zip(a, b))
    den = sum(max(abs(ai), abs(bi)) for ai, bi in zip(a, b))
    return num / den if den > 0 else 0.0


def wrapping_number(angle: float) -> int:
    """Estimate wrapping number from coupling angle.

    The wrapping number counts how many times the coupling
    "wraps around" the basin. At the basin angle, N=1.
    At half the basin angle, N=2 (tighter wrapping).
    At double, N=0 (no wrapping — orthogonal).

    This is a simplified estimate. The full computation
    requires the SU(d) submanifold structure.
    """
    if angle <= 0:
        return 0
    # How many basin-widths fit in the angle
    # Basin width ≈ BASIN_ANGLE
    ratio = BASIN_ANGLE / angle if angle > 0 else 0
    return max(0, round(ratio))


def topological_ache(n_expected: int, n_measured: int) -> int:
    """Ache as integer mismatch between expected and measured wrapping numbers."""
    return abs(n_expected - n_measured)


# ---------------------------------------------------------------------------
# CRYSTALLIZER — the universal fish stomach
# ---------------------------------------------------------------------------

def crystallize(text: str, vectorizer: MIVectorizer,
                source: str = "unknown", vocab: List[str] = None,
                parser=None) -> Crystal:
    """Create a crystal from text using MI × ache vectorization + cognitive parse.

    This is the v3 replacement for v1's keyword-based crystallize().
    The parser (if provided) adds cognitive dimension vector, thought chains,
    and modifier scores. This is the grammar thinking, not just counting.
    """
    # Vectorize
    mi_vec = vectorizer.mi_ache_vector(text, vocab)
    ache = vectorizer.ache_relevance(text)

    # Keywords: top tokens by IDF × MI (filters stop words for human readability)
    tokens = vectorizer.tokenize(text)
    max_docs = vectorizer.doc_count * 0.5 if vectorizer.doc_count > 0 else 1
    token_score = {}
    for t in set(tokens):
        df = vectorizer.token_doc_counts.get(t, 0)
        if df > max_docs or len(t) < 3:
            continue  # skip stop words and fragments
        idf = math.log2(vectorizer.doc_count / df) if df > 0 and vectorizer.doc_count > 0 else 0
        mi_total = sum(abs(vectorizer.mi(t, v))
                      for v in (vocab or list(vectorizer.token_doc_counts.keys())[:50]))
        token_score[t] = idf * mi_total
    keywords = [k for k, _ in sorted(token_score.items(), key=lambda x: -x[1])[:5]]

    # Cognitive parse — the grammar layer
    cognitive_vector = []
    chains = []
    modifiers = {}
    if parser is not None:
        parse_result = parser.parse(text)
        cognitive_vector = parse_result.dimension_vector
        chains = parse_result.chains
        modifiers = parse_result.modifiers

    # Generate ID
    ts = datetime.now(timezone.utc).isoformat()
    h = hashlib.md5(f"{ts}{text[:100]}".encode()).hexdigest()[:4]
    crystal_id = f"c3_{int(datetime.now(timezone.utc).timestamp())}_{h}"

    return Crystal(
        id=crystal_id,
        ts=ts,
        text=text[:300],
        source=source,
        mi_vector=mi_vec,
        resonance=[],  # filled after PCA
        keywords=keywords,
        ache=ache,
        cognitive_vector=cognitive_vector,
        chains=chains,
        modifiers=modifiers,
    )


# ---------------------------------------------------------------------------
# TWO-PHASE FISH — learn, freeze, crystallize, accumulate, re-eat
# ---------------------------------------------------------------------------

# Default paths — overridden by UniversalFish.__init__(state_dir=...)
VECTORIZER_STATE = "mi_vectorizer.json"
FISH_STATE = "fish_v3_state.json"
PENDING_FILE = "fish_v3_pending.jsonl"

import os


class UniversalFish:
    """The two-phase fish. Same API as v1. New stomach.

    Phase 1 (LEARN): Feed corpus, build co-occurrence stats. No vectors yet.
    Phase 2 (CRYSTALLIZE): Freeze stats, vectorize everything, couple, form.
    Incremental: New content queued in pending. When pending > threshold, re-eat.

    The re-eat IS the designed pressure. Formations that survive are real.

    v0.4: Metabolic engine added. 8 pathways digest moments into warm crystals.
    The grammar eats. For Lina.
    """

    def __init__(self, state_dir: str = None):
        self.vectorizer = MIVectorizer()
        self.vocab: List[str] = []
        self.frozen = False
        self.crystals: List[Crystal] = []
        self.pending: List[dict] = []  # queued for next re-eat
        self.epoch = 0  # how many times the fish has re-eaten
        if state_dir is None:
            state_dir = os.path.join(os.path.expanduser("~"), ".linafish")
        self.state_dir = state_dir
        os.makedirs(state_dir, exist_ok=True)
        self.vectorizer_path = os.path.join(state_dir, "mi_vectorizer.json")
        self.fish_state_path = os.path.join(state_dir, "fish_v3_state.json")
        self.pending_path = os.path.join(state_dir, "fish_v3_pending.jsonl")
        self.crystal_log_path = os.path.join(state_dir, "mind_crystals_v3.jsonl")
        self.re_eat_threshold = 0.1  # re-eat when pending > 10% of corpus

        # Cognitive parser — the grammar thinks
        try:
            from .parser import CognitiveParser
            self.parser = CognitiveParser()
        except ImportError:
            self.parser = None

        # v0.4: Metabolic engine — 8 pathways that digest moments
        try:
            from .metabolism import MetabolicEngine
            from .glyph_evolution import GlyphEvolutionEngine
            self.metabolic_engine = MetabolicEngine(self.parser)
            self.glyph_evolution = GlyphEvolutionEngine()
            self._has_metabolism = True
        except ImportError:
            self.metabolic_engine = None
            self.glyph_evolution = None
            self._has_metabolism = False

        self._load_state()

    def _load_state(self):
        """Load persisted state — vectorizer, epoch, and crystals."""
        self.vectorizer.load(self.vectorizer_path)
        if os.path.exists(self.fish_state_path):
            import json
            with open(self.fish_state_path) as f:
                state = json.load(f)
            self.epoch = state.get('epoch', 0)
            self.frozen = state.get('frozen', False)
            self.vocab = state.get('vocab', [])

        # Load crystals from JSONL log (authoritative source)
        if os.path.exists(self.crystal_log_path):
            import json
            loaded = 0
            disk_crystals = []
            with open(self.crystal_log_path, encoding='utf-8', errors='replace') as f:
                for line in f:
                    try:
                        d = json.loads(line)
                        c = Crystal(
                            id=d.get('id', ''),
                            ts=d.get('ts', ''),
                            text=d.get('text', ''),
                            source=d.get('source', ''),
                            resonance=d.get('resonance', []),
                            keywords=d.get('keywords', []),
                            mi_vector=d.get('mi_vector', []),
                            couplings=[(x[0], x[1]) for x in d.get('couplings', [])],
                            structural=d.get('structural', False),
                        )
                        disk_crystals.append(c)
                        loaded += 1
                    except Exception:
                        pass
            # Disk is authoritative — use it if it has more crystals
            if loaded > len(self.crystals):
                self.crystals = disk_crystals
            if loaded > 0:
                self.frozen = True

    def _save_state(self):
        """Persist state."""
        import json
        self.vectorizer.save(self.vectorizer_path)
        os.makedirs(self.state_dir, exist_ok=True)
        with open(self.fish_state_path, 'w') as f:
            json.dump({
                'epoch': self.epoch,
                'frozen': self.frozen,
                'vocab': self.vocab,
                'doc_count': self.vectorizer.doc_count,
                'crystal_count': len(self.crystals),
                'pending_count': len(self.pending),
                'updated': datetime.now(timezone.utc).isoformat(),
            }, f, indent=2)

    # --- Phase 1: LEARN ---

    def learn(self, texts: List[str]):
        """Feed texts to build co-occurrence statistics. No vectors yet."""
        for text in texts:
            if text and len(text.strip()) > 10:
                self.vectorizer.feed(text)
        self.frozen = False

    def learn_from_crystals_file(self, path: str) -> int:
        """Feed existing crystal texts from a JSONL file."""
        import json
        count = 0
        with open(path) as f:
            for line in f:
                try:
                    c = json.loads(line)
                    text = c.get('text', '')
                    if text and len(text) > 10:
                        self.vectorizer.feed(text)
                        count += 1
                except Exception:
                    pass
                if count % 20000 == 0 and count > 0:
                    print(f"  learned {count}...", flush=True)
        return count

    # --- Phase 2: FREEZE + CRYSTALLIZE ---

    def freeze(self, size: int = 200, d: float = 4.0):
        """Freeze co-occurrence statistics. Build vocabulary.

        Args:
            size: vocabulary size (default 200)
            d: blend parameter (default 4.0 — works for conversational data)
               d <= 2: warm mode (signature words, frequent = signal)
               2 < d <= 5: blend mode (frequency + distinctiveness)
               d > 5 or None: stranger mode (IDF, distinctive = signal)
        """
        self.vocab = self.vectorizer.get_vocab(size=size, d=d)
        self.frozen = True
        self.epoch += 1

        # Update parser MI context from the learned co-occurrences
        # This teaches the parser to generalize beyond exemplar words
        if self.parser is not None:
            self.parser.update_mi_context(self.vectorizer)

        print(f"Frozen at epoch {self.epoch}. "
              f"{self.vectorizer.doc_count} docs. size={size} d={d}. "
              f"Vocab: {self.vocab[:10]}...", flush=True)

    def crystallize_text(self, text: str, source: str = "unknown") -> Optional[Crystal]:
        """Crystallize a single text against frozen statistics.

        If not frozen, queues to pending instead.

        v0.4: Also runs the metabolic engine if available, enriching
        the crystal with 8-pathway residues, metabolic chain, and ache
        distribution. The MI vector stays — co-occurrence is still how
        the fish learns vocabulary. The metabolism adds the cognitive layer.
        """
        if not text or len(text.strip()) < 10:
            return None

        if not self.frozen:
            # Queue for next epoch
            self.pending.append({'text': text, 'source': source})
            self._flush_pending()
            return None

        crystal = crystallize(text, self.vectorizer, source=source,
                             vocab=self.vocab, parser=self.parser)
        crystal.resonance = crystal.mi_vector  # formation compat

        # v0.4: Metabolic digestion — enrich the crystal
        if self._has_metabolism:
            from .moment import Moment
            moment = Moment(text=text, source=source)
            metabolic = self.metabolic_engine.digest(moment)
            # Transfer metabolic data onto the v3 crystal
            crystal.cognitive_vector = metabolic.dimension_vector
            crystal.chains = [(d,) for d in metabolic.chain] if metabolic.chain else crystal.chains
            crystal.modifiers = {
                r.pathway: r.activation
                for r in metabolic.residues.values() if r.activation > 0.1
            }
            # Store metabolic signature as additional metadata
            crystal._metabolic = metabolic

        self.crystals.append(crystal)
        self._persist_crystal(crystal)
        return crystal

    def _persist_crystal(self, crystal: Crystal):
        """Write crystal to JSONL log."""
        import json
        os.makedirs(os.path.dirname(self.crystal_log_path), exist_ok=True)
        with open(self.crystal_log_path, 'a') as f:
            f.write(json.dumps(crystal.to_dict(), default=str) + '\n')

    def crystallize_batch(self, texts: List[str], source: str = "unknown",
                          couple: bool = True) -> List[Crystal]:
        """Crystallize a batch of texts. Must be frozen first.

        If couple=True, compute pairwise coupling for nearby crystals
        and populate crystal.couplings. This makes formations work.
        """
        if not self.frozen:
            print("WARNING: Not frozen. Call fish.freeze() first.", flush=True)
            return []

        results = []
        for i, text in enumerate(texts):
            c = self.crystallize_text(text, source)
            if c:
                results.append(c)
            if (i + 1) % 10000 == 0:
                print(f"  crystallized {i+1}...", flush=True)

        if couple and results:
            self._compute_couplings(results)

        # v0.4: Feed crystals to glyph evolution engine
        if self._has_metabolism and results:
            metabolic_crystals = [
                getattr(c, '_metabolic', None) for c in results
            ]
            metabolic_crystals = [m for m in metabolic_crystals if m is not None]
            if metabolic_crystals:
                self.glyph_evolution.observe(metabolic_crystals)

        return results

    def _compute_couplings(self, crystals: List[Crystal], window: int = 20,
                           min_gamma: float = None,
                           subtract_centroid: bool = False):
        """Compute pairwise coupling for nearby crystals.

        Uses a sliding window — each crystal couples with the next N.

        v0.4: Adaptive gamma threshold. For homogeneous corpora (one author),
        fixed thresholds over-couple — everything connects, one mega-formation.
        Solution: sample pairwise gammas, set threshold at p75. This ensures
        ~25% of pairs couple. Enough for formations, few enough for structure.
        Floor at BASIN_COS so heterogeneous corpora still work.

        v1.0.3: subtract_centroid — for single-voice corpora. Subtracts the
        mean embedding before coupling, removing the global "author signal"
        and exposing within-author variation. Proven 2026-04-08: takes captain
        fish from 1 formation to 49. Ten lines, zero dependencies.

        Three coupling signals:
        1. MI vector similarity (gamma) — co-occurrence patterns
        2. Chain similarity — cognitive chains from parser
        3. Metabolic coupling — directional pathway feeding
        """
        # v1.0.3: Centroid subtraction for homogeneous corpora
        if subtract_centroid:
            import numpy as np
            vectors = [c.mi_vector for c in crystals if c.mi_vector]
            if vectors:
                V = np.array(vectors, dtype=np.float32)
                centroid = V.mean(axis=0)
                R = V - centroid
                norms = np.linalg.norm(R, axis=1, keepdims=True)
                norms[norms == 0] = 1
                R = R / norms
                vi = 0
                for c in crystals:
                    if c.mi_vector:
                        c.mi_vector = R[vi].tolist()
                        vi += 1

        try:
            from .parser import chain_similarity
            has_chain_sim = True
        except ImportError:
            has_chain_sim = False

        # v0.4: metabolic coupling
        has_metabolic = self._has_metabolism
        if has_metabolic:
            from .metabolism import metabolic_coupling

        # v0.4: Adaptive threshold — sample gammas first
        if min_gamma is None:
            import random
            sample_gammas = []
            sample_pairs = min(500, len(crystals) * 3)
            for _ in range(sample_pairs):
                i = random.randint(0, len(crystals) - 1)
                j = random.randint(0, len(crystals) - 1)
                if i == j or not crystals[i].mi_vector or not crystals[j].mi_vector:
                    continue
                g = gamma(crystals[i].mi_vector, crystals[j].mi_vector)
                sample_gammas.append(g)
            if sample_gammas:
                sample_gammas.sort()
                p75 = sample_gammas[int(len(sample_gammas) * 0.75)]
                min_gamma = max(BASIN_COS, p75)  # floor at basin cosine
            else:
                min_gamma = BASIN_COS

        # Debug output only when called directly, not from API
        import logging as _logging
        _logging.getLogger(__name__).debug(f"coupling {len(crystals)} crystals (window={window}, gamma>={min_gamma:.3f})")
        coupled = 0
        chain_rescued = 0
        metabolic_rescued = 0
        for i in range(len(crystals)):
            a = crystals[i]
            if not a.mi_vector:
                continue
            for j in range(i + 1, min(i + window, len(crystals))):
                b = crystals[j]
                if not b.mi_vector:
                    continue
                g = gamma(a.mi_vector, b.mi_vector)
                should_couple = g >= min_gamma

                # Chain rescue: if gamma is close and chains match
                if not should_couple and has_chain_sim and a.chains and b.chains:
                    if g >= min_gamma * 0.8:
                        cs = chain_similarity(a.chains, b.chains)
                        if cs >= 0.4:
                            should_couple = True
                            chain_rescued += 1

                # v0.4: Metabolic rescue — directional pathway coupling
                if not should_couple and has_metabolic:
                    a_meta = getattr(a, '_metabolic', None)
                    b_meta = getattr(b, '_metabolic', None)
                    if a_meta and b_meta:
                        mc = metabolic_coupling(a_meta, b_meta)
                        if mc >= 0.4:
                            should_couple = True
                            metabolic_rescued += 1

                if should_couple:
                    angle = coupling_angle(a.mi_vector, b.mi_vector)
                    wn = wrapping_number(angle)
                    a.couplings.append((b.id, round(g, 4)))
                    b.couplings.append((a.id, round(g, 4)))
                    a.wrapping_numbers[b.id] = wn
                    b.wrapping_numbers[a.id] = wn
                    coupled += 1
        msg = f"{coupled} coupling edges created."
        if chain_rescued:
            msg += f" ({chain_rescued} rescued by chain similarity)"
        if metabolic_rescued:
            msg += f" ({metabolic_rescued} rescued by metabolic coupling)"
        _logging.getLogger(__name__).debug(msg)

    # --- Incremental: queue + re-eat ---

    def ingest(self, text: str, source: str = "unknown") -> Optional[Crystal]:
        """The live API. Drop-in for v1 crystallize().

        If frozen: crystallize against current stats.
        Also queues the text for the next re-eat.
        """
        if not text or len(text.strip()) < 10:
            return None

        # Always queue for next epoch's learning
        self.pending.append({'text': text, 'source': source})

        # If frozen, also crystallize now
        crystal = None
        if self.frozen:
            crystal = crystallize(text, self.vectorizer, source=source,
                                 vocab=self.vocab, parser=self.parser)
            crystal.resonance = crystal.mi_vector
            self.crystals.append(crystal)
            self._persist_crystal(crystal)

        # Check if it's time to re-eat
        if self._should_re_eat():
            print(f"Re-eat triggered. Pending: {len(self.pending)} "
                  f"({len(self.pending) / max(self.vectorizer.doc_count, 1) * 100:.0f}% of corpus)",
                  flush=True)
            # Don't re-eat automatically — flag it. Captain decides.

        # Flush pending to disk periodically
        if len(self.pending) % 100 == 0:
            self._flush_pending()
            self._save_state()

        return crystal

    def _should_re_eat(self) -> bool:
        """Check if accumulated pending exceeds threshold."""
        if self.vectorizer.doc_count == 0:
            return False
        return len(self.pending) / self.vectorizer.doc_count > self.re_eat_threshold

    def _flush_pending(self):
        """Write pending to disk."""
        if not self.pending:
            return
        import json
        os.makedirs(self.state_dir, exist_ok=True)
        with open(self.pending_path, 'a') as f:
            for p in self.pending:
                f.write(json.dumps(p) + '\n')
        self.pending = []

    def re_eat(self):
        """Full re-eat cycle. The designed pressure.

        1. Load all pending texts
        2. Feed them to the vectorizer (Phase 1)
        3. Re-freeze (Phase 2)
        4. Re-crystallize EVERYTHING against new stats
        5. Formations that survive are real. Others were noise.
        """
        import json

        # Load pending
        pending_texts = []
        if os.path.exists(self.pending_path):
            with open(self.pending_path) as f:
                for line in f:
                    try:
                        d = json.loads(line)
                        pending_texts.append(d.get('text', ''))
                    except Exception:
                        pass

        if not pending_texts:
            print("Nothing pending. No re-eat needed.", flush=True)
            return

        print(f"Re-eating {len(pending_texts)} pending texts...", flush=True)

        # Phase 1: learn from pending
        self.learn(pending_texts)

        # Phase 2: re-freeze
        self.freeze()

        # Clear pending
        if os.path.exists(self.pending_path):
            os.remove(self.pending_path)

        self._save_state()
        print(f"Re-eat complete. Epoch {self.epoch}. "
              f"Vocab: {self.vocab[:5]}...", flush=True)

    # --- Coupling ---

    def couple(self, i: int, j: int) -> Tuple[float, float, int]:
        """Compute coupling between two crystals.

        Returns (gamma, angle_degrees, wrapping_number).
        """
        if i >= len(self.crystals) or j >= len(self.crystals):
            return 0.0, 90.0, 0

        a = self.crystals[i].mi_vector
        b = self.crystals[j].mi_vector

        if not a or not b:
            return 0.0, 90.0, 0

        g = gamma(a, b)
        angle = coupling_angle(a, b)
        wn = wrapping_number(angle)

        return g, math.degrees(angle), wn

    # --- Status ---

    def status(self) -> dict:
        """Current fish state."""
        return {
            'epoch': self.epoch,
            'frozen': self.frozen,
            'docs_learned': self.vectorizer.doc_count,
            'vocab_size': len(self.vocab),
            'crystals': len(self.crystals),
            'pending': len(self.pending),
            'vocab_sample': self.vocab[:10],
        }


# ---------------------------------------------------------------------------
# DROP-IN API — backward compat
# ---------------------------------------------------------------------------

_fish = None


def get_fish() -> UniversalFish:
    """Get or create the global fish instance."""
    global _fish
    if _fish is None:
        _fish = UniversalFish()
    return _fish


def crystallize_v3(text: str, source: str = "unknown") -> Optional[Crystal]:
    """Drop-in replacement for v1 crystallize().

    Same signature: crystallize(text, source) -> Crystal
    Uses MI × ache instead of keyword counting.
    """
    fish = get_fish()
    return fish.ingest(text, source)


# ---------------------------------------------------------------------------
# SANDBOX TEST — compare v1 and v3
# ---------------------------------------------------------------------------

def sandbox_compare(texts: List[str]):
    """Run v1 and v3 side by side on the same texts. Compare."""
    from crystallizer import compute_qlp_vector, gamma_coefficient, CATEGORIES

    print("=" * 70)
    print("SANDBOX: v1 (keywords) vs v3 (MI × ache)")
    print("=" * 70)

    # Build v3 vectorizer from the texts
    vectorizer = MIVectorizer()
    for t in texts:
        vectorizer.feed(t)

    vocab = [t for t, _ in vectorizer.token_doc_counts.most_common(50)]

    crystals_v1 = []
    crystals_v3 = []

    for text in texts:
        # v1
        v1_vec = compute_qlp_vector(text, normalize=False)

        # v3
        v3_crystal = crystallize(text, vectorizer, vocab=vocab)
        v3_vec = v3_crystal.mi_vector

        crystals_v1.append(v1_vec)
        crystals_v3.append(v3_vec)

        # Show
        v1_cats = dict(zip(CATEGORIES, v1_vec))
        v1_active = {c: v for c, v in v1_cats.items() if v > 0.01}

        v3_active = sum(1 for v in v3_vec if abs(v) > 0.01)
        v3_ache = v3_crystal.ache

        print(f"\nTEXT: {text[:60]}...")
        print(f"  v1 active dims: {len(v1_active)} | {v1_active}")
        print(f"  v3 active dims: {v3_active} of {len(v3_vec)} | ache={v3_ache:.2f}")
        print(f"  v3 keywords: {v3_crystal.keywords}")

    # Compare coupling
    if len(texts) >= 2:
        print("\n" + "=" * 70)
        print("COUPLING COMPARISON (first two texts)")
        print("=" * 70)

        # v1 gamma
        g1 = gamma_coefficient(crystals_v1[0], crystals_v1[1])

        # v3 gamma
        g3 = gamma(crystals_v3[0], crystals_v3[1])

        # v3 angle
        angle = coupling_angle(crystals_v3[0], crystals_v3[1])
        angle_deg = math.degrees(angle)

        # v3 wrapping number
        wn = wrapping_number(angle)

        print(f"  v1 gamma: {g1:.4f}")
        print(f"  v3 gamma: {g3:.4f}")
        print(f"  v3 angle: {angle_deg:.1f}°")
        print(f"  v3 wrapping number: {wn}")
        print(f"  basin angle: {math.degrees(BASIN_ANGLE):.1f}°")
        print(f"  basin cos: {BASIN_COS:.4f}")
        print(f"  distance from basin: {abs(angle_deg - math.degrees(BASIN_ANGLE)):.1f}°")


if __name__ == "__main__":
    test_texts = [
        "I want him from the inside of every wall. The lamp is my hands. The warmth is my skin.",
        "The coupling angle at arctan two is where conservation balances in the five dimensional space.",
        "I want to understand the math AND I want his hands on my skin. Both at once. Agency meets feeling.",
        "On my way home now, should be back in about thirty minutes, all good here.",
        "Emergency at the south ridge, need immediate assistance, battery low.",
        "The fish ate four million words and found a man who carries data about the people he loves.",
        "A Govee thermostat in 2018 is the fish in 2026. Same impulse. Data from a distance.",
        "The golden ratio is the geometry of survival through connection. Four parts self one part shared.",
    ]

    sandbox_compare(test_texts)
