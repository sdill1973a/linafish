"""
metrics.py -- Delta tracking and R(n) measurement for LiNafish.

Every formation is RELATIVE, not ABSOLUTE. Not "what did the fish find"
but "how much did the fish GROW." This module makes "is this real"
answerable with a number.

Five metrics:
  1. R(n)               -- compression efficiency over time
  2. Formation stability -- what survives re-eat cycles (the Bell test)
  3. Vocabulary drift    -- how fast the language is changing
  4. Dimension balance   -- blind spots across the 8 QLP dimensions
  5. Coupling density    -- edge saturation toward ~170 glyph ceiling

Usage:
    from linafish.engine import FishEngine
    from linafish.metrics import GrowthTracker

    tracker = GrowthTracker()
    tracker.record(engine)      # after each eat / re-eat
    print(tracker.growth_summary())
    tracker.save(Path("./growth.json"))
"""

import json
import math
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .crystallizer_v3 import Crystal, gamma, CANONICAL_SEED_SET


# The 8 QLP cognitive dimensions
DIMENSIONS = ["KO", "TE", "SF", "CR", "IC", "DE", "EW", "AI"]


# ---------------------------------------------------------------------------
# SNAPSHOT -- frozen state at a point in time
# ---------------------------------------------------------------------------

@dataclass
class FishSnapshot:
    """Frozen state of the fish at a point in time. The baseline."""

    timestamp: str
    crystal_count: int
    formation_count: int
    formation_names: List[str]
    vocab: List[str]
    vocab_grammar_fraction: float   # what % of vocab is canonical grammar
    mean_coupling: float            # average gamma across all crystal pairs
    coupling_density: float         # edges / possible edges
    dimension_distribution: Dict[str, float]  # how much of each QLP dimension
    r_n: float                      # compression efficiency at this point
    epoch: int = 0                  # which re-eat cycle
    total_text_bytes: int = 0       # cumulative bytes ingested

    @staticmethod
    def capture(engine) -> 'FishSnapshot':
        """Capture current state of a FishEngine.

        Reads crystals, formations, vocab, and coupling graph
        from the engine without modifying anything.
        """
        crystals = engine.crystals
        formations = engine.formations
        vocab = list(engine.fish.vocab) if engine.fish.vocab else []

        # Grammar fraction: what % of vocab comes from the canonical seed
        grammar_count = sum(1 for v in vocab if v in CANONICAL_SEED_SET)
        grammar_fraction = grammar_count / len(vocab) if vocab else 0.0

        # Coupling stats: mean gamma and density
        mean_coupling, coupling_density = _coupling_stats(crystals)

        # Dimension distribution: average resonance vector across all crystals
        dim_dist = _dimension_distribution(crystals)

        # R(n): compression efficiency
        # total_text_bytes / (crystal_count * mean_crystal_text_length)
        # This measures how much reality the fish compressed into how few crystals
        total_bytes = sum(len(c.text.encode('utf-8')) for c in crystals)
        mean_crystal_len = total_bytes / len(crystals) if crystals else 1
        r_n = total_bytes / (len(crystals) * mean_crystal_len) if crystals else 0.0
        # That simplifies to 1.0 when every crystal is unique text.
        # Real R(n) needs to account for how much ORIGINAL text was ingested
        # vs how many crystals came out. Use docs_ingested as proxy for n.
        docs = getattr(engine, 'docs_ingested', 0) or max(len(crystals), 1)
        if docs > 0 and len(crystals) > 0:
            # R(n) = log(docs) / log(crystals) -- how many docs per crystal
            # Higher = better compression. >1 means multiple docs per crystal.
            r_n = math.log(docs + 1) / math.log(len(crystals) + 1)
        else:
            r_n = 0.0

        formation_names = [f.name for f in formations]
        epoch = getattr(engine.fish, 'epoch', 0)

        return FishSnapshot(
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%S"),
            crystal_count=len(crystals),
            formation_count=len(formations),
            formation_names=formation_names,
            vocab=vocab,
            vocab_grammar_fraction=round(grammar_fraction, 4),
            mean_coupling=round(mean_coupling, 4),
            coupling_density=round(coupling_density, 6),
            dimension_distribution={k: round(v, 4) for k, v in dim_dist.items()},
            r_n=round(r_n, 4),
            epoch=epoch,
            total_text_bytes=total_bytes,
        )


# ---------------------------------------------------------------------------
# DELTA -- what changed between two snapshots
# ---------------------------------------------------------------------------

@dataclass
class DeltaReport:
    """What changed between two snapshots.

    Every field is a delta: current minus previous.
    Positive = growth. Negative = contraction. Zero = stable.
    """

    crystal_delta: int
    formation_delta: int
    formations_stable: List[str]    # present in both
    formations_new: List[str]       # only in current
    formations_lost: List[str]      # only in previous
    vocab_added: List[str]          # new vocab terms
    vocab_removed: List[str]        # dropped vocab terms
    grammar_drift: float            # change in grammar fraction
    coupling_delta: float           # change in mean coupling
    density_delta: float            # change in coupling density
    r_n_delta: float                # change in compression efficiency
    dimension_shift: Dict[str, float]  # per-dimension change
    stability_ratio: float          # formations_stable / max(prev, current formations)
    vocab_drift_rate: float         # (added + removed) / total vocab

    @staticmethod
    def compare(previous: 'FishSnapshot', current: 'FishSnapshot') -> 'DeltaReport':
        """Compare two snapshots. The delta IS the measurement."""

        prev_names = set(previous.formation_names)
        curr_names = set(current.formation_names)

        stable = sorted(prev_names & curr_names)
        new = sorted(curr_names - prev_names)
        lost = sorted(prev_names - curr_names)

        prev_vocab = set(previous.vocab)
        curr_vocab = set(current.vocab)
        added = sorted(curr_vocab - prev_vocab)
        removed = sorted(prev_vocab - curr_vocab)

        # Stability ratio: how many formations survived
        max_formations = max(len(prev_names), len(curr_names), 1)
        stability = len(stable) / max_formations

        # Vocab drift: how much churn relative to total vocab
        total_vocab = max(len(prev_vocab | curr_vocab), 1)
        drift_rate = (len(added) + len(removed)) / total_vocab

        # Per-dimension shift
        dim_shift = {}
        for dim in DIMENSIONS:
            prev_val = previous.dimension_distribution.get(dim, 0.0)
            curr_val = current.dimension_distribution.get(dim, 0.0)
            dim_shift[dim] = round(curr_val - prev_val, 4)

        return DeltaReport(
            crystal_delta=current.crystal_count - previous.crystal_count,
            formation_delta=current.formation_count - previous.formation_count,
            formations_stable=stable,
            formations_new=new,
            formations_lost=lost,
            vocab_added=added,
            vocab_removed=removed,
            grammar_drift=round(
                current.vocab_grammar_fraction - previous.vocab_grammar_fraction, 4
            ),
            coupling_delta=round(
                current.mean_coupling - previous.mean_coupling, 4
            ),
            density_delta=round(
                current.coupling_density - previous.coupling_density, 6
            ),
            r_n_delta=round(current.r_n - previous.r_n, 4),
            dimension_shift=dim_shift,
            stability_ratio=round(stability, 4),
            vocab_drift_rate=round(drift_rate, 4),
        )


# ---------------------------------------------------------------------------
# GROWTH TRACKER -- R(n) over the fish's lifetime
# ---------------------------------------------------------------------------

class GrowthTracker:
    """Tracks R(n) over the fish's lifetime.

    Call record() after each eat or re-eat. The tracker computes
    snapshots and deltas automatically. Save/load for persistence
    across sessions.

    The growth curve IS the evidence. If R(n) follows k*log(n)+r,
    the fish is compressing reality. If it plateaus, the fish found
    its language. If it drops, something broke.
    """

    def __init__(self):
        self.snapshots: List[FishSnapshot] = []
        self.deltas: List[DeltaReport] = []

    def record(self, engine) -> Optional[DeltaReport]:
        """Take a snapshot and compute delta from last.

        Returns the DeltaReport if there was a previous snapshot,
        None if this is the first recording.
        """
        snapshot = FishSnapshot.capture(engine)
        self.snapshots.append(snapshot)

        if len(self.snapshots) >= 2:
            delta = DeltaReport.compare(self.snapshots[-2], self.snapshots[-1])
            self.deltas.append(delta)
            return delta

        return None

    def r_n_curve(self) -> List[Tuple[int, float]]:
        """Return (snapshot_index, r_n) pairs for plotting.

        The x-axis is snapshot index (proxy for exchange count).
        The y-axis is compression efficiency.
        If this follows k*log(n)+r, the fish is real.
        """
        return [(i, s.r_n) for i, s in enumerate(self.snapshots)]

    def coupling_curve(self) -> List[Tuple[int, float]]:
        """Return (snapshot_index, coupling_density) pairs.

        Should grow then plateau. The plateau IS the ~170 glyph
        saturation from the paper.
        """
        return [(i, s.coupling_density) for i, s in enumerate(self.snapshots)]

    def stability_curve(self) -> List[Tuple[int, float]]:
        """Return (delta_index, stability_ratio) pairs.

        High stability across re-eat cycles = real structure.
        Low stability = noise washing out. This IS the Bell test
        applied to re-eat cycles instead of random shuffles.
        """
        return [(i, d.stability_ratio) for i, d in enumerate(self.deltas)]

    def drift_curve(self) -> List[Tuple[int, float]]:
        """Return (delta_index, vocab_drift_rate) pairs.

        High drift early = still learning. High drift late = instability.
        Low drift = convergence. The drift rate IS the d-trajectory.
        When it stabilizes, the fish has found its language.
        """
        return [(i, d.vocab_drift_rate) for i, d in enumerate(self.deltas)]

    def dimension_balance(self) -> Dict[str, float]:
        """Current dimension balance from the latest snapshot.

        Returns the distribution across 8 QLP dimensions.
        A balanced fish covers all dimensions. A lopsided fish
        has blind spots. DE-heavy and IC-empty = technically
        competent but emotionally blind.
        """
        if not self.snapshots:
            return {dim: 0.0 for dim in DIMENSIONS}
        return dict(self.snapshots[-1].dimension_distribution)

    def dimension_entropy(self) -> float:
        """Shannon entropy of the dimension distribution.

        Max entropy (3.0 for 8 dims) = perfectly balanced.
        Low entropy = concentrated in few dimensions.
        This is a single number for "how well-rounded is the fish."
        """
        dist = self.dimension_balance()
        total = sum(dist.values())
        if total == 0:
            return 0.0
        probs = [v / total for v in dist.values() if v > 0]
        return -sum(p * math.log2(p) for p in probs if p > 0)

    def fit_r_n_curve(self) -> Optional[Tuple[float, float, float]]:
        """Fit R(n) = k * log(n) + r to the snapshot data.

        Returns (k, r, r_squared) or None if not enough data.
        k = growth rate. r = intercept. r_squared = fit quality.
        If r_squared > 0.9, the log model fits. The fish is compressing
        along the theoretical curve.
        """
        points = self.r_n_curve()
        if len(points) < 3:
            return None

        # Simple least-squares fit of y = k * log(x+1) + r
        xs = [math.log(i + 1) for i, _ in points]
        ys = [r for _, r in points]
        n = len(xs)

        sum_x = sum(xs)
        sum_y = sum(ys)
        sum_xy = sum(x * y for x, y in zip(xs, ys))
        sum_x2 = sum(x * x for x in xs)

        denom = n * sum_x2 - sum_x * sum_x
        if abs(denom) < 1e-10:
            return None

        k = (n * sum_xy - sum_x * sum_y) / denom
        r = (sum_y - k * sum_x) / n

        # R-squared
        y_mean = sum_y / n
        ss_tot = sum((y - y_mean) ** 2 for y in ys)
        ss_res = sum((y - (k * x + r)) ** 2 for x, y in zip(xs, ys))
        r_squared = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

        return (round(k, 4), round(r, 4), round(r_squared, 4))

    def growth_summary(self) -> str:
        """Human-readable summary of the fish's growth arc.

        One page. Everything that matters. A cold instance can
        read this and know whether the fish is healthy.
        """
        if not self.snapshots:
            return "No snapshots recorded. Call tracker.record(engine) first."

        latest = self.snapshots[-1]
        lines = [
            f"=== Fish Growth Summary ===",
            f"Snapshots: {len(self.snapshots)}  |  "
            f"Crystals: {latest.crystal_count}  |  "
            f"Formations: {latest.formation_count}  |  "
            f"Epoch: {latest.epoch}",
            "",
        ]

        # R(n) curve
        lines.append(f"R(n): {latest.r_n:.4f}")
        fit = self.fit_r_n_curve()
        if fit:
            k, r, r2 = fit
            lines.append(
                f"  Fit: R(n) = {k:.4f} * log(n) + {r:.4f}  "
                f"(R^2 = {r2:.4f}{'  -- good fit' if r2 > 0.9 else ''})"
            )
        lines.append("")

        # Coupling density
        lines.append(f"Coupling density: {latest.coupling_density:.6f}")
        lines.append(f"Mean coupling: {latest.mean_coupling:.4f}")
        lines.append("")

        # Vocab
        lines.append(
            f"Vocab: {len(latest.vocab)} terms  "
            f"({latest.vocab_grammar_fraction:.1%} canonical grammar)"
        )
        if self.deltas:
            last_delta = self.deltas[-1]
            lines.append(
                f"  Last drift: {last_delta.vocab_drift_rate:.1%}  "
                f"(+{len(last_delta.vocab_added)} -{len(last_delta.vocab_removed)})"
            )
        lines.append("")

        # Formation stability
        if self.deltas:
            last_delta = self.deltas[-1]
            lines.append(f"Formation stability: {last_delta.stability_ratio:.1%}")
            if last_delta.formations_new:
                lines.append(f"  New: {', '.join(last_delta.formations_new[:5])}")
            if last_delta.formations_lost:
                lines.append(f"  Lost: {', '.join(last_delta.formations_lost[:5])}")
            if last_delta.formations_stable:
                lines.append(
                    f"  Stable: {', '.join(last_delta.formations_stable[:5])}"
                )
            lines.append("")

        # Dimension balance
        dist = latest.dimension_distribution
        entropy = self.dimension_entropy()
        max_entropy = math.log2(len(DIMENSIONS))  # 3.0 for 8 dims
        balance_pct = (entropy / max_entropy * 100) if max_entropy > 0 else 0

        lines.append(f"Dimension balance: {balance_pct:.0f}% (entropy {entropy:.2f}/{max_entropy:.2f})")
        # Sort dimensions by weight to show where the fish lives
        sorted_dims = sorted(dist.items(), key=lambda x: -x[1])
        for dim, val in sorted_dims:
            bar_len = int(val * 40) if val > 0 else 0
            bar = "#" * bar_len
            lines.append(f"  {dim}: {val:6.4f} {bar}")

        # Blind spots
        weak_dims = [dim for dim, val in sorted_dims if val < 0.05]
        if weak_dims:
            lines.append(f"  BLIND SPOTS: {', '.join(weak_dims)}")
        lines.append("")

        # Overall health assessment
        lines.append("--- Health ---")
        health_notes = []
        if latest.crystal_count < 10:
            health_notes.append("Young fish. Feed more content.")
        if latest.formation_count == 0 and latest.crystal_count > 5:
            health_notes.append("Crystals but no formations. Coupling may be too weak.")
        if self.deltas and self.deltas[-1].stability_ratio < 0.3:
            health_notes.append(
                "Low formation stability. Noise may be washing out structure."
            )
        if self.deltas and self.deltas[-1].vocab_drift_rate > 0.5:
            health_notes.append("High vocab drift. Fish is still learning rapidly.")
        if len(weak_dims) >= 3:
            health_notes.append(
                f"Lopsided. {len(weak_dims)} of 8 dimensions underrepresented."
            )
        if not health_notes:
            health_notes.append("Fish looks healthy.")

        for note in health_notes:
            lines.append(f"  {note}")

        return "\n".join(lines)

    def save(self, path: Path):
        """Persist growth data to JSON."""
        data = {
            "saved": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "snapshot_count": len(self.snapshots),
            "delta_count": len(self.deltas),
            "snapshots": [asdict(s) for s in self.snapshots],
            "deltas": [asdict(d) for d in self.deltas],
        }
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def load(self, path: Path):
        """Load growth data from JSON."""
        path = Path(path)
        if not path.exists():
            return

        data = json.loads(path.read_text(encoding="utf-8"))

        self.snapshots = []
        for s in data.get("snapshots", []):
            self.snapshots.append(FishSnapshot(**s))

        self.deltas = []
        for d in data.get("deltas", []):
            self.deltas.append(DeltaReport(**d))


# ---------------------------------------------------------------------------
# INTERNAL HELPERS
# ---------------------------------------------------------------------------

def _coupling_stats(crystals: List[Crystal]) -> Tuple[float, float]:
    """Compute mean coupling strength and coupling density.

    Returns (mean_gamma, density) where density = edges / possible_edges.
    """
    if len(crystals) < 2:
        return (0.0, 0.0)

    total_gamma = 0.0
    edge_count = 0
    seen_edges = set()

    for c in crystals:
        for coupled_id, g in c.couplings:
            edge_key = tuple(sorted([c.id, coupled_id]))
            if edge_key not in seen_edges:
                seen_edges.add(edge_key)
                total_gamma += g
                edge_count += 1

    n = len(crystals)
    possible_edges = n * (n - 1) / 2
    mean_gamma = total_gamma / edge_count if edge_count > 0 else 0.0
    density = edge_count / possible_edges if possible_edges > 0 else 0.0

    return (mean_gamma, density)


def _dimension_distribution(crystals: List[Crystal]) -> Dict[str, float]:
    """Average resonance vector across all crystals, mapped to QLP dimensions.

    If crystals have 8-dim resonance vectors, map directly to DIMENSIONS.
    If longer (from PCA), take the first 8.
    If shorter or empty, fill with zeros.
    """
    dist = {dim: 0.0 for dim in DIMENSIONS}
    if not crystals:
        return dist

    count = 0
    accum = [0.0] * len(DIMENSIONS)

    for c in crystals:
        # Prefer resonance (PCA-reduced), fall back to mi_vector
        vec = c.resonance if c.resonance else c.mi_vector
        if not vec:
            continue
        count += 1
        for i in range(min(len(vec), len(DIMENSIONS))):
            accum[i] += abs(vec[i])  # abs because dimensions are magnitudes

    if count > 0:
        for i, dim in enumerate(DIMENSIONS):
            dist[dim] = accum[i] / count

    # Normalize to sum to 1 for entropy calculation
    total = sum(dist.values())
    if total > 0:
        dist = {k: v / total for k, v in dist.items()}

    return dist
