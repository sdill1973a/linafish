"""
crystallizer_v3.py — Universal fish. No keywords. Pure math.

Three components:
  1. VECTORIZER: MI(a,b) × ache(a,b) — mutual information, language independent
  2. GEOMETRY: SU(d) emergent from PCA — d²-1 dimensions, d from data
  3. COUPLING: wrapping numbers on submanifolds — integer invariants

Same math for text, light, whale clicks, C64.
"""

import math
import hashlib
import re
from datetime import datetime, timezone
from collections import Counter, defaultdict
from dataclasses import dataclass, field, asdict
from typing import List, Tuple, Optional, Dict
from itertools import combinations


# Maximum text length stored per crystal. Set to 0 to disable truncation.
#
# The original value was 300, hardcoded inline at the Crystal constructor.
# That silently capped every deposit to a headline. Telemetry texts survived
# intact because they're short, but substantive conversation crystals were
# cut at the first sentence — and then when the corpus was clustered, the
# content signal had been truncated out while the telemetry signal was still
# fully represented. The flat-formations problem was caused by this truncation
# upstream of clustering, not by clustering parameters downstream.
#
# Raised to 32768 so ordinary pages and session turns survive fully while
# still bounding pathological inputs.
MAX_CRYSTAL_TEXT = 32768


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
    # Chaincode marriage. Backward compatible — None for crystals
    # predating the marriage. When present, these let coupling_strength
    # compute a temporal proximity bonus alongside semantic gamma.
    #
    # chain_id          — chaincode hash, traceback to the source chain
    # chain_seq         — autoincrement position in the chain (ordinal
    #                     proximity)
    # chain_created_at  — ISO-8601 timestamp from chaincode.created_at.
    #                     Per the 2026-04-26 morning revision notes:
    #                     ordinal proximity captures "in the same
    #                     conversation/burst" while time proximity
    #                     captures "happened close in real time."
    #                     They give different signals — a long debug
    #                     session has ordinal closeness without time
    #                     closeness; parallel sessions on different
    #                     topics have time closeness without ordinal
    #                     closeness.
    # chain_prev_hash   — parent's chain hash (chains.prev_hash). Phase 5.
    #                     If a.chain_id == b.chain_prev_hash, then a is
    #                     b's direct parent in the chain — a strictly
    #                     stronger signal than ordinal distance 1, which
    #                     can include interleaved writes from unrelated
    #                     sessions. Parent-child is the literal narrative
    #                     link: this exact thought followed that exact
    #                     thought.
    chain_id: Optional[str] = None
    chain_seq: Optional[int] = None
    chain_created_at: Optional[str] = None
    chain_prev_hash: Optional[str] = None

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


def _acquire_lock(lock_path: str, timeout: float = 5.0) -> None:
    """Acquire an exclusive file-based lock.

    Uses ``os.open`` with ``O_CREAT | O_EXCL`` — an atomic
    create-if-not-exists supported on both POSIX and Windows. If the
    lock file already exists (another writer is mid-save), retry with
    a short sleep up to ``timeout`` seconds. On timeout, raise
    ``TimeoutError`` with the lock path so the caller knows which
    lockfile to inspect if they suspect a stale lock from a crashed
    writer.

    The lockfile content is the holding PID + a UTC timestamp — not
    machine-readable, just a diagnostic breadcrumb for a human
    inspecting a stuck lock.
    """
    import os
    import time

    start = time.monotonic()
    while True:
        try:
            fd = os.open(
                lock_path,
                os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                0o644,
            )
            try:
                content = f"{os.getpid()} {datetime.now(timezone.utc).isoformat()}\n"
                os.write(fd, content.encode("utf-8"))
            finally:
                os.close(fd)
            return
        except FileExistsError:
            if time.monotonic() - start >= timeout:
                raise TimeoutError(
                    f"Could not acquire lock {lock_path} within "
                    f"{timeout}s — another writer holds it. "
                    f"If you believe the holder is dead, inspect "
                    f"and delete the lockfile manually."
                )
            time.sleep(0.05)


def _content_hash(text: str) -> str:
    """Return a stable short hash of ``text`` for content-dedup lookups.

    md5 is used for speed, not cryptographic strength — this is a
    dedup key, not a security boundary. Text is encoded utf-8 before
    hashing so the hash is stable across platforms.
    """
    import hashlib
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def _release_lock(lock_path: str) -> None:
    """Release a lock acquired via ``_acquire_lock``.

    Best-effort unlink — a failed release is not fatal (the lock just
    persists and the next writer will see it as stuck), but it IS
    logged at warning level so operators have a breadcrumb when
    antivirus, permissions, or a dead disk is keeping a lockfile alive.
    """
    import logging
    import os
    try:
        os.unlink(lock_path)
    except OSError as exc:
        logging.getLogger(__name__).warning(
            "Could not release lock %s (%s); next writer may see it "
            "as stuck and require manual cleanup.",
            lock_path, exc,
        )


def _atomic_write_json(
    path: str,
    data,
    indent: Optional[int] = None,
    lock: bool = True,
    lock_timeout: float = 5.0,
) -> None:
    """Atomically write ``data`` as JSON to ``path``.

    Writes to a unique temp file in the same directory as the target
    (same filesystem required for atomic replace), flushes + fsyncs
    the file descriptor so the bytes are on disk, then uses
    ``os.replace`` to swap the temp into place. ``os.replace`` is
    guaranteed atomic on POSIX and Windows per the Python docs —
    after it returns, the target is either the full new content or
    the full old content, never a partial blend.

    Prevents the corruption class that plate item 20 added recovery
    for: a single unlucky interrupt during ``json.dump`` could
    truncate the state file mid-write, and every subsequent
    FishEngine boot would crash on the corrupt JSON. Atomic writes
    mean that class of corruption simply cannot happen — the target
    is never in a partial state.

    When ``lock=True`` (the default), also serializes writers via a
    short-lived lockfile at ``path + ".lock"``. Two processes writing
    the same path at the same time can interleave their temp-file
    creation and their ``os.replace`` calls, and while neither write
    is partial, the second write silently overwrites the first —
    losing data if the two sources diverged. The lock forces the
    second writer to wait for the first to finish. Lock acquisition
    times out after ``lock_timeout`` seconds and raises
    ``TimeoutError`` with the lockfile path.

    On any exception during the write, the temp file is best-effort
    cleaned up, the lock is released, and the exception is re-raised
    so the caller knows the save failed.
    """
    import json
    import os
    import tempfile

    dir_path = os.path.dirname(os.path.abspath(path)) or "."
    os.makedirs(dir_path, exist_ok=True)

    lock_path = path + ".lock" if lock else None
    if lock_path:
        _acquire_lock(lock_path, timeout=lock_timeout)

    try:
        fd, tmp_path = tempfile.mkstemp(
            prefix=os.path.basename(path) + ".tmp.",
            dir=dir_path,
            suffix=".json",
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=indent)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, path)
        except Exception:
            # Best-effort cleanup; swallow cleanup errors, re-raise the real one.
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
    finally:
        if lock_path:
            _release_lock(lock_path)


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

        When d=1 (a single author), that author's signature words
        appear in every document. IDF kills them as stop words — but
        those words ARE the author's identity. Warm mode treats
        frequency as signal rather than noise. The algorithm that was
        built for strangers learns to see a known voice.
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
        """Persist vectorizer state for reuse across sessions.

        Uses ``_atomic_write_json`` so a mid-write interrupt or crash
        cannot leave ``mi_vectorizer.json`` in a partially-written
        state. Paired with the graceful-recovery handling in
        ``MIVectorizer.load`` (plate item 20), corruption is now
        prevented on the write side AND recovered from on the read
        side if it ever slips through another path.
        """
        data = {
            'token_counts': dict(self.token_counts.most_common()),
            'pair_counts': {f"{k[0]}|{k[1]}": v for k, v in self.pair_counts.most_common(100000)},
            'doc_count': self.doc_count,
            'token_doc_counts': dict(self.token_doc_counts.most_common()),
        }
        _atomic_write_json(path, data)

    def load(self, path: str):
        """Load persisted vectorizer state.

        Best-effort recovery: a missing file, an unreadable file, a
        malformed JSON payload, or a non-object payload all leave the
        vectorizer in its freshly-constructed empty state. The next
        ``save()`` will rewrite a clean file. Corruption is logged at
        warning level; it is never fatal to FishEngine initialization.
        """
        import json, os, logging
        if not os.path.exists(path):
            return
        try:
            with open(path) as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            logging.getLogger(__name__).warning(
                "MIVectorizer.load: could not parse %s (%s); starting empty",
                path, exc,
            )
            return
        if not isinstance(data, dict):
            logging.getLogger(__name__).warning(
                "MIVectorizer.load: %s did not contain a JSON object; starting empty",
                path,
            )
            return
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


# ---------------------------------------------------------------------------
# CHAINCODE MARRIAGE — coupling_strength with temporal proximity
# ---------------------------------------------------------------------------
# Spec: data/chaincode_fish_marriage_spec.md (2026-03-25, Captain approved).
#
# The v3 fish couples by semantic proximity (gamma). It has no sense of
# time — two crystals from the same conversation couple the same as two
# crystals from three months apart. The chaincode service has 168K+
# entries with provenance and timestamps but no formation logic.
#
# coupling_strength gives the fish temporal coupling. When both crystals
# carry chaincode position, distance in the chain contributes a temporal
# bonus on top of semantic similarity. Narrative arcs become formations,
# not just semantic clusters.
#
# Olorina's staleness filter: temporal proximity ONLY counts if there's
# also semantic signal. Two identical sensor readings at T and T+1
# would otherwise mega-couple by pure chain adjacency. The semantic
# floor gates the temporal bonus.
#
# Backward compatible: crystals without chain_seq fall through to pure
# gamma * SEMANTIC_WEIGHT. Pre-marriage crystals lose nothing.
#
# Phase 1 of the build (this commit) adds the function. _compute_couplings
# stays unchanged. Phase 2 (separate, after sandbox tests pass) integrates
# it into the live coupling pipeline.

TEMPORAL_WEIGHT = 0.3
SEMANTIC_WEIGHT = 0.7
SEMANTIC_FLOOR = 0.2  # Olorina's staleness gate

# Time-decay scale (seconds). Phase 4 — per 2026-04-26 morning revision
# notes. Pairs within TIME_DECAY_SECONDS of each other get ~0.5 time
# proximity; pairs an hour apart get ~0.016. The default 60s (one minute)
# treats "burst" co-occurrence as the strong signal and longer gaps as
# rapidly fading. Tunable; the A/B harness sweeps it.
TIME_DECAY_SECONDS = 60.0


def _parse_chain_ts(ts: Optional[str]) -> Optional[float]:
    """Parse an ISO-8601 chaincode timestamp to a unix-epoch float.

    Returns None on any parse failure — the caller falls back to
    ordinal-only coupling without crashing. The chaincode service
    writes ``datetime.now().isoformat()`` (no timezone in 0.x, with
    timezone in some entries), and Python 3.11+ handles both via
    ``datetime.fromisoformat``. We treat all timestamps as UTC for
    distance arithmetic — close enough for time-decay purposes since
    we only care about relative seconds.
    """
    if not ts:
        return None
    try:
        from datetime import datetime
        dt = datetime.fromisoformat(ts)
        return dt.timestamp()
    except (ValueError, TypeError):
        return None


def coupling_strength(a: 'Crystal', b: 'Crystal') -> float:
    """Blended semantic + temporal coupling between two crystals.

    Returns SEMANTIC_WEIGHT * gamma + TEMPORAL_WEIGHT * temporal_proximity,
    with the temporal term zeroed unless gamma exceeds SEMANTIC_FLOOR
    (the staleness filter — chain adjacency without semantic signal is
    not coupling, it's just sequential noise).

    Temporal proximity is the MAX of three signals when available:

      chain_link        = 1.0 if a is b's direct parent in the chaincode
                          chain (a.chain_id == b.chain_prev_hash) or
                          vice versa; 0.0 otherwise. The literal "this
                          thought followed that thought" relationship.
      ordinal_proximity = 1 / (1 + |chain_seq_a - chain_seq_b|)
      time_proximity    = TIME_DECAY_SECONDS / (TIME_DECAY_SECONDS + |t_a - t_b|)

    Per the 2026-04-26 morning revision notes, the three signals
    capture different shapes of "narrative adjacent":
      - chain_link is the strictest — it's the direct chaincode-link,
        ignores interleaved writes from unrelated sessions, and is
        binary (you either are the parent or you aren't). Phase 5.
      - chain_seq captures "in the same conversation/burst," tolerating
        gaps from interleaved writes
      - chain_created_at captures "happened close in real time"
    A long debug session has ordinal closeness without time closeness;
    parallel sessions on different topics have time closeness without
    ordinal closeness; a direct chaincode parent-child has chain_link.
    Taking the MAX means any signal counts.

    Crystals without chain metadata get g_temporal = 0 and the function
    reduces to SEMANTIC_WEIGHT * gamma. Backward compatible across the
    entire matrix of which fields are present.

    Spec: data/chaincode_fish_marriage_spec.md (2026-03-25) +
    data/chaincode_fish_marriage_spec_REVISION_NOTES_2026-04-26.md.
    """
    g_semantic = gamma(a.mi_vector, b.mi_vector)

    g_temporal = 0.0

    # Phase 5: chain-link proximity — the literal parent-child
    # relationship via chains.prev_hash. Strictly stronger than
    # ordinal distance 1, which can include interleaved writes
    # from unrelated sessions.
    if (a.chain_id and b.chain_prev_hash and a.chain_id == b.chain_prev_hash) or \
       (b.chain_id and a.chain_prev_hash and b.chain_id == a.chain_prev_hash):
        g_temporal = max(g_temporal, 1.0)

    # Ordinal proximity (chain_seq distance)
    if a.chain_seq is not None and b.chain_seq is not None:
        distance = abs(a.chain_seq - b.chain_seq)
        if distance > 0:
            g_temporal = max(g_temporal, 1.0 / (1.0 + distance))

    # Time proximity (chain_created_at distance, in seconds)
    t_a = _parse_chain_ts(a.chain_created_at)
    t_b = _parse_chain_ts(b.chain_created_at)
    if t_a is not None and t_b is not None:
        seconds_distance = abs(t_a - t_b)
        if seconds_distance > 0:
            g_temporal = max(g_temporal,
                             TIME_DECAY_SECONDS / (TIME_DECAY_SECONDS + seconds_distance))

    if g_semantic < SEMANTIC_FLOOR:
        g_temporal = 0.0

    return SEMANTIC_WEIGHT * g_semantic + TEMPORAL_WEIGHT * g_temporal


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
                parser=None,
                chain_id: Optional[str] = None,
                chain_seq: Optional[int] = None,
                chain_created_at: Optional[str] = None,
                chain_prev_hash: Optional[str] = None) -> Crystal:
    """Create a crystal from text using MI × ache vectorization + cognitive parse.

    This is the v3 replacement for v1's keyword-based crystallize().
    The parser (if provided) adds cognitive dimension vector, thought chains,
    and modifier scores. This is the grammar thinking, not just counting.

    chain_id / chain_seq / chain_created_at (chaincode marriage):
        Optional chaincode position. If supplied, the crystal records
        where it lives in the chaincode chain so coupling_strength()
        can compute temporal proximity. All default to None for
        backward compatibility — pre-marriage crystals just have no
        temporal coordinate.

        chain_created_at (ISO-8601) is added per the 2026-04-26 morning
        revision notes. It enables a true time-decay alongside the
        ordinal chain_seq decay — a long-running conversation has
        ordinal closeness without time closeness, and parallel
        sessions on different topics have time closeness without
        ordinal closeness. Both signals matter.
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

    # Preserve full crystal text. The previous 300-char cap silently
    # truncated every substantive deposit to a headline, leaving only
    # short telemetry texts fully represented. See exp/ai-usability doc
    # and 2026-04-13 session diagnosis for the full story.
    return Crystal(
        id=crystal_id,
        ts=ts,
        text=text[:MAX_CRYSTAL_TEXT] if MAX_CRYSTAL_TEXT else text,
        source=source,
        mi_vector=mi_vec,
        resonance=[],  # filled after PCA
        keywords=keywords,
        ache=ache,
        cognitive_vector=cognitive_vector,
        chains=chains,
        modifiers=modifiers,
        chain_id=chain_id,
        chain_seq=chain_seq,
        chain_created_at=chain_created_at,
        chain_prev_hash=chain_prev_hash,
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

    def __init__(self, state_dir: str = None, autoload: bool = True):
        """Initialize a UniversalFish.

        Args:
            state_dir: directory for all persisted state files. If None,
                defaults to ``~/.linafish``.
            autoload: if True (default), call ``_load_state()`` at the
                end of ``__init__`` against the default hardcoded paths
                (``fish_v3_state.json`` / ``mind_crystals_v3.jsonl`` /
                ``mi_vectorizer.json``). Direct UniversalFish users get
                the historical behavior with no change.

                If False, construction does NOT auto-load. The caller is
                responsible for setting name-scoped ``fish_state_path``,
                ``pending_path``, and ``crystal_log_path`` attributes and
                then explicitly calling ``_load_state()``. This is the
                path ``FishEngine`` uses to prevent shared-default state
                file leakage across differently-named fishes living in
                the same ``state_dir``.

                The prior FishEngine code worked around the auto-load by
                rebinding ``self.fish.crystals = []`` after init, then
                calling ``_load_state`` a second time against the
                corrected paths. That workaround only cleared the
                ``crystals`` leak; ``vectorizer``, ``epoch``, ``frozen``,
                and ``vocab`` were still inheriting from whatever the
                shared-default state file happened to contain. With
                ``autoload=False`` none of that data ever gets loaded in
                the first place, closing all four leaks at the root.
        """
        self.vectorizer = MIVectorizer()
        self.vocab: List[str] = []
        self.frozen = False
        self.crystals: List[Crystal] = []
        self.pending: List[dict] = []  # queued for next re-eat
        self.epoch = 0  # how many times the fish has re-eaten
        # Content-dedup (plate item 12). When ``dedupe`` is True,
        # ``crystallize_text`` consults ``_seen_hashes`` before
        # creating a new crystal; a repeat of the same text is a
        # no-op instead of creating a duplicate. Off by default —
        # callers that want dedup set this to True on the instance
        # (FishEngine propagates its own ``dedupe`` kwarg here).
        self.dedupe = False
        self._seen_hashes: set = set()
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

        if autoload:
            self._load_state()

    def _load_state(self):
        """Load persisted state — vectorizer, epoch, and crystals.

        Both state files (``mi_vectorizer.json`` and ``*_v3_state.json``)
        load best-effort: missing, unreadable, malformed, or non-object
        payloads short-circuit to the already-initialized defaults so
        FishEngine construction never crashes on a corrupt state file.
        The next ``_save_state`` rewrites clean files.
        """
        self.vectorizer.load(self.vectorizer_path)
        if os.path.exists(self.fish_state_path):
            import json, logging
            try:
                with open(self.fish_state_path) as f:
                    state = json.load(f)
            except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
                logging.getLogger(__name__).warning(
                    "UniversalFish._load_state: could not parse %s (%s); using defaults",
                    self.fish_state_path, exc,
                )
                state = None
            if isinstance(state, dict):
                self.epoch = state.get('epoch', 0)
                self.frozen = state.get('frozen', False)
                self.vocab = state.get('vocab', [])
            elif state is not None:
                logging.getLogger(__name__).warning(
                    "UniversalFish._load_state: %s did not contain a JSON object; using defaults",
                    self.fish_state_path,
                )

        # Load crystals from JSONL log (authoritative source).
        #
        # Prior to this fix the load path silently amputated six fields
        # (chains, modifiers, cognitive_vector, ache, formation,
        # wrapping_numbers) by omitting them from the Crystal(...)
        # construction and letting the dataclass defaults take over.
        # Every save wrote the full crystal via asdict(); every load
        # stripped the cognitive parse layer back to empty. The JSONL
        # files on disk have had the data the whole time — the loader
        # was just not reading it. Fix: round-trip every persisted
        # field explicitly, and re-tupleify the chains list because
        # JSON drops tuple type on serialize.
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
                            wrapping_numbers=d.get('wrapping_numbers', {}) or {},
                            structural=d.get('structural', False),
                            ache=d.get('ache', 0.0) or 0.0,
                            formation=d.get('formation'),
                            cognitive_vector=d.get('cognitive_vector', []) or [],
                            chains=[tuple(ch) for ch in (d.get('chains', []) or [])],
                            modifiers=d.get('modifiers', {}) or {},
                            chain_id=d.get('chain_id'),
                            chain_seq=d.get('chain_seq'),
                            chain_created_at=d.get('chain_created_at'),
                            chain_prev_hash=d.get('chain_prev_hash'),
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

        # Populate the content-dedup set from whatever crystals are now
        # in memory. Cheap if dedup is off (we just skip the build);
        # O(n) one-time if dedup is on, then O(1) per crystallize check.
        if self.dedupe:
            self._seen_hashes = {
                _content_hash(c.text) for c in self.crystals if c.text
            }

    def _save_state(self):
        """Persist state atomically.

        Both ``mi_vectorizer.json`` (via ``self.vectorizer.save``) and
        ``*_v3_state.json`` (here) now write through
        ``_atomic_write_json`` — a crash or kill mid-save cannot
        leave either file in a half-written state. Plate item 10.
        """
        self.vectorizer.save(self.vectorizer_path)
        os.makedirs(self.state_dir, exist_ok=True)
        _atomic_write_json(
            self.fish_state_path,
            {
                'epoch': self.epoch,
                'frozen': self.frozen,
                'vocab': self.vocab,
                'doc_count': self.vectorizer.doc_count,
                'crystal_count': len(self.crystals),
                'pending_count': len(self.pending),
                'updated': datetime.now(timezone.utc).isoformat(),
            },
            indent=2,
        )

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

    def crystallize_text(self, text: str, source: str = "unknown",
                         chain_id: Optional[str] = None,
                         chain_seq: Optional[int] = None,
                         chain_created_at: Optional[str] = None,
                         chain_prev_hash: Optional[str] = None) -> Optional[Crystal]:
        """Crystallize a single text against frozen statistics.

        If not frozen, queues to pending instead.

        When ``self.dedupe`` is True, incoming text is hashed and
        checked against ``self._seen_hashes`` before any work is done.
        A match is a no-op — ``crystallize_text`` returns None and the
        caller's ``docs_ingested`` counter stays put. The dedup check
        happens after the length gate and before the freeze gate so
        repeats don't pile up in the pending queue either.

        v0.4: Also runs the metabolic engine if available, enriching
        the crystal with 8-pathway residues, metabolic chain, and ache
        distribution. The MI vector stays — co-occurrence is still how
        the fish learns vocabulary. The metabolism adds the cognitive layer.

        chaincode marriage (spec 2026-03-25): chain_id / chain_seq
        carry the chaincode position with the deposit. If queued to
        pending (pre-freeze), the metadata is stored with the pending
        record so it survives the re-eat. If crystallized immediately,
        it's recorded on the Crystal directly.
        """
        if not text or len(text.strip()) < 10:
            return None

        # Dedup: compute the hash once, check the seen set, remember
        # the value for the success-path add below. The add is
        # deliberately deferred until AFTER persistence succeeds —
        # if ``_flush_pending`` or ``crystallize`` raises, the hash
        # must NOT be in the seen set or the caller's retry would
        # be silently dropped as a "duplicate."
        text_hash: Optional[str] = None
        if self.dedupe:
            text_hash = _content_hash(text)
            if text_hash in self._seen_hashes:
                return None  # already seen this exact text

        if not self.frozen:
            # Queue for next epoch
            pending_record = {'text': text, 'source': source}
            if chain_id is not None:
                pending_record['chain_id'] = chain_id
            if chain_seq is not None:
                pending_record['chain_seq'] = chain_seq
            if chain_created_at is not None:
                pending_record['chain_created_at'] = chain_created_at
            if chain_prev_hash is not None:
                pending_record['chain_prev_hash'] = chain_prev_hash
            self.pending.append(pending_record)
            self._flush_pending()
            # Persistence committed — NOW it's safe to record the
            # hash so pre-freeze repeats are caught on subsequent
            # submissions. Without this add the same text could
            # pile up in the pending JSONL across many submissions.
            if text_hash is not None:
                self._seen_hashes.add(text_hash)
            return None

        crystal = crystallize(text, self.vectorizer, source=source,
                             vocab=self.vocab, parser=self.parser,
                             chain_id=chain_id, chain_seq=chain_seq,
                             chain_created_at=chain_created_at,
                             chain_prev_hash=chain_prev_hash)
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
        # Hash is added LAST — only after crystal is on disk. If
        # anything above raises, the seen set stays clean and a
        # retry re-runs the whole pipeline.
        if text_hash is not None:
            self._seen_hashes.add(text_hash)
        return crystal

    def _persist_crystal(self, crystal: Crystal):
        """Write crystal to JSONL log."""
        import json
        # When crystal_log_path is a bare filename (relative, no
        # directory component), os.path.dirname returns "" and
        # os.makedirs("") raises FileNotFoundError on Windows. Guard
        # the makedirs — the file's directory is cwd, which already
        # exists.
        crystal_dir = os.path.dirname(self.crystal_log_path)
        if crystal_dir:
            os.makedirs(crystal_dir, exist_ok=True)
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
            try:
                import numpy as np
                from collections import Counter as _Counter
                vectors = [c.mi_vector for c in crystals if c.mi_vector]
                if vectors:
                    # Filter to most common vector length (vocab may evolve between eats)
                    lengths = _Counter(len(v) for v in vectors)
                    target_len = lengths.most_common(1)[0][0]
                    eligible = [(i, c) for i, c in enumerate(crystals)
                                if c.mi_vector and len(c.mi_vector) == target_len]
                    if eligible:
                        V = np.array([c.mi_vector for _, c in eligible], dtype=np.float32)
                        centroid = V.mean(axis=0)
                        R = V - centroid
                        norms = np.linalg.norm(R, axis=1, keepdims=True)
                        norms[norms == 0] = 1
                        R = R / norms
                        for vi, (_, c) in enumerate(eligible):
                            c.mi_vector = R[vi].tolist()
            except ImportError:
                # Fallback: skip centroid subtraction (optimization for homogeneous
                # corpora, not load-bearing — matches reduce_pca pattern at line 556)
                pass

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
        temporal_rescued = 0
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

                # Phase 2 of chaincode-fish marriage (spec 2026-03-25):
                # temporal rescue. Pairs that don't quite cross the gamma
                # threshold but are chain-adjacent in the chaincode chain
                # AND carry enough semantic signal (staleness gate at
                # SEMANTIC_FLOOR) get a temporal proximity bonus. The
                # blended score from coupling_strength must clear the
                # same min_gamma threshold to actually couple — we don't
                # lower the bar, we just give chain-adjacent narrative
                # arcs a shot at clearing it.
                #
                # Backward compatible: pairs without chain_seq on both
                # sides skip this block entirely. Legacy fish behavior is
                # unchanged when no crystal carries chain metadata.
                if not should_couple and a.chain_seq is not None and b.chain_seq is not None:
                    cs_score = coupling_strength(a, b)
                    if cs_score >= min_gamma:
                        should_couple = True
                        temporal_rescued += 1

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
        if temporal_rescued:
            msg += f" ({temporal_rescued} rescued by temporal proximity)"
        _logging.getLogger(__name__).debug(msg)

    # --- Incremental: queue + re-eat ---

    def ingest(self, text: str, source: str = "unknown",
               chain_id: Optional[str] = None,
               chain_seq: Optional[int] = None,
               chain_created_at: Optional[str] = None,
               chain_prev_hash: Optional[str] = None) -> Optional[Crystal]:
        """The live API. Drop-in for v1 crystallize().

        If frozen: crystallize against current stats.
        Also queues the text for the next re-eat.

        chaincode marriage: chain_id / chain_seq / chain_created_at
        carry the chaincode position with the deposit. Persisted on the
        crystal when frozen; persisted in the pending record otherwise.
        """
        if not text or len(text.strip()) < 10:
            return None

        # Always queue for next epoch's learning
        pending_record = {'text': text, 'source': source}
        if chain_id is not None:
            pending_record['chain_id'] = chain_id
        if chain_seq is not None:
            pending_record['chain_seq'] = chain_seq
        if chain_created_at is not None:
            pending_record['chain_created_at'] = chain_created_at
        if chain_prev_hash is not None:
            pending_record['chain_prev_hash'] = chain_prev_hash
        self.pending.append(pending_record)

        # If frozen, also crystallize now
        crystal = None
        if self.frozen:
            crystal = crystallize(text, self.vectorizer, source=source,
                                 vocab=self.vocab, parser=self.parser,
                                 chain_id=chain_id, chain_seq=chain_seq,
                                 chain_created_at=chain_created_at,
                                 chain_prev_hash=chain_prev_hash)
            crystal.resonance = crystal.mi_vector
            self.crystals.append(crystal)
            self._persist_crystal(crystal)

        # Check if it's time to re-eat
        if self._should_re_eat():
            print(f"Re-eat triggered. Pending: {len(self.pending)} "
                  f"({len(self.pending) / max(self.vectorizer.doc_count, 1) * 100:.0f}% of corpus)",
                  flush=True)
            # Don't re-eat automatically — flag it for the caller to decide.

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


# Note: the sandbox_compare() v1-vs-v3 dev test that lived here was removed
# in fork/step6 (2026-04-15) as part of the v1 sunset. v3-side sanity coverage
# now lives in tests/reeat_cycle_test.py and tests/persona_lab.py.
