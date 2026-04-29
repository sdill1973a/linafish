#!/usr/bin/env python3
"""Migrate an existing fish to the addressed-formations index.

Commit 3 of 5 in the §RECOUPLE.IN.PLACE follow-up. One-shot batch script
that takes a fish state directory holding crystals coupled+formation-detected
under the legacy global-BFS path, and re-files every crystal into the new
``formation_index`` by its grammar address. After this runs, every
subsequent eat() on the fish (with addressed_formations=True) operates in
constant time regardless of corpus size.

The migration does NOT re-vectorize — every crystal already carries its
``cognitive_vector`` from the original crystallize_text call. We re-address.

Cost at 387K crystals (.67 federation room corpus):
  - O(N) addressing sweep + aggregate fold
  - One O(N) JSON dump in _save_state at the end
  - Total: under 2 minutes

Idempotent — re-running it re-derives the same Formation objects from the
same crystals, modulo Formation.id assignment which depends on iteration
order. Safe to run after schema changes.

Usage:
    python scripts/migrate_to_addressed_formations.py \\
        --state-dir /home/sdill/codebooks \\
        --name anchor

The script does NOT mutate the input state until the final save_state.
A failure mid-migration leaves the original fish.md / state files
untouched and the JSONL crystal log intact.
"""

import argparse
import sys
import time
from pathlib import Path

# Ensure the repo root is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from linafish.engine import FishEngine
from linafish.formations import Formation, formation_address


def migrate(state_dir: Path, name: str, dry_run: bool = False,
            verbose: bool = False) -> dict:
    """Run the migration. Returns a summary dict.

    Args:
        state_dir: path to the fish state directory.
        name: fish name (matches the *_crystals.jsonl filename prefix).
        dry_run: when True, builds the addressed index in memory but does
            NOT write fish.md or save state. Useful for validating the
            migration produces sensible output before committing to it.
        verbose: print progress every 10000 crystals.

    Returns:
        Summary dict with phase timings, crystal counts, formation counts,
        UNKNOWN-bucket size, and address space statistics.
    """
    summary = {
        "state_dir": str(state_dir),
        "name": name,
        "dry_run": dry_run,
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    t_total = time.perf_counter()

    # Phase 0: construct the engine. addressed_formations=True so
    # subsequent reads use the new path. enable_gardener=False because
    # there's no gardener wired yet (commit 4 lands that).
    print(f"[phase 0] loading engine from {state_dir}/{name}_crystals.jsonl ...")
    t = time.perf_counter()
    engine = FishEngine(
        state_dir=state_dir,
        name=name,
        addressed_formations=True,
        git_autocommit=False,
    )
    summary["phase_0_load_seconds"] = round(time.perf_counter() - t, 2)
    summary["crystal_count"] = len(engine.fish.crystals)
    print(f"  loaded {summary['crystal_count']} crystals in "
          f"{summary['phase_0_load_seconds']}s")

    if summary["crystal_count"] == 0:
        print("[phase 0] empty fish — nothing to migrate.")
        summary["status"] = "empty"
        return summary

    # Phase 1: clear any existing formation_index (a fresh re-derivation)
    # and address each crystal, folding into the index.
    print(f"[phase 1] addressing {summary['crystal_count']} crystals ...")
    t = time.perf_counter()
    engine.formation_index = {}
    unknown_count = 0
    for i, c in enumerate(engine.fish.crystals):
        addr = formation_address(
            cognitive_vector=getattr(c, 'cognitive_vector', None),
            resonance=getattr(c, 'resonance', None),
            keywords=getattr(c, 'keywords', None),
        )
        c.formation = addr
        if addr == "UNKNOWN":
            unknown_count += 1

        formation = engine.formation_index.get(addr)
        if formation is None:
            formation = Formation(
                id=len(engine.formation_index),
                name=addr,
                keywords=[],
                member_ids=[],
                centroid=[0.0] * 8,
                representative_text="",
                crystal_count=0,
                cognitive_centroid=[0.0] * 8,
            )
            engine.formation_index[addr] = formation

        formation.member_ids.append(c.id)
        formation.update_with(c)

        if verbose and (i + 1) % 10000 == 0:
            print(f"  {i + 1} addressed; index has "
                  f"{len(engine.formation_index)} formations")

    summary["phase_1_address_seconds"] = round(time.perf_counter() - t, 2)
    summary["formation_count"] = len(engine.formation_index)
    summary["unknown_count"] = unknown_count
    summary["unknown_pct"] = round(
        100.0 * unknown_count / max(summary["crystal_count"], 1), 2
    )
    print(f"  addressed {summary['crystal_count']} crystals into "
          f"{summary['formation_count']} formations in "
          f"{summary['phase_1_address_seconds']}s")
    print(f"  UNKNOWN bucket: {unknown_count} crystals "
          f"({summary['unknown_pct']}% of corpus)")

    # Phase 2: top-N report
    top_formations = sorted(
        engine.formation_index.values(),
        key=lambda f: f.crystal_count,
        reverse=True,
    )[:10]
    summary["top_formations"] = [
        {
            "name": f.name,
            "crystal_count": f.crystal_count,
            "cog_amplitude": round(f.cog_amplitude, 4),
            "mean_ache": round(f.mean_ache, 4),
            "content_diversity": round(f.content_diversity, 4),
            "compression_score": round(f.compression_score, 4),
        }
        for f in top_formations
    ]
    print("\n[phase 2] top 10 formations by crystal_count:")
    for f in top_formations:
        print(f"  {f.name:50s} {f.crystal_count:>7} crystals  "
              f"cog={f.cog_amplitude:.3f} ache={f.mean_ache:.3f} "
              f"div={f.content_diversity:.3f} score={f.compression_score:.4f}")

    # Phase 3: publish the engine.formations list from the index
    engine.formations = list(engine.formation_index.values())

    if dry_run:
        print("\n[phase 3] DRY RUN — skipping save. No state written to disk.")
        summary["status"] = "dry_run"
    else:
        # Phase 3: save state. This is the irreducible serialization cost.
        print(f"\n[phase 3] saving state to {state_dir} ...")
        t = time.perf_counter()
        engine._save_state(commit=False)
        summary["phase_3_save_seconds"] = round(time.perf_counter() - t, 2)
        print(f"  saved in {summary['phase_3_save_seconds']}s")
        summary["status"] = "migrated"

    summary["total_seconds"] = round(time.perf_counter() - t_total, 2)
    summary["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    print(f"\n[done] total: {summary['total_seconds']}s")
    return summary


def main():
    parser = argparse.ArgumentParser(
        description="Migrate a fish to addressed-formations.",
    )
    parser.add_argument(
        "--state-dir", required=True, type=Path,
        help="Path to the fish state directory "
             "(e.g. /home/sdill/codebooks or ~/.linafish/).",
    )
    parser.add_argument(
        "--name", required=True,
        help="Fish name (matches the *_crystals.jsonl filename prefix).",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Build the addressed index in memory but don't save. "
             "Useful for validating output before committing.",
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Print progress every 10000 crystals.",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Emit summary as JSON to stdout in addition to human prints.",
    )
    args = parser.parse_args()

    if not args.state_dir.exists():
        print(f"error: state_dir {args.state_dir} does not exist",
              file=sys.stderr)
        sys.exit(1)

    summary = migrate(
        state_dir=args.state_dir,
        name=args.name,
        dry_run=args.dry_run,
        verbose=args.verbose,
    )

    if args.json:
        import json
        print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
