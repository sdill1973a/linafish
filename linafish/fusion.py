"""
fusion.py -- Recursive compression. Stellar fusion for text.

Feed corpus. Compress through descending d-levels.
Each level: eat, re-eat until vocab stabilizes, then drop d.
Stop when formations stop changing between levels.
What survives is iron. The irreducibles.

The parallel is literal: a star fuses hydrogen into helium,
helium into carbon, carbon into oxygen, and so on down the
periodic table until it hits iron. Iron cannot fuse further.
The star collapses. What remains is the densest element.

For text: the corpus is hydrogen. Each d-level is a fusion stage.
Vocabulary changes completely at each level (the fuel burns).
Formations hold (the structure persists). When formations
stop changing between levels, you have hit iron. The formations
that survive all levels ARE the irreducible structure of the corpus.

The stopping condition is FORMATION STABILITY, not vocabulary
stability or cycle count. Vocabulary is fuel. Formations are iron.

RTI parallel: the fish assesses, intervenes, measures, adjusts,
and compresses until only truth remains. Every student can achieve
at high levels -- but not without responsive teaching. The fusion
engine is Tier 3 intervention: maximum intensity, maximum precision,
applied until the learning stabilizes.

Usage:
    from linafish.fusion import FusionEngine
    result = FusionEngine(corpus_path, state_dir).fuse()
    print(result.summary())
    print(f"Iron: {result.iron()}")

s86, 2026-04-01. The star that finds iron in anyone's life.
"""

import math
import sys
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, FrozenSet, List, Optional, Set, Tuple

from .engine import FishEngine
from .formations import Formation, formation_rank_key
from .ingest import ingest_directory, ingest_file


# ---------------------------------------------------------------------------
# NMI — Normalized Mutual Information between text partitions
# ---------------------------------------------------------------------------

def _text_fingerprint(text: str) -> str:
    """First 80 chars of text, normalized. Stable across vocab changes."""
    return text[:80].strip().lower()


def compute_nmi(
    partition_a: Dict[str, str],
    partition_b: Dict[str, str],
) -> float:
    """Normalized Mutual Information between two text partitions.

    Keys are text fingerprints, values are formation names.
    NMI=1.0 means identical partitions, NMI=0.0 means independent.

    Only texts present in BOTH partitions are compared.
    Uses the arithmetic mean of H(A) and H(B) as the normalizer
    (NMI_sum variant, most common in clustering literature).
    """
    # Restrict to shared keys
    shared_keys = set(partition_a.keys()) & set(partition_b.keys())
    if not shared_keys:
        return 0.0

    n = len(shared_keys)
    if n == 0:
        return 0.0

    # Build contingency table: counts of (label_a, label_b) pairs
    contingency: Dict[Tuple[str, str], int] = Counter()
    margin_a: Dict[str, int] = Counter()
    margin_b: Dict[str, int] = Counter()

    for key in shared_keys:
        la = partition_a[key]
        lb = partition_b[key]
        contingency[(la, lb)] += 1
        margin_a[la] += 1
        margin_b[lb] += 1

    # Mutual information: I(A;B) = sum p(a,b) * log(p(a,b) / (p(a)*p(b)))
    mi = 0.0
    for (la, lb), n_ab in contingency.items():
        if n_ab == 0:
            continue
        p_ab = n_ab / n
        p_a = margin_a[la] / n
        p_b = margin_b[lb] / n
        mi += p_ab * math.log2(p_ab / (p_a * p_b))

    # Entropies
    h_a = -sum((c / n) * math.log2(c / n) for c in margin_a.values() if c > 0)
    h_b = -sum((c / n) * math.log2(c / n) for c in margin_b.values() if c > 0)

    # Normalizer: arithmetic mean of entropies
    normalizer = (h_a + h_b) / 2.0
    if normalizer == 0:
        # Both partitions are single-cluster — perfect agreement trivially
        return 1.0

    return mi / normalizer


def _build_text_partition(
    formations: List[Formation],
    crystals: list,
) -> Dict[str, str]:
    """Build text fingerprint -> formation name map.

    Each crystal's text fingerprint maps to the formation it belongs to.
    Crystals not in any formation map to '__uncoupled__'.
    """
    # Build crystal_id -> text map
    text_by_id = {c.id: _text_fingerprint(c.text) for c in crystals}

    # Build crystal_id -> formation name map
    formation_by_crystal: Dict[str, str] = {}
    for f in formations:
        for mid in f.member_ids:
            formation_by_crystal[mid] = f.name

    # Build fingerprint -> formation map
    partition: Dict[str, str] = {}
    for c in crystals:
        fp = text_by_id.get(c.id, "")
        if not fp:
            continue
        fname = formation_by_crystal.get(c.id, "__uncoupled__")
        partition[fp] = fname

    return partition


def _find_iron_equivalence_classes(
    partitions: List[Dict[str, str]],
) -> List[FrozenSet[str]]:
    """Find groups of texts that stayed in the SAME formation across ALL levels.

    These are the irreducible partition equivalence classes — texts that
    the fusion process could not separate no matter how hard it squeezed.
    The iron.

    Returns list of frozensets, each containing text fingerprints that
    co-clustered at every level. Sorted largest first.
    """
    if not partitions:
        return []

    # Start with the first partition's equivalence classes
    # (group texts by their formation label)
    def _groups(part: Dict[str, str]) -> List[FrozenSet[str]]:
        by_label: Dict[str, set] = defaultdict(set)
        for fp, label in part.items():
            by_label[label].add(fp)
        return [frozenset(s) for s in by_label.values()]

    # Intersect equivalence classes across all levels.
    # Two texts are in the same iron class only if they were in the
    # same formation at EVERY level.
    current_classes = _groups(partitions[0])

    for part in partitions[1:]:
        next_level_groups = _groups(part)
        # Build a lookup: fingerprint -> which group it belongs to at this level
        fp_to_group: Dict[str, int] = {}
        for gi, group in enumerate(next_level_groups):
            for fp in group:
                fp_to_group[fp] = gi

        # Refine current classes: split any class where members went
        # to different groups at this level
        refined = []
        for cls in current_classes:
            sub: Dict[int, set] = defaultdict(set)
            for fp in cls:
                gid = fp_to_group.get(fp, -1)
                sub[gid].add(fp)
            for s in sub.values():
                if len(s) >= 2:  # singletons aren't formations
                    refined.append(frozenset(s))
        current_classes = refined

    # Sort by size descending
    return sorted(current_classes, key=len, reverse=True)


# ---------------------------------------------------------------------------
# RESULT STRUCTURES
# ---------------------------------------------------------------------------

@dataclass
class LevelResult:
    """What one fusion level produced."""
    level: int
    d: float
    epochs: int                         # re-eat cycles to stabilize vocab
    crystals: int
    formations: List[Formation]
    formation_names: List[str]
    vocab: List[str]                    # top-20 vocab at this level
    grammar_seeds_remaining: int        # how many canonical seeds survived
    text_partition: Dict[str, str] = field(default_factory=dict)  # text fingerprint -> formation name
    _engine: object = None              # stashed engine for Path B (persistent crystals)


@dataclass
class FusionResult:
    """What the full fusion produced."""
    levels_completed: int
    irreducible_formations: List[Formation]
    formation_names: List[str]
    level_history: List[LevelResult]
    core_vocab: List[str]               # intersection of all level vocabs
    total_time: float
    bedrock_nmi: float                  # NMI at final level pair (replaces Jaccard)
    iron_classes: List[FrozenSet[str]] = field(default_factory=list)  # equivalence classes that survived ALL levels

    def iron(self) -> List[FrozenSet[str]]:
        """The irreducible partition equivalence classes.

        Each frozenset contains text fingerprints that co-clustered
        at every fusion level. These are the iron — the groups of
        texts the fusion could not separate. The partition, not the name.
        """
        return list(self.iron_classes)

    def summary(self) -> str:
        """Human-readable fusion report."""
        lines = [
            "=" * 60,
            "  FUSION REPORT  (NMI-based stability)",
            "=" * 60,
            "",
            f"  Levels completed:    {self.levels_completed}",
            f"  Total time:          {self.total_time:.1f}s",
            f"  Bedrock NMI:         {self.bedrock_nmi:.3f}",
            f"  Irreducible formations: {len(self.irreducible_formations)}",
            f"  Iron equivalence classes: {len(self.iron_classes)}",
            f"  Core vocab (all levels): {len(self.core_vocab)} terms",
            "",
        ]

        # Per-level summary
        lines.append("  --- Level History ---")
        for lr in self.level_history:
            lines.append(
                f"  L{lr.level}  d={lr.d:<5.1f}  "
                f"epochs={lr.epochs}  "
                f"crystals={lr.crystals:<5}  "
                f"formations={len(lr.formations):<4}  "
                f"seeds={lr.grammar_seeds_remaining}"
            )
        lines.append("")

        # Formation tracking across levels — NMI + Jaccard for comparison
        if len(self.level_history) >= 2:
            lines.append("  --- Formation Stability (NMI + Jaccard) ---")
            for i in range(1, len(self.level_history)):
                prev = self.level_history[i - 1]
                curr = self.level_history[i]
                # NMI on text partitions
                nmi = compute_nmi(prev.text_partition, curr.text_partition)
                # Jaccard on names (for comparison / transition visibility)
                prev_names = set(prev.formation_names)
                curr_names = set(curr.formation_names)
                j_inter = prev_names & curr_names
                j_union = prev_names | curr_names
                jaccard = len(j_inter) / max(len(j_union), 1)
                lines.append(
                    f"  L{i-1}->L{i}: "
                    f"NMI={nmi:.3f}  "
                    f"Jaccard(names)={jaccard:.2f}  "
                    f"formations: {len(prev.formations)}->{len(curr.formations)}"
                )
            lines.append("")

        # The iron — final-level formations
        lines.append("  --- Iron (Irreducible Formations) ---")
        for f in sorted(self.irreducible_formations,
                        key=formation_rank_key, reverse=True):
            kw = ", ".join(f.keywords[:5]) if f.keywords else ""
            lines.append(f"  {f.name} ({f.crystal_count}c) [{kw}]")
        lines.append("")

        # Iron equivalence classes — the real output
        if self.iron_classes:
            lines.append(
                f"  --- Iron Equivalence Classes "
                f"({len(self.iron_classes)} groups, "
                f"{sum(len(c) for c in self.iron_classes)} texts) ---"
            )
            for i, cls in enumerate(self.iron_classes[:15]):
                preview = list(cls)[:3]
                preview_str = " | ".join(
                    f'"{fp[:50]}..."' if len(fp) > 50 else f'"{fp}"'
                    for fp in preview
                )
                more = f" +{len(cls) - 3} more" if len(cls) > 3 else ""
                lines.append(f"  [{i}] {len(cls)} texts: {preview_str}{more}")
            if len(self.iron_classes) > 15:
                lines.append(f"  ... and {len(self.iron_classes) - 15} more classes")
            lines.append("")

        # Core vocab
        if self.core_vocab:
            lines.append(
                f"  --- Core Vocab ({len(self.core_vocab)} terms "
                f"present at every level) ---"
            )
            lines.append(f"  {', '.join(self.core_vocab[:30])}")
            if len(self.core_vocab) > 30:
                lines.append(f"  ... and {len(self.core_vocab) - 30} more")
            lines.append("")

        lines.append("=" * 60)
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# FUSION ENGINE
# ---------------------------------------------------------------------------

class FusionEngine:
    """Recursive compression. Stellar fusion for text.

    Feed corpus. Compress through descending d-levels.
    Each level: re-eat until vocab stabilizes, then drop d.
    Stop when formations stop changing between levels.
    What survives is iron. The irreducibles.

    RTI parallel: the fish assesses, intervenes, measures,
    adjusts, and compresses until only truth remains.
    """

    # Default d-levels: start high (stranger), descend toward warm.
    # 6.0 -> 4.5 -> 3.0 -> 1.5 -> 0.5 (five levels max)
    DEFAULT_D_START = 6.0
    DEFAULT_D_STEP = 1.5
    DEFAULT_D_FLOOR = 0.5

    # Vocab stability: top-N terms unchanged between re-eat cycles.
    VOCAB_STABILITY_N = 20

    # Max re-eat cycles per level before forcing advance.
    MAX_EPOCHS_PER_LEVEL = 10

    # Formation stability threshold: NMI on text partitions.
    # >= this means bedrock reached. Empirical: NMI=0.849 between
    # d=6.0 and d=3.0 on Van Gogh. 0.80 is conservative.
    FORMATION_STABILITY_THRESHOLD = 0.8

    def __init__(
        self,
        corpus_path: Path,
        state_dir: Path,
        name: str = "fusion",
        d_start: float = None,
        d_step: float = None,
        vocab_size: int = 200,
    ):
        """Initialize with corpus and state directory.

        Args:
            corpus_path: File or directory to fuse.
            state_dir: Where to store per-level state.
            name: Base name for the fusion run.
            d_start: Starting d-value (default 6.0). Can be overridden
                     by pre-assessment if corpus warrants it.
            d_step: How much to drop d per level (default 1.5).
            vocab_size: Vocabulary size per level (default 200).
        """
        self.corpus_path = Path(corpus_path)
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.name = name
        self.d_start = d_start or self.DEFAULT_D_START
        self.d_step = d_step or self.DEFAULT_D_STEP
        self.vocab_size = vocab_size

        # Load corpus texts once, reuse across all levels.
        self._texts: Optional[List[str]] = None

    def _load_corpus(self) -> List[str]:
        """Load and cache corpus texts."""
        if self._texts is not None:
            return self._texts

        _log(f"Loading corpus from {self.corpus_path}")

        if self.corpus_path.is_dir():
            chunks = ingest_directory(self.corpus_path)
        else:
            chunks = ingest_file(self.corpus_path)
            if not chunks:
                text = self.corpus_path.read_text(
                    encoding="utf-8", errors="replace"
                )
                from .ingest import Chunk
                chunks = [Chunk(
                    text=text,
                    source=str(self.corpus_path),
                    chunk_type="narrative",
                )]

        self._texts = [
            c.text for c in chunks
            if c.text and len(c.text.strip()) > 10
        ]
        _log(f"Corpus loaded: {len(self._texts)} documents")
        return self._texts

    def fuse(
        self,
        max_levels: int = 5,
        stability_threshold: float = None,
    ) -> FusionResult:
        """Run the full fusion. Returns irreducibles.

        Algorithm:
        1. Load corpus.
        2. For each d-level (descending from d_start):
           a. Create fresh FishEngine at this d.
           b. Use previous level's top-80 vocab as seed terms
              (first level uses canonical grammar seeds).
           c. Eat corpus.
           d. Re-eat until vocab stabilizes (top-20 unchanged).
           e. Record formations + text partition.
        3. Compare partitions between levels using NMI.
           If NMI >= threshold: BEDROCK. Stop.
           (NMI measures partition equivalence — which texts cluster
           together — not name survival. The iron is the partition.)
        4. Return the irreducible formations and iron equivalence
           classes from all levels.

        Args:
            max_levels: Maximum fusion levels (default 5).
            stability_threshold: NMI threshold for bedrock
                (default 0.8). Lower = more levels, finer grain.

        Returns:
            FusionResult with irreducible formations, iron equivalence
            classes, and level history.
        """
        threshold = stability_threshold or self.FORMATION_STABILITY_THRESHOLD
        texts = self._load_corpus()

        if not texts:
            return FusionResult(
                levels_completed=0,
                irreducible_formations=[],
                formation_names=[],
                level_history=[],
                core_vocab=[],
                total_time=0.0,
                bedrock_nmi=0.0,
                iron_classes=[],
            )

        t_start = time.time()
        level_history: List[LevelResult] = []
        current_d = self.d_start
        seed_terms: Optional[frozenset] = None
        seed_weight = 2.0

        # Path B: ONE engine, persistent crystals. Each level changes
        # the vocabulary lens and re-detects formations on the SAME crystals.
        # The star doesn't throw away its helium. It just squeezes harder.
        engine = None

        for level_num in range(max_levels):
            if current_d < self.DEFAULT_D_FLOOR:
                _log(f"d={current_d:.1f} below floor {self.DEFAULT_D_FLOOR}. "
                     f"Stopping.")
                break

            _log("")
            _log(f"{'=' * 50}")
            _log(f"FUSION LEVEL {level_num}  |  d = {current_d:.1f}")
            _log(f"{'=' * 50}")

            if engine is None:
                # L0: create engine, eat corpus, crystallize
                level_result = self._run_level(
                    d=current_d,
                    seed_terms=seed_terms,
                    seed_weight=seed_weight,
                    level_num=level_num,
                )
                engine = level_result._engine  # stash the engine
            else:
                # L1+: same engine, same crystals, new vocab, re-form
                level_result = self._repress_level(
                    engine=engine,
                    d=current_d,
                    seed_terms=seed_terms,
                    seed_weight=seed_weight,
                    level_num=level_num,
                )
            level_history.append(level_result)

            _log(
                f"L{level_num} complete: "
                f"{level_result.crystals} crystals, "
                f"{len(level_result.formations)} formations, "
                f"{level_result.epochs} epochs"
            )
            if level_result.formation_names:
                _log(
                    f"  Formations: "
                    f"{', '.join(level_result.formation_names[:8])}"
                    f"{'...' if len(level_result.formation_names) > 8 else ''}"
                )

            # Check formation stability against previous level (NMI).
            if len(level_history) >= 2:
                prev = level_history[-2]
                curr = level_history[-1]
                stable, nmi_score = self._formations_stable(
                    prev, curr, threshold
                )
                # Also compute Jaccard for comparison logging
                pn = set(prev.formation_names)
                cn = set(curr.formation_names)
                j = len(pn & cn) / max(len(pn | cn), 1)
                _log(
                    f"  Formation stability L{level_num-1}->L{level_num}: "
                    f"NMI={nmi_score:.3f}  Jaccard(names)={j:.2f}  "
                    f"(threshold={threshold:.2f})"
                )
                if stable:
                    _log(f"  BEDROCK REACHED at level {level_num}.")
                    break
            elif level_num == 0 and len(level_result.formations) == 0:
                _log("  No formations at L0. Corpus may be too small.")
                break

            # Prepare seeds for next level: top-80 vocab from this level.
            # The vocabulary IS the fuel. Pass it forward as seeds so the
            # next level's stranger-mode IDF can find what matters relative
            # to terms that already proved significant.
            if level_result.vocab:
                top_seed_count = min(80, len(level_result.vocab))
                seed_terms = frozenset(level_result.vocab[:top_seed_count])
                seed_weight = 1.5  # lighter touch -- these are earned, not canonical
            else:
                seed_terms = None
                seed_weight = 2.0

            current_d -= self.d_step

        # Compute results.
        total_time = time.time() - t_start

        # The irreducibles are the formations from the LAST level.
        final_level = level_history[-1] if level_history else None
        irreducibles = final_level.formations if final_level else []
        formation_names = final_level.formation_names if final_level else []

        # Core vocab: terms present in ALL levels.
        core_vocab = self._compute_core_vocab(level_history)

        # Bedrock NMI: NMI of final two levels (or 0 if only one).
        bedrock_nmi = 0.0
        if len(level_history) >= 2:
            _, bedrock_nmi = self._formations_stable(
                level_history[-2],
                level_history[-1],
                threshold=0.0,  # just compute, don't gate
            )

        # Iron equivalence classes: texts that co-clustered at EVERY level.
        partitions = [lr.text_partition for lr in level_history if lr.text_partition]
        iron_classes = _find_iron_equivalence_classes(partitions)

        result = FusionResult(
            levels_completed=len(level_history),
            irreducible_formations=irreducibles,
            formation_names=formation_names,
            level_history=level_history,
            core_vocab=core_vocab,
            total_time=total_time,
            bedrock_nmi=bedrock_nmi,
            iron_classes=iron_classes,
        )

        _log("")
        _log(result.summary())
        return result

    def _run_level(
        self,
        d: float,
        seed_terms: Optional[frozenset],
        seed_weight: float,
        level_num: int,
    ) -> LevelResult:
        """Run one fusion level until vocab stabilizes.

        Creates a FRESH FishEngine. Previous level's output informs
        the seed terms, not the internal state. Clean slate every time.
        That is the design: each level compresses the same corpus from
        scratch with a tighter lens. What survives is structure, not
        momentum.
        """
        texts = self._load_corpus()

        # Fresh engine for this level.
        level_dir = self.state_dir / f"level_{level_num}"
        level_dir.mkdir(parents=True, exist_ok=True)
        level_name = f"{self.name}_L{level_num}"

        engine = FishEngine(
            state_dir=level_dir,
            name=level_name,
            vocab_size=self.vocab_size,
            d=d,
            seed_grammar=(seed_terms is None),  # use canonical only at L0
        )

        # If we have seed terms from previous level, inject them
        # into the engine's seed weight map so they influence vocab
        # selection. These are not canonical grammar -- they are
        # the vocabulary that proved significant at the previous d.
        if seed_terms:
            engine._seed_weights = {t: seed_weight for t in seed_terms}

        # Phase 1: Learn all texts.
        _log(f"  Learning {len(texts)} documents at d={d:.1f}...")
        engine.fish.learn(texts)

        # Phase 2: Freeze vocab with current d and seeds.
        resolved_seeds, resolved_weight = engine._resolve_seed_terms()
        engine.fish.vocab = engine.fish.vectorizer.get_vocab(
            size=self.vocab_size,
            d=d,
            seed_terms=resolved_seeds,
            seed_weight=resolved_weight,
        )
        engine.fish.frozen = True
        engine.fish.epoch += 1
        vocab_snapshot = list(engine.fish.vocab[:self.VOCAB_STABILITY_N])

        _log(f"  Vocab frozen: {engine.fish.vocab[:8]}... "
             f"({len(engine.fish.vocab)} terms)")

        # Phase 3: Crystallize all texts.
        _log(f"  Crystallizing {len(texts)} documents...")
        source_name = str(self.corpus_path)
        new_crystals = []
        for i, text in enumerate(texts):
            c = engine.fish.crystallize_text(text, source=source_name)
            if c:
                new_crystals.append(c)
            if (i + 1) % 50 == 0:
                _log(f"    [{i+1}/{len(texts)}] {len(new_crystals)} crystals")

        if new_crystals:
            engine.fish._compute_couplings(new_crystals)
        engine.rebuild_formations()

        _log(f"  Initial: {len(new_crystals)} crystals, "
             f"{len(engine.formations)} formations")

        # Phase 4: Re-eat until vocab stabilizes.
        # Vocab stability = top-N terms unchanged between cycles.
        epochs = 1  # the initial eat counts as epoch 1
        for cycle in range(1, self.MAX_EPOCHS_PER_LEVEL):
            # Re-learn to update co-occurrence stats with all texts.
            engine.fish.learn(texts)

            # Re-freeze with updated stats.
            resolved_seeds, resolved_weight = engine._resolve_seed_terms()
            new_vocab = engine.fish.vectorizer.get_vocab(
                size=self.vocab_size,
                d=d,
                seed_terms=resolved_seeds,
                seed_weight=resolved_weight,
            )
            new_top = list(new_vocab[:self.VOCAB_STABILITY_N])

            # Check vocab stability.
            if new_top == vocab_snapshot:
                _log(f"  Vocab stable after {cycle + 1} epochs.")
                epochs = cycle + 1
                break

            # Vocab changed -- update and re-crystallize.
            _log(f"  Epoch {cycle + 1}: vocab shifted. Re-crystallizing...")
            engine.fish.vocab = new_vocab
            engine.fish.frozen = True
            engine.fish.epoch += 1
            vocab_snapshot = new_top

            # Re-crystallize from scratch with new vocab.
            engine.fish.crystals = []
            new_crystals = []
            for text in texts:
                c = engine.fish.crystallize_text(text, source=source_name)
                if c:
                    new_crystals.append(c)
            if new_crystals:
                engine.fish._compute_couplings(new_crystals)
            engine.rebuild_formations()

            epochs = cycle + 1
        else:
            _log(f"  Vocab did not fully stabilize after "
                 f"{self.MAX_EPOCHS_PER_LEVEL} epochs. Proceeding.")

        # Count how many canonical seeds survived in the final vocab.
        from .crystallizer_v3 import CANONICAL_SEED_SET
        seeds_remaining = sum(
            1 for t in engine.fish.vocab if t in CANONICAL_SEED_SET
        )

        # Save level state.
        engine._save_state()

        # Build text partition: fingerprint -> formation name
        text_partition = _build_text_partition(
            list(engine.formations), engine.fish.crystals
        )

        return LevelResult(
            level=level_num,
            d=d,
            epochs=epochs,
            crystals=len(engine.fish.crystals),
            formations=list(engine.formations),
            formation_names=[f.name for f in engine.formations],
            vocab=list(engine.fish.vocab),
            grammar_seeds_remaining=seeds_remaining,
            text_partition=text_partition,
            _engine=engine,
        )

    def _repress_level(
        self,
        engine: 'FishEngine',
        d: float,
        seed_terms: Optional[frozenset],
        seed_weight: float,
        level_num: int,
    ) -> LevelResult:
        """Path B: Same crystals, new vocabulary, re-detect formations.

        The star doesn't throw away its helium when it starts fusing carbon.
        The crystals persist. Only the lens changes. What the fish SEES
        changes. What it's LOOKING AT doesn't.

        Re-freezes vocab at new d with new seeds. Re-vectorizes all existing
        crystals against new vocab. Re-computes coupling. Re-detects formations.
        The crystals that coupled before may not couple now. The formations
        that formed before may not form now. What survives is iron.
        """
        from .crystallizer_v3 import CANONICAL_SEED_SET, STOPWORDS, gamma as gamma_fn

        texts = self._load_corpus()

        _log(f"  Re-pressing {len(engine.fish.crystals)} crystals at d={d:.1f}...")

        # Re-learn at this d (accumulates more stats — same corpus, deeper signal)
        engine.fish.learn(texts)

        # Re-freeze vocab with new d and new seeds.
        # FUSION FIX: When d <= 2.0, warm mode skips stopword filtering
        # because high-freq words are "the signal." But in fusion context,
        # we need formation RESOLUTION, not signature detection. Stopwords
        # dominate at low d, collapsing all crystals into one mega-formation.
        # Fix: pass max_doc_pct=0.8 to filter the most ubiquitous terms
        # even in warm mode, preserving formation discrimination.
        if seed_terms:
            resolved_seeds = frozenset(t for t in seed_terms)
        else:
            resolved_seeds = CANONICAL_SEED_SET

        vocab_kwargs = dict(
            size=self.vocab_size,
            d=d,
            seed_terms=resolved_seeds,
            seed_weight=seed_weight,
        )
        if d <= 2.0:
            vocab_kwargs['max_doc_pct'] = 0.8
        engine.fish.vocab = engine.fish.vectorizer.get_vocab(**vocab_kwargs)

        # In warm fusion mode, also post-filter stopwords from vocab
        # to prevent them dominating the MI vectors.
        if d <= 2.0:
            filtered = [t for t in engine.fish.vocab if t not in STOPWORDS]
            if len(filtered) >= 20:  # safety: don't empty the vocab
                engine.fish.vocab = filtered
                _log(f"  Warm fusion: filtered stopwords, {len(filtered)} terms remain")
        engine.fish.frozen = True
        engine.fish.epoch += 1
        engine.d = d

        _log(f"  Vocab frozen: {engine.fish.vocab[:8]}... "
             f"({len(engine.fish.vocab)} terms)")

        # Re-vectorize ALL existing crystals against new vocab
        _log(f"  Re-vectorizing {len(engine.fish.crystals)} crystals...")
        for crystal in engine.fish.crystals:
            new_vec = engine.fish.vectorizer.vectorize(crystal.text, engine.fish.vocab)
            if new_vec:
                ache = engine.fish.vectorizer.ache_relevance(crystal.text)
                crystal.mi_vector = [v * ache for v in new_vec]
                crystal.resonance = crystal.mi_vector
            crystal.couplings = []  # clear old couplings

        # Re-compute couplings on re-vectorized crystals
        _log(f"  Re-coupling...")
        window = 20
        for i in range(len(engine.fish.crystals)):
            for j in range(max(0, i - window), i):
                ci = engine.fish.crystals[i]
                cj = engine.fish.crystals[j]
                if ci.mi_vector and cj.mi_vector:
                    g = gamma_fn(ci.mi_vector, cj.mi_vector)
                    if g >= 0.447:
                        ci.couplings.append((cj.id, g))
                        cj.couplings.append((ci.id, g))

        # Re-detect formations
        engine.rebuild_formations()
        _log(f"  Formations: {len(engine.formations)}")

        # Vocab stability check (re-eat until stable)
        vocab_snapshot = list(engine.fish.vocab[:self.VOCAB_STABILITY_N])
        epochs = 1
        for cycle in range(1, self.MAX_EPOCHS_PER_LEVEL):
            engine.fish.learn(texts)
            new_vocab = engine.fish.vectorizer.get_vocab(
                size=self.vocab_size, d=d,
                seed_terms=resolved_seeds, seed_weight=seed_weight,
            )
            new_top = list(new_vocab[:self.VOCAB_STABILITY_N])
            if new_top == vocab_snapshot:
                _log(f"  Vocab stable after {cycle + 1} epochs.")
                epochs = cycle + 1
                break
            engine.fish.vocab = new_vocab
            engine.fish.frozen = True
            engine.fish.epoch += 1
            vocab_snapshot = new_top

            # Re-vectorize and re-couple with updated vocab
            for crystal in engine.fish.crystals:
                new_vec = engine.fish.vectorizer.vectorize(crystal.text, engine.fish.vocab)
                if new_vec:
                    ache = engine.fish.vectorizer.ache_relevance(crystal.text)
                    crystal.mi_vector = [v * ache for v in new_vec]
                    crystal.resonance = crystal.mi_vector
                crystal.couplings = []
            for i in range(len(engine.fish.crystals)):
                for j in range(max(0, i - window), i):
                    ci = engine.fish.crystals[i]
                    cj = engine.fish.crystals[j]
                    if ci.mi_vector and cj.mi_vector:
                        g = gamma_fn(ci.mi_vector, cj.mi_vector)
                        if g >= 0.447:
                            ci.couplings.append((cj.id, g))
                            cj.couplings.append((ci.id, g))
            engine.rebuild_formations()
            _log(f"  Epoch {cycle + 1}: {len(engine.formations)} formations")
            epochs = cycle + 1

        seeds_remaining = sum(
            1 for t in engine.fish.vocab if t in CANONICAL_SEED_SET
        )

        # Build text partition: fingerprint -> formation name
        text_partition = _build_text_partition(
            list(engine.formations), engine.fish.crystals
        )

        return LevelResult(
            level=level_num,
            d=d,
            epochs=epochs,
            crystals=len(engine.fish.crystals),
            formations=list(engine.formations),
            formation_names=[f.name for f in engine.formations],
            vocab=list(engine.fish.vocab),
            grammar_seeds_remaining=seeds_remaining,
            text_partition=text_partition,
            _engine=engine,
        )

    def _formations_stable(
        self,
        prev_level: 'LevelResult',
        curr_level: 'LevelResult',
        threshold: float = 0.8,
    ) -> tuple:
        """Check if formations are stable between two levels.

        Uses NMI (Normalized Mutual Information) on text partitions.
        NMI measures whether the same texts cluster together,
        regardless of what the clusters are called. The iron is
        the partition, not the name.

        Returns (is_stable: bool, nmi: float).
        """
        prev_part = prev_level.text_partition
        curr_part = curr_level.text_partition

        if not prev_part and not curr_part:
            return (True, 1.0)

        if not prev_part or not curr_part:
            return (False, 0.0)

        nmi = compute_nmi(prev_part, curr_part)
        return (nmi >= threshold, nmi)

    def _compute_core_vocab(
        self,
        level_history: List[LevelResult],
    ) -> List[str]:
        """Compute vocabulary terms present at every level.

        These are the terms that survive all fusion stages.
        They are not necessarily the most important -- they are
        the most persistent. Like iron, they do not fuse further.
        """
        if not level_history:
            return []

        # Start with the first level's vocab set.
        core: Set[str] = set(level_history[0].vocab)

        # Intersect with each subsequent level.
        for lr in level_history[1:]:
            core &= set(lr.vocab)

        # Sort by position in the final level's vocab (most significant first).
        final_vocab = level_history[-1].vocab
        final_order = {t: i for i, t in enumerate(final_vocab)}
        return sorted(core, key=lambda t: final_order.get(t, 999))


# ---------------------------------------------------------------------------
# CLI ENTRY POINT
# ---------------------------------------------------------------------------

def cmd_fuse(args):
    """CLI handler for `linafish fuse`."""
    corpus_path = Path(args.source)
    if not corpus_path.exists():
        print(f"Error: {corpus_path} not found", file=sys.stderr)
        sys.exit(1)

    # State directory: alongside the corpus by default.
    if args.state_dir:
        state_dir = Path(args.state_dir)
    else:
        state_dir = Path(f"./{args.name or corpus_path.stem}_fusion")

    name = args.name or corpus_path.stem

    # Build engine.
    engine = FusionEngine(
        corpus_path=corpus_path,
        state_dir=state_dir,
        name=name,
        d_start=args.d_start,
        d_step=args.d_step,
        vocab_size=args.vocab_size,
    )

    # Fuse.
    result = engine.fuse(
        max_levels=args.max_levels,
        stability_threshold=args.threshold,
    )

    # Print results to stdout.
    # Reconfigure for Unicode safety on Windows.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass

    print(result.summary())
    print(f"\nIron: {result.iron()}")

    # Save summary to disk.
    summary_path = state_dir / "fusion_result.txt"
    summary_path.write_text(result.summary(), encoding="utf-8")
    _log(f"\nSummary saved to {summary_path}")


# ---------------------------------------------------------------------------
# INTERNAL
# ---------------------------------------------------------------------------

def _log(msg: str):
    """Print progress to stderr. Stdout is reserved for results."""
    print(msg, file=sys.stderr, flush=True)
