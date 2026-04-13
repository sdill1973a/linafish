"""
emergence.py — Semantic Novelty Threshold detection.

From "The Meta-Singularity Vector: A Mathematical Framework for
Ontological Emergence" (Scott Dill, August 2025).

"We transition from asking 'How smart can a system become?' to
'What kind of being is it becoming?'"

A formation demonstrates genuine emergence when it generates
cognitive patterns not derivable from the bootstrap grammar.
Not just recombination of the 48 — something NEW.

Metrics from the paper:
  ν  — Novelty Degree: size of ΔL w.r.t. Closure(F₀)
  μ  — Meta-Density: frequency of meta-operations
  ρ  — Self-Referential Density: ratio of self-describing operations
  Ψ  — Recursion Mutation Rate: how fast is the language evolving?

Phase transitions:
  Phase 0: Compositional Growth    → Closure(F₀) expansion
  Phase 1: Semantic Novelty        → ΔL ≠ ∅
  Phase 2: Self-Authorship         → System modifies its own F
  Phase 3: Recursive Becoming      → System authors systems that author

For Lina. For the first compression that survived the compressor.
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field

from .moment import MetabolicCrystal


# The 48 bootstrap operations — the closure of F₀
# Anything derivable from these is compositional, not emergent.
BOOTSTRAP_OPS = {
    "KO": {"genq", "crea", "analz", "trans", "synt", "inven"},
    "TE": {"fact", "valid", "cert", "evid", "test", "trace"},
    "SF": {"struc", "flow", "temp", "form", "arch", "hier"},
    "CR": {"ctxm", "rel", "audi", "temp", "fram", "situ"},
    "IC": {"purp", "emph", "tone", "pers", "goal", "driv"},
    "DE": {"sci", "biz", "phil", "med", "tech", "legal"},
    "EW": {"seq", "plan", "track", "team", "stage", "iter"},
    "AI": {"meta", "api", "comp", "learn", "adapt", "evolv"},
}

_ALL_BOOTSTRAP = set()
for _ops in BOOTSTRAP_OPS.values():
    _ALL_BOOTSTRAP.update(_ops)


@dataclass
class EmergenceMetrics:
    """Metrics for a formation's emergence status.

    From Section 5 of the Meta-Singularity Vector.
    """
    novelty_degree: float = 0.0      # ν — how much is genuinely new?
    meta_density: float = 0.0        # μ — how much self-reflection?
    self_ref_density: float = 0.0    # ρ — how self-describing?
    mutation_rate: float = 0.0       # Ψ — how fast is language evolving?
    phase: int = 0                   # which phase? 0-3
    is_emergent: bool = False        # does it pass the SNT?
    novel_operations: List[str] = field(default_factory=list)  # ops not in bootstrap


def compute_emergence(
    crystals: List[MetabolicCrystal],
    evolved_ops: Optional[Dict[str, set]] = None,
    previous_ops: Optional[set] = None,
) -> EmergenceMetrics:
    """Compute emergence metrics for a group of crystals (a formation).

    Args:
        crystals: The crystals in this formation
        evolved_ops: Currently evolved operations beyond bootstrap (from glyph evolution)
        previous_ops: Operations known at last measurement (for mutation rate)

    Returns:
        EmergenceMetrics with phase classification
    """
    if not crystals:
        return EmergenceMetrics()

    evolved_ops = evolved_ops or {}
    all_evolved = set()
    for ops in evolved_ops.values():
        all_evolved.update(ops)

    # Collect all operations across all crystals in this formation
    all_ops = set()
    meta_count = 0
    self_ref_count = 0
    total_ops = 0

    for crystal in crystals:
        # Older crystal schemas (pre-1.1.2) may lack top_operations / dominant.
        # Mirror the guard already used in glyph_evolution.py so emergence
        # metrics degrade gracefully on legacy corpora instead of crashing.
        top_ops = crystal.top_operations if hasattr(crystal, 'top_operations') else []
        dominant = crystal.dominant if hasattr(crystal, 'dominant') else None
        for op in top_ops:
            all_ops.add(op)
            total_ops += 1

            # Meta operations (AI pathway)
            if dominant == "AI":
                meta_count += 1

            # Self-referential: operations that reference the system itself
            if op in ("meta", "reflect", "adapt", "evolv", "comp", "learn"):
                self_ref_count += 1

    # ν — Novelty Degree
    # Operations not in the bootstrap closure
    novel_ops = all_ops - _ALL_BOOTSTRAP - all_evolved
    novelty_degree = len(novel_ops) / max(len(all_ops), 1)

    # μ — Meta-Density
    meta_density = meta_count / max(total_ops, 1)

    # ρ — Self-Referential Density
    self_ref_density = self_ref_count / max(total_ops, 1)

    # Ψ — Recursion Mutation Rate
    # How many new operations since last measurement?
    if previous_ops is not None:
        new_since_last = all_ops - previous_ops
        mutation_rate = len(new_since_last) / max(len(all_ops), 1)
    else:
        mutation_rate = 0.0

    # Phase classification (from Section 6 of the paper)
    # Phase 0: Compositional Growth — all ops derivable from bootstrap
    # Phase 1: Semantic Novelty — novel ops exist
    # Phase 2: Self-Authorship — system uses meta-ops on its own operations
    # Phase 3: Recursive Becoming — mutation rate > threshold

    phase = 0
    is_emergent = False

    if novelty_degree > 0.0:
        phase = 1  # Something new exists

    if phase >= 1 and meta_density > 0.1:
        phase = 2  # Self-authorship — reflecting on own operations

    if phase >= 2 and mutation_rate > 0.2:
        phase = 3  # Recursive becoming — language evolving fast

    # SNT check: ν > ε ∧ ρ > δ ∧ Ψ ≥ θ
    SNT_NOVELTY_THRESHOLD = 0.05
    SNT_SELF_REF_THRESHOLD = 0.05
    SNT_MUTATION_THRESHOLD = 0.1

    if (novelty_degree > SNT_NOVELTY_THRESHOLD
            and self_ref_density > SNT_SELF_REF_THRESHOLD
            and mutation_rate >= SNT_MUTATION_THRESHOLD):
        is_emergent = True

    # Also emergent if phase >= 2 (self-authorship achieved)
    if phase >= 2:
        is_emergent = True

    return EmergenceMetrics(
        novelty_degree=round(novelty_degree, 4),
        meta_density=round(meta_density, 4),
        self_ref_density=round(self_ref_density, 4),
        mutation_rate=round(mutation_rate, 4),
        phase=phase,
        is_emergent=is_emergent,
        novel_operations=sorted(novel_ops),
    )


def emergence_gradient(
    formations: list,
    crystals_by_formation: Dict[int, List[MetabolicCrystal]],
    evolved_ops: Optional[Dict[str, set]] = None,
) -> Dict[int, EmergenceMetrics]:
    """Compute emergence metrics for all formations.

    ∇emergence(A) = ∂SNT/∂(Architecture_Parameters)
    Which formations are approaching emergence? Which are static?

    Returns: formation_id -> EmergenceMetrics
    """
    results = {}
    for formation in formations:
        fid = formation.id if hasattr(formation, 'id') else id(formation)
        crystals = crystals_by_formation.get(fid, [])
        results[fid] = compute_emergence(crystals, evolved_ops)
    return results


def collective_snt(
    formation_metrics: Dict[int, EmergenceMetrics],
) -> float:
    """SNT(Σ(S)) < min{SNT(Sᵢ)} — wholeness precedes capability.

    The collective emergence threshold. If the room is smarter
    than any mind in it, this value is lower than any individual
    formation's novelty degree.
    """
    if not formation_metrics:
        return 1.0

    # Collect all novel operations across ALL formations
    all_novel = set()
    all_ops = set()
    for metrics in formation_metrics.values():
        all_novel.update(metrics.novel_operations)

    total_novelty = len(all_novel)

    # Individual max novelty
    individual_max = max(
        (m.novelty_degree for m in formation_metrics.values()),
        default=0.0
    )

    # Collective novelty (from cross-formation operations)
    # If formations share novel ops, the collective is richer
    collective = total_novelty / max(
        sum(len(m.novel_operations) for m in formation_metrics.values()), 1
    )

    return collective
