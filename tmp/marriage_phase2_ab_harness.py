"""A/B harness for chaincode-fish marriage Phase 2.

Spec test plan (data/chaincode_fish_marriage_spec.md, 2026-03-25):
  - Take crystals from today's ingest (known chain order)
  - Run coupling with and without temporal term
  - Compare formation count, size distribution, naming
  - Verify staleness filter blocks sensor data coupling

This script builds a synthetic corpus with deliberate narrative structure:
multiple "sessions" where each session has internally-similar texts but
sessions differ from each other. Crystals within a session are
chain-adjacent. Temporal rescue should lift borderline within-session
pairs that miss the gamma threshold; cross-session pairs should NOT
get rescued because they're chain-distant.

The stress test feeds sequential sensor-style identical-vector pairs
to confirm the staleness filter blocks chain-only coupling.

Output: tmp/marriage_phase2_ab_results.md
"""
import json
import random
import tempfile
from collections import defaultdict
from pathlib import Path

from linafish.crystallizer_v3 import Crystal, UniversalFish, gamma


# ---------------------------------------------------------------------------
# Corpus generators
# ---------------------------------------------------------------------------

def make_session(session_id: int, n_crystals: int, base_chain_seq: int,
                 attach_chain_seq: bool, vocab_size: int = 30) -> list:
    """Build n_crystals from one synthetic 'session.'

    Each session has an internal vocabulary signature: 3 'core' dims
    that fire reliably for every crystal in the session, plus per-
    crystal sampling of 2 more dims drawn from a session-specific
    pool of 6 candidates. This produces:
      - high intra-session gamma when crystals happen to draw the
        same auxiliary dims (the strong signal)
      - moderate intra-session gamma when crystals share core but
        not auxiliaries (the borderline band — where temporal
        rescue earns its keep)
      - low cross-session gamma (the negative control)

    Sparse vectors (no background noise floor) keep the Jaccard
    gamma sensitive to actual signal alignment instead of being
    dominated by uniformly-distributed noise mass.
    """
    crystals = []
    rng = random.Random(session_id * 1000 + 7)

    # Session-stable core: 3 dims that EVERY crystal in this session activates
    core_dims = rng.sample(range(vocab_size), 3)
    # Session-stable auxiliary pool: 6 candidate dims, each crystal draws 2
    aux_pool = rng.sample(
        [d for d in range(vocab_size) if d not in core_dims], 6
    )

    for k in range(n_crystals):
        vec = [0.0] * vocab_size
        for d in core_dims:
            vec[d] = 1.0
        chosen_aux = rng.sample(aux_pool, 2)
        for d in chosen_aux:
            vec[d] = 1.0

        c = Crystal(
            id=f"s{session_id}_c{k}",
            ts="",
            text=f"session {session_id} crystal {k}",
            source=f"session_{session_id}",
            mi_vector=vec,
            resonance=[],
            keywords=[],
            chain_seq=(base_chain_seq + k) if attach_chain_seq else None,
        )
        crystals.append(c)
    return crystals


def build_corpus(attach_chain_seq: bool, n_sessions: int = 10,
                 per_session: int = 20) -> list:
    """Build a corpus of n_sessions × per_session crystals.

    Chain seq runs continuously across sessions (so cross-session pairs
    are chain-distant by per_session-sized gaps).
    """
    crystals = []
    chain_pos = 0
    for sid in range(n_sessions):
        sess = make_session(sid, per_session, chain_pos, attach_chain_seq)
        crystals.extend(sess)
        chain_pos += per_session
    return crystals


# ---------------------------------------------------------------------------
# Coupling runner — captures both edges and rescue counts
# ---------------------------------------------------------------------------

def run_coupling(crystals, min_gamma=0.5, window=20):
    """Run _compute_couplings on a fresh fish wrapping the given crystals.

    Returns (edges, formations_by_size_distribution_text).
    """
    sandbox = tempfile.mkdtemp(prefix="marriage_ab_")
    fish = UniversalFish(state_dir=sandbox, autoload=False)
    # Reset coupling state (since we may re-run on the same crystals)
    for c in crystals:
        c.couplings = []
        c.wrapping_numbers = {}
    fish.crystals = list(crystals)
    fish._compute_couplings(fish.crystals, window=window, min_gamma=min_gamma)

    edges = sum(len(c.couplings) for c in crystals) // 2  # each edge counted twice
    return edges


def find_components(crystals):
    """Union-find over crystal couplings to enumerate connected components."""
    parent = {c.id: c.id for c in crystals}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x, y):
        rx, ry = find(x), find(y)
        if rx != ry:
            parent[rx] = ry

    for c in crystals:
        for other_id, _ in c.couplings:
            if other_id in parent:
                union(c.id, other_id)

    components = defaultdict(list)
    for c in crystals:
        components[find(c.id)].append(c.id)
    return list(components.values())


# ---------------------------------------------------------------------------
# A/B comparison
# ---------------------------------------------------------------------------

def compare_ab():
    """Run A/B: same corpus, with and without chain_seq."""
    # Match seeds for fair comparison
    crystals_with_chain = build_corpus(attach_chain_seq=True)
    crystals_without = build_corpus(attach_chain_seq=False)

    # Verify the corpora have identical mi_vectors (only chain_seq differs)
    for a, b in zip(crystals_with_chain, crystals_without):
        assert a.mi_vector == b.mi_vector, "corpus generation mismatch"

    # Diagnostic: sample gamma distribution to set a threshold in the
    # borderline band. We want a min_gamma where SOME within-session
    # pairs miss the threshold but are chain-adjacent — the rescue zone.
    sample_gammas = []
    rng = random.Random(0)
    for _ in range(2000):
        i = rng.randint(0, len(crystals_without) - 1)
        j = rng.randint(0, len(crystals_without) - 1)
        if i == j:
            continue
        sample_gammas.append(
            gamma(crystals_without[i].mi_vector, crystals_without[j].mi_vector)
        )
    sample_gammas.sort()
    p60 = sample_gammas[int(len(sample_gammas) * 0.60)]
    p75 = sample_gammas[int(len(sample_gammas) * 0.75)]
    p90 = sample_gammas[int(len(sample_gammas) * 0.90)]
    # Use p75 — high enough to exclude weak pairs, low enough that some
    # within-session pairs land just below it (the rescue zone).
    threshold = max(p75, 0.30)

    results = {
        "_diagnostic": {
            "gamma_p60": p60, "gamma_p75": p75, "gamma_p90": p90,
            "threshold_used": threshold,
        },
    }
    for label, corpus in [("without_chain", crystals_without),
                          ("with_chain", crystals_with_chain)]:
        edges = run_coupling(corpus, min_gamma=threshold, window=20)
        components = find_components(corpus)
        sizes = sorted([len(c) for c in components], reverse=True)
        nontrivial = [s for s in sizes if s > 1]

        results[label] = {
            "edges": edges,
            "components_total": len(components),
            "nontrivial_components": len(nontrivial),
            "largest_component": sizes[0] if sizes else 0,
            "size_distribution": sizes[:10],
        }

    return results


def stress_staleness():
    """Stress test: 100 sequential sensor-style readings with near-zero
    semantic overlap should NOT mega-couple via temporal proximity.
    The staleness filter inside coupling_strength must block.

    Sparse one-hot-style vectors. Each sensor is a single dimension
    spike. Pairwise gamma is exactly 0.0 between any two sensors
    spiking different dims. The first version of this harness used
    low-uniform-noise vectors with tiny perturbations — but Jaccard
    gamma over 20 noisy dims sums up to ~0.4 from the noise mass
    alone, putting the pair WELL ABOVE the 0.2 staleness floor and
    hiding the test condition entirely. Sparse vectors expose the
    filter.
    """
    crystals = []
    n = 100
    # 100 distinct dims so every sensor spikes a different position
    vocab = n
    for i in range(n):
        vec = [0.0] * vocab
        vec[i] = 1.0
        c = Crystal(
            id=f"sensor_{i}",
            ts="",
            text=f"sensor reading {i}",
            source="sensor",
            mi_vector=vec,
            resonance=[],
            keywords=[],
            chain_seq=i,  # all chain-adjacent
        )
        crystals.append(c)

    # Confirm pairwise gamma is genuinely below SEMANTIC_FLOOR
    rng = random.Random(42)
    sample_gammas = []
    for _ in range(50):
        i = rng.randint(0, n - 1)
        j = rng.randint(0, n - 1)
        if i == j:
            continue
        sample_gammas.append(gamma(crystals[i].mi_vector, crystals[j].mi_vector))
    avg_gamma = sum(sample_gammas) / len(sample_gammas) if sample_gammas else 0.0

    edges = run_coupling(crystals, min_gamma=0.4, window=20)
    components = find_components(crystals)
    largest = max(len(c) for c in components) if components else 0

    return {
        "n_crystals": len(crystals),
        "avg_gamma_sample": avg_gamma,
        "edges": edges,
        "largest_component": largest,
        "components_count": len(components),
    }


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def main():
    print("Running A/B comparison...")
    ab = compare_ab()

    print("Running staleness stress test...")
    stress = stress_staleness()

    out_path = Path(__file__).parent / "marriage_phase2_ab_results.md"
    with open(out_path, "w") as f:
        f.write("# Chaincode-Fish Marriage Phase 2 — A/B Results\n\n")
        f.write("Spec: data/chaincode_fish_marriage_spec.md (2026-03-25)\n\n")
        f.write("Generated by tests/marriage_phase2_ab_harness.py\n\n")

        f.write("## A/B: synthetic corpus with vs without chain_seq\n\n")
        f.write("Corpus: 10 synthetic 'sessions' × 20 crystals each = 200 crystals total.\n")
        f.write("Each session has internal vocabulary signature; cross-session pairs are\n")
        f.write("chain-distant (distance >= 20 between any two sessions).\n\n")
        diag = ab.get("_diagnostic", {})
        f.write("**Gamma distribution (sampled 2000 pairs, no chain metadata):**\n\n")
        f.write(f"  p60={diag.get('gamma_p60', 0):.3f}, "
                f"p75={diag.get('gamma_p75', 0):.3f}, "
                f"p90={diag.get('gamma_p90', 0):.3f}\n\n")
        f.write(f"  threshold used: min_gamma = {diag.get('threshold_used', 0):.3f}\n\n")
        f.write("| metric | without_chain | with_chain | delta |\n")
        f.write("|---|---:|---:|---:|\n")

        for key in ["edges", "components_total", "nontrivial_components", "largest_component"]:
            without = ab["without_chain"][key]
            with_ = ab["with_chain"][key]
            delta = with_ - without
            f.write(f"| {key} | {without} | {with_} | {delta:+d} |\n")

        f.write("\nSize distributions (top 10 component sizes):\n\n")
        f.write(f"  without_chain: {ab['without_chain']['size_distribution']}\n")
        f.write(f"  with_chain:    {ab['with_chain']['size_distribution']}\n\n")

        f.write("**Interpretation.** Phase 2 temporal rescue is *additive* — it can only\n")
        f.write("ADD edges, never remove them. So `edges with_chain >= edges without_chain`\n")
        f.write("must hold. Likewise component count can only stay the same or shrink as\n")
        f.write("rescued edges merge previously-disconnected components.\n\n")

        f.write("## Stress: staleness filter blocks sensor-data mega-coupling\n\n")
        f.write("100 synthetic sensor readings, all chain-adjacent (chain_seq 0..99),\n")
        f.write("each with a single tiny dimension spike at a different position.\n")
        f.write("Pairwise gamma is below SEMANTIC_FLOOR (0.2). Without the staleness\n")
        f.write("gate, pure chain proximity would couple every pair into one giant\n")
        f.write("formation. With the gate, the temporal term is zeroed and gamma alone\n")
        f.write("(below threshold) keeps them apart.\n\n")
        for k, v in stress.items():
            f.write(f"  {k}: {v}\n")

        f.write("\n**Pass criterion.** `largest_component` should remain near 1 (every\n")
        f.write("sensor isolated) — not anywhere near `n_crystals`. If we see 100, the\n")
        f.write("staleness filter is broken.\n\n")

        verdict_lines = []
        # Phase 2 must be additive
        if ab["with_chain"]["edges"] >= ab["without_chain"]["edges"]:
            verdict_lines.append("- A/B additivity: PASS "
                                f"({ab['with_chain']['edges']} >= "
                                f"{ab['without_chain']['edges']} edges)")
        else:
            verdict_lines.append("- A/B additivity: FAIL — Phase 2 lost edges")

        # Staleness must hold
        if stress["largest_component"] < 50:
            verdict_lines.append(f"- Staleness filter: PASS "
                                f"(largest sensor component = {stress['largest_component']}, "
                                f"well below {stress['n_crystals']})")
        else:
            verdict_lines.append(f"- Staleness filter: FAIL — sensor mega-coupling at "
                                f"size {stress['largest_component']}")

        f.write("## Verdict\n\n")
        f.write("\n".join(verdict_lines) + "\n")

    print(f"\nResults written to {out_path}")
    print("\n--- Summary ---")
    print(f"A/B edges: without={ab['without_chain']['edges']} -> "
          f"with={ab['with_chain']['edges']} "
          f"({ab['with_chain']['edges'] - ab['without_chain']['edges']:+d})")
    print(f"A/B components: without={ab['without_chain']['nontrivial_components']} -> "
          f"with={ab['with_chain']['nontrivial_components']}")
    print(f"Staleness stress: {stress['n_crystals']} sensors, "
          f"largest component = {stress['largest_component']}, "
          f"edges = {stress['edges']}")


if __name__ == "__main__":
    main()
