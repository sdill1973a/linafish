"""Formation Gardener — periodic maintenance for addressed formations.

Commits 3-4 of 5 in the §RECOUPLE.IN.PLACE follow-up. The gardener runs
maintenance the addressed-formations path defers from the eat() hot
path: oversize fission identification and formation-health status JSON
emission, ported from the Ice-9 lineage that has been Anchor's
metacognitive surface since 2026-03-09.

Commit 3 (skeleton): structure + atomic status JSON write
Commit 4 (regime port): DIGNITY/POVERTY/PATHOLOGY/CONTAGION classifier
   ported from ice9a.py:582-625, operating on grammar signals
   already on Formation (compression_score / cog_amplitude / mean_ache
   / content_diversity) instead of the v2-memory anchor-set cosine that
   the original Ice-9 used.

The classification semantics are preserved:
  POVERTY   — formation is too grounded (high signal density, low
              engagement). Bedrock crystals, system facts. Uninteresting.
  DIGNITY   — well-grounded, varied content with real engagement.
              The healthy target regime.
  PATHOLOGY — low signal density. Operational noise, tool spam,
              broadcast templates with no ground truth.
  CONTAGION — pathology AT SCALE: oversize formation, low diversity,
              no grounded crystals to anchor it. The actionable warning
              regime — needs data injection or pruning.

The status JSON file (data/{name}_lattice_status.json) matches the
shape of ice9a_status.json so any downstream consumer that reads
Ice-9's output can read linafish's lattice status without retraining.

Wakes on:
  - GARDEN_INTERVAL_SEC periodic timer (default 600s)
  - GARDEN_NUDGE_EATS threshold (default 5000 eats since last pass)
  - explicit FishEngine.gardener.run() call

Operates on a snapshot of self.formation_index under a brief lock so
/pfc and eat() keep flowing during the pass. Never blocks the eat()
hot path.
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from .formations import Formation, FISSION_THRESHOLD

if TYPE_CHECKING:
    from .engine import FishEngine


GARDEN_INTERVAL_SEC = 600    # 10 min default; daemon can override
GARDEN_NUDGE_EATS = 5000     # threshold-triggered fast pass
SUB_ADDRESS_SEPARATOR = "/"  # hierarchical sub-address marker for fission output

# Health regime thresholds. Ported from ice9a.py:582-592 in spirit, but
# applied to ``compression_score`` (mean_ache × cog_amplitude × trust ×
# content_diversity) instead of the anchor-set fp_estimate that v2 memory
# used. The threshold values are deliberately the same numerical values as
# Ice-9's fp cutoffs (0.6 / 1.2) but interpreted on the inverted axis:
# higher compression_score → lower fp_analog → more grounded.
#
# fp_analog = clamp(2.0 - compression_score * 4.0, 0.0, 2.0)
#   compression_score = 0.5  →  fp_analog = 0.0  (POVERTY — rock-solid grounded)
#   compression_score = 0.3  →  fp_analog = 0.8  (DIGNITY — healthy)
#   compression_score = 0.2  →  fp_analog = 1.2  (DIGNITY/PATHOLOGY boundary)
#   compression_score = 0.1  →  fp_analog = 1.6  (PATHOLOGY)
#   compression_score = 0.0  →  fp_analog = 2.0  (PATHOLOGY ceiling)
#
# The 4.0 multiplier calibrates against typical compression_score values
# (0.05 - 0.5 in observed federation corpora). Re-tunable; commit 5 may
# adjust based on production telemetry.
COMPRESSION_TO_FP_MULTIPLIER = 4.0
FP_POVERTY_CUTOFF = 0.6
FP_DIGNITY_CUTOFF = 1.2

# CONTAGION criteria: pathology AT SCALE without grounded crystals.
# Mirrors ice9a.py:591 — pat > 0.8 * size and pov == 0.
# In linafish-terms: a PATHOLOGY-classified formation that is large
# (>= CONTAGION_MIN_SIZE) and has very low diversity (broadcast/template
# saturation). The "no grounded crystals" check translates to
# content_diversity below CONTAGION_DIVERSITY_FLOOR — a formation
# saturated with retransmission has nothing to anchor it.
CONTAGION_MIN_SIZE = 50
CONTAGION_DIVERSITY_FLOOR = 0.3

# Minimum formation size for regime classification. A 1-3 crystal
# "formation" hasn't accumulated enough signal for the
# DIGNITY/POVERTY/PATHOLOGY/CONTAGION semantics to apply — its
# compression_score reflects that every text is "unique" (div=1.0)
# in a tiny sample, not that it's bedrock-grounded. Below this
# threshold, classify_health returns "SEEDLING" — bookkeeping
# only, not part of the regime grade.
#
# Calibrated 2026-04-30 against a real anchor-writing corpus
# (6823 crystals, 329 addressed formations): without this gate,
# 88.8% of formations classified as POVERTY purely because most
# were 1-3 crystals with maximum diversity. With this gate, the
# regime mix reflects substantive formations only.
SEEDLING_MAX_SIZE = 5


def _compression_to_fp_analog(compression_score: float) -> float:
    """Map compression_score to a [0, 2] fp_analog axis.

    Higher compression_score → lower fp_analog → more grounded (POVERTY
    end of spectrum). Lower compression_score → higher fp_analog → more
    noise (PATHOLOGY end). Boundary at fp_analog 0.6 / 1.2 matches
    Ice-9's regime cutoffs.

    See module docstring for the calibration rationale.
    """
    fp = 2.0 - compression_score * COMPRESSION_TO_FP_MULTIPLIER
    return max(0.0, min(2.0, fp))


def classify_health(formation: Formation) -> str:
    """Classify a formation's health regime.

    Ported from ice9a.py:582-592. Operates on Formation.compression_score
    as the fp_analog substrate — the same composite signal v7 surface
    ranking uses (mean_ache × cog_amplitude × trust × content_diversity).
    No anchor-set / sentence-transformers dependency; the fish judges
    itself by its own grammar.

    Regimes:
      SEEDLING  — formation has too few crystals (<= SEEDLING_MAX_SIZE)
                  for the regime semantics to apply. Bookkeeping only;
                  not counted in regime grade.
      POVERTY   — formation is bedrock-grounded (system facts, sensor
                  data, factual citations). compression_score very high.
      DIGNITY   — healthy: well-grounded, varied content with real
                  engagement.
      PATHOLOGY — low signal density. Operational noise.
      CONTAGION — pathology + oversize + no diversity. The actionable
                  warning that the formation is broadcast pollution.
    """
    if formation.crystal_count <= SEEDLING_MAX_SIZE:
        return "SEEDLING"

    fp = _compression_to_fp_analog(formation.compression_score)

    if fp < FP_POVERTY_CUTOFF:
        regime = "POVERTY"
    elif fp <= FP_DIGNITY_CUTOFF:
        regime = "DIGNITY"
    else:
        regime = "PATHOLOGY"

    # CONTAGION override: oversize PATHOLOGY with broadcast-template
    # diversity. The "ALL MINDS" formation pattern that ate the .67
    # federation room.
    if (regime == "PATHOLOGY"
            and formation.crystal_count >= CONTAGION_MIN_SIZE
            and formation.content_diversity < CONTAGION_DIVERSITY_FLOOR):
        regime = "CONTAGION"

    return regime


def assign_grade(counts: dict) -> str:
    """Letter grade from regime counts. Mirrors ice9a's grade computation
    in spirit — high CONTAGION drags grade down; high DIGNITY raises it.

    SEEDLING formations are excluded from the denominator — the grade
    reflects substantive-formation health, not how many tiny addresses
    exist. A corpus with 200 seedlings and 10 healthy formations gets
    the same grade as one with 0 seedlings and 10 healthy formations.

    A: ≥80% DIGNITY, no CONTAGION
    B: ≥60% DIGNITY, ≤5% CONTAGION
    C: ≥40% DIGNITY, ≤15% CONTAGION
    D: anything else
    """
    classified = {k: v for k, v in counts.items() if k != "SEEDLING"}
    total = sum(classified.values())
    if total == 0:
        return "?"
    dignity_pct = classified.get("DIGNITY", 0) / total
    contagion_pct = classified.get("CONTAGION", 0) / total
    if dignity_pct >= 0.80 and contagion_pct == 0.0:
        return "A"
    if dignity_pct >= 0.60 and contagion_pct <= 0.05:
        return "B"
    if dignity_pct >= 0.40 and contagion_pct <= 0.15:
        return "C"
    return "D"


class FormationGardener:
    """Background maintenance for the addressed formation_index.

    Lives alongside a FishEngine and runs maintenance passes on its
    formation_index. Stateless across passes — each run() reads the
    current state, computes its work, writes its outputs. Any state
    that needs to persist (e.g. last-pass timestamp) lives on the
    engine or on disk in the lattice_status.json file.

    Commit 3 (this file): skeleton + lattice_status.json write
    Commit 4 (later): port DIGNITY/POVERTY/PATHOLOGY/CONTAGION regime
                       classification from ice9a.py:582-625, full
                       fission split logic with hierarchical
                       sub-addresses
    Commit 5 (later): periodic background thread driver
    """

    def __init__(self, engine: "FishEngine"):
        self.engine = engine
        self.last_run_at: Optional[datetime] = None
        self.last_run_summary: Optional[dict] = None

    def _status_path(self) -> Path:
        """Path to data/{name}_lattice_status.json, alongside other status files."""
        # State dir is per-fish; lattice_status.json lives there so a
        # multi-fish workstation has independent statuses per fish.
        return Path(self.engine.state_dir) / f"{self.engine.name}_lattice_status.json"

    def run(self, write_status: bool = True) -> dict:
        """Run one maintenance pass over the engine's formation_index.

        Returns a summary dict with counts and timings. When
        ``write_status`` is True (default), also writes the status JSON
        so consumers can read the latest health.

        Skeleton behavior (commit 3):
          - Identify oversized formations
          - Compute basic counts and an aggregate fp_mean stand-in
            (cog_amplitude inverted: low amplitude = high "fp" analog)
          - Write status JSON in ice9a_status.json's shape

        SINGLE-THREADED ONLY (until a future commit lands the lock).
        ``run()`` iterates ``self.engine.formation_index.values()``
        directly. ``FishEngine._file_into_formation`` mutates
        ``formation_index`` in the eat() hot path. If both run on the
        same engine in different threads, ``run()`` will raise
        ``RuntimeError: dictionary changed size during iteration`` (or
        worse, silently read partially-mutated formations whose
        ``member_ids`` were appended but whose aggregates are mid-update).

        For now, callers MUST guarantee no eat() is in flight when
        ``run()`` executes. The intended deployment shape (manual call,
        explicit /pfc-side maintenance hook, end-of-eat batch sweep) is
        single-threaded by construction. The deferred background-thread
        driver (commit 5+ in the §RECOUPLE.IN.PLACE roadmap) MUST land an
        engine-level lock alongside it, snapshotting the formation_index
        under that lock before iteration. Codex flagged this as a
        BLOCKING concurrency issue 2026-04-30 — the fix is a
        commit-5-prerequisite, not a commit-4 patch.
        """
        t0 = time.perf_counter()
        summary = {
            "name": self.engine.name,
            "scanned_at": datetime.now(timezone.utc).isoformat(),
            "n_formations": len(self.engine.formation_index),
            "n_crystals": len(self.engine.fish.crystals),
        }

        if not self.engine.formation_index:
            summary["status"] = "empty"
            self.last_run_summary = summary
            self.last_run_at = datetime.now(timezone.utc)
            if write_status:
                self._write_status(summary)
            return summary

        # Identify oversized formations: anything above FISSION_THRESHOLD
        # of total crystal count is a candidate for fission. Commit 4
        # will actually split them; commit 3 just reports them.
        n_total = max(summary["n_crystals"], 1)
        threshold_count = max(int(n_total * FISSION_THRESHOLD), 1)
        oversize = [
            f for f in self.engine.formation_index.values()
            if f.crystal_count > threshold_count
        ]
        summary["oversize_threshold_count"] = threshold_count
        summary["oversize_count"] = len(oversize)
        summary["oversize_formations"] = [
            {
                "name": f.name,
                "crystal_count": f.crystal_count,
                "compression_score": round(f.compression_score, 4),
            }
            for f in oversize
        ]

        # Aggregate stats (placeholder for the full Ice-9 regime port in
        # commit 4). For now we surface what's already on Formation.
        amps = [f.cog_amplitude for f in self.engine.formation_index.values()]
        aches = [f.mean_ache for f in self.engine.formation_index.values()]
        summary["cog_amplitude_mean"] = round(
            sum(amps) / max(len(amps), 1), 4
        )
        summary["mean_ache_mean"] = round(
            sum(aches) / max(len(aches), 1), 4
        )

        # Top-K by compression_score — the v7 surface ranking signal
        from .formations import formation_rank_key
        top = sorted(
            self.engine.formation_index.values(),
            key=formation_rank_key,
            reverse=True,
        )[:10]
        summary["top_compression_score"] = [
            {
                "name": f.name,
                "crystal_count": f.crystal_count,
                "compression_score": round(f.compression_score, 4),
                "cog_amplitude": round(f.cog_amplitude, 4),
                "mean_ache": round(f.mean_ache, 4),
                "content_diversity": round(f.content_diversity, 4),
            }
            for f in top
        ]

        # §RECOUPLE.IN.PLACE commit 4 — Ice-9 regime classification
        # ported onto Formation grammar signals (compression_score as
        # fp_analog substrate). Each formation gets a regime tag; the
        # counts roll up; the grade summarizes fleet health.
        counts = {
            "SEEDLING": 0,
            "POVERTY": 0,
            "DIGNITY": 0,
            "PATHOLOGY": 0,
            "CONTAGION": 0,
        }
        regime_per_formation = {}
        fp_analogs = []
        for f in self.engine.formation_index.values():
            regime = classify_health(f)
            counts[regime] += 1
            regime_per_formation[f.name] = regime
            fp_analogs.append(_compression_to_fp_analog(f.compression_score))

        summary["counts"] = counts
        summary["grade"] = assign_grade(counts)
        # fp_mean across all formations — analogous to ice9a's fp_mean
        # but on the linafish fp_analog (derived from compression_score).
        if fp_analogs:
            summary["fp_mean"] = round(
                sum(fp_analogs) / len(fp_analogs), 4
            )
        else:
            summary["fp_mean"] = 0.0

        # contagion_top — the actionable list. Ported from ice9a's
        # contagion_top key in the status file. Top-N by fp_analog
        # within the CONTAGION regime; what fish_taste_anchor's hook
        # would surface in the per-turn `<subconscious>` block.
        contagion_formations = [
            f for f in self.engine.formation_index.values()
            if regime_per_formation.get(f.name) == "CONTAGION"
        ]
        contagion_formations.sort(
            key=lambda f: f.crystal_count,
            reverse=True,
        )
        summary["contagion_top"] = [
            {
                "id": f.name,
                "fp": round(_compression_to_fp_analog(f.compression_score), 4),
                "size": f.crystal_count,
                "compression_score": round(f.compression_score, 4),
                "content_diversity": round(f.content_diversity, 4),
            }
            for f in contagion_formations[:5]
        ]

        summary["pass_seconds"] = round(time.perf_counter() - t0, 3)
        summary["status"] = "ran"

        self.last_run_at = datetime.now(timezone.utc)
        self.last_run_summary = summary
        if write_status:
            self._write_status(summary)
        return summary

    def _write_status(self, summary: dict) -> None:
        """Write summary to {state_dir}/{name}_lattice_status.json.

        Atomic write via temp+rename so concurrent readers never see a
        half-written file.
        """
        path = self._status_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        body = dict(summary)
        body["written_at"] = datetime.now(timezone.utc).isoformat()
        tmp.write_text(json.dumps(body, indent=2), encoding="utf-8")
        tmp.replace(path)
