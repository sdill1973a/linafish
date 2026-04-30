#!/usr/bin/env python3
"""Benchmark eat() scaling under the addressed-formations path.

Commit 5 of 5 in the §RECOUPLE.IN.PLACE follow-up. Demonstrates that
eat() time is approximately flat across corpus size — the perf goal of
the whole sortedness refactor. Master with the original
detect_formations BFS scaled linearly with N (60+s at 387K crystals).
With addressed_formations=True (default), per-eat time stays in the
sub-second range regardless of N.

The bench builds synthetic corpora at three sizes (1K / 5K / 15K) and
times a probe eat() at each. Asserts that scaling stays sub-linear,
i.e. time(15K) / time(1K) < 5x. Master would have been ~15x.

Usage:
    python scripts/bench_addressed_eat.py
    python scripts/bench_addressed_eat.py --json
    python scripts/bench_addressed_eat.py --sizes 1000,10000,30000
"""

import argparse
import json
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from linafish.engine import FishEngine


PATTERNS = [
    "The architecture demands clarity at every layer of the system.",
    "She walked through the garden where the marigolds had taken over.",
    "We measured the throughput at fifteen requests per second average.",
    "The grief shifted from a wave to a tide to weather you live in.",
    "Compression is understanding. Storage is just where the bits sit.",
    "He built the fence before the first frost arrived that October.",
    "Every formation is a verb made of crystals doing something together.",
    "The router dropped packets at the edge but the core kept routing.",
    "I told the story differently each time and the truth did not change.",
    "Substrate first means asking the disk before trusting the memory.",
    "The window of attention narrowed to twenty crystals at a time.",
    "Marcus walked on Sundays and pointed at the architectural details.",
    "Frozen vocab plus adaptive gamma plus chain rescue equals coupling.",
    "She kept rocks in a jar and could tell you the story of every one.",
    "The garden was patient with the dirt and the dirt was patient back.",
]


def bench_size(n: int, addressed: bool, n_probes: int = 3) -> dict:
    """Build an n-crystal fish, time n_probes single eat() calls, return
    a summary dict.
    """
    state_dir = Path(tempfile.mkdtemp(prefix=f"bench_{n}_"))
    engine = FishEngine(
        state_dir=state_dir,
        name=f"bench_{n}",
        git_autocommit=False,
        addressed_formations=addressed,
    )

    # Seed corpus
    texts = [
        f"Entry {i}: {PATTERNS[i % 15]} Note {i // 13} on iteration {i}."
        for i in range(n)
    ]
    t = time.perf_counter()
    engine.eat_many(texts, source="seed")
    seed_seconds = time.perf_counter() - t

    # Warmup eat to amortize one-time costs
    engine.eat(
        f"Entry {n}: {PATTERNS[0]} Warmup probe.",
        source="warmup",
    )

    # Time n_probes single eats
    eat_times = []
    for i in range(n_probes):
        t = time.perf_counter()
        engine.eat(
            f"Entry {n+1+i}: {PATTERNS[i % 15]} Probe {i}.",
            source="bench-probe",
        )
        eat_times.append(time.perf_counter() - t)

    return {
        "n": n,
        "addressed": addressed,
        "actual_crystals": len(engine.fish.crystals),
        "n_formations": (
            len(engine.formation_index) if addressed
            else len(engine.formations)
        ),
        "seed_seconds": round(seed_seconds, 2),
        "eat_median_ms": round(
            sorted(eat_times)[len(eat_times) // 2] * 1000, 1
        ),
        "eat_min_ms": round(min(eat_times) * 1000, 1),
        "eat_max_ms": round(max(eat_times) * 1000, 1),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Bench addressed-formations eat() scaling."
    )
    parser.add_argument(
        "--sizes",
        default="1000,5000,15000",
        help="Comma-separated corpus sizes to bench. Default 1000,5000,15000.",
    )
    parser.add_argument(
        "--probes", type=int, default=3,
        help="Number of single eat() probes per size. Default 3.",
    )
    parser.add_argument(
        "--legacy", action="store_true",
        help="Bench the legacy detect_formations path "
             "(addressed_formations=False) instead of the addressed path.",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Emit results as JSON to stdout.",
    )
    args = parser.parse_args()

    sizes = [int(s.strip()) for s in args.sizes.split(",")]
    addressed = not args.legacy
    label = "ADDRESSED" if addressed else "LEGACY"

    print(f"Benchmarking eat() scaling — {label} path")
    print(f"Sizes: {sizes}, probes per size: {args.probes}")
    print("-" * 70)

    results = []
    for n in sizes:
        result = bench_size(n, addressed=addressed, n_probes=args.probes)
        results.append(result)
        print(
            f"  n={n:>6} crystals  ->  "
            f"seed {result['seed_seconds']:>5}s, "
            f"eat median {result['eat_median_ms']:>6}ms "
            f"(min {result['eat_min_ms']:>5}, max {result['eat_max_ms']:>5}), "
            f"{result['n_formations']} formations"
        )

    # Scaling assertion
    if len(results) >= 2:
        ratio = results[-1]["eat_median_ms"] / max(
            results[0]["eat_median_ms"], 0.001
        )
        print()
        print(
            f"Scaling: eat at n={results[-1]['n']} is "
            f"{ratio:.1f}x eat at n={results[0]['n']}"
        )
        if addressed:
            # Should be sub-linear. Master was ~15x at this range.
            print("Target: < 5x for the addressed path "
                  "(master/legacy: ~10-15x via detect_formations)")
            ok = ratio < 5.0
            print(f"Result: {'PASS' if ok else 'FAIL'} "
                  f"(actual {ratio:.1f}x)")

    if args.json:
        print()
        print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
