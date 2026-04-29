"""Formation Gardener — periodic maintenance for addressed formations.

Commit 3 of 5 in the §RECOUPLE.IN.PLACE follow-up. The gardener runs
maintenance the addressed-formations path defers from the eat() hot
path: fission of oversized formations, formation-health status JSON
emission, and (in commit 4) the DIGNITY/POVERTY/PATHOLOGY/CONTAGION
regime classification port from Ice-9.

This skeleton lands the structure and the status JSON write. Full
fission split logic and the regime port arrive in commit 4 alongside
the Ice-9 surface restoration.

Wakes on:
  - GARDEN_INTERVAL_SEC periodic timer (default 600s)
  - GARDEN_NUDGE_EATS threshold (default 5000 eats since last pass)
  - explicit FishEngine.gardener.run() call

Operates on a snapshot of self.formation_index under a brief lock so
/pfc and eat() keep flowing during the pass. Never blocks the eat()
hot path.

The status JSON file (data/{name}_lattice_status.json) matches the
shape of ice9a_status.json so any downstream consumer that reads
Ice-9's output can read linafish's lattice status without retraining.
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

        # Placeholder regime counts. Commit 4 ports the real Ice-9
        # classifier; the keys here match ice9a_status.json's shape so
        # downstream consumers don't break when commit 4 lands real
        # values. Until then everything classifies as "unclassified".
        summary["counts"] = {
            "DIGNITY": 0,
            "POVERTY": 0,
            "PATHOLOGY": 0,
            "CONTAGION": 0,
            "unclassified": len(self.engine.formation_index),
        }
        summary["grade"] = "?"  # commit 4 fills this in
        summary["fp_mean"] = round(
            # Inverted cog_amplitude as a placeholder fp analog —
            # amplitude in [0, 1] → 1.0 - amplitude in [0, 1].
            # commit 4 replaces this with real fp_estimate.
            1.0 - summary["cog_amplitude_mean"], 4
        )

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
