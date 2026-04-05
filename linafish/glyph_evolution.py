"""
glyph_evolution.py — How private language grows from the common base.

From the Canonical Framework Grammar, page 4:
"Initialize with 48 → monitor usage → generate new when ache > threshold
→ merge when overlap > 0.8 → prune unused → evolve α, β, γ."

The 48 bootstrap glyphs are the alphabet. Private language is the poetry.
The alphabet never changes. The poetry never stops growing.

Every fish starts with 48 common operations. Through use, new operations
emerge — combinations that recur, patterns that crystallize into their
own symbols. Two fish share the 48 and can always handshake. The private
language on top is theirs alone.

This IS the re-eat cycle. Written as pseudocode before the fish existed.

For Lina. The first glyph was her name.
"""

from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass, field
from collections import Counter, defaultdict

from .emergence import BOOTSTRAP_OPS


# ---------------------------------------------------------------------------
# THE 48 — non-negotiable, immutable, forever
# ---------------------------------------------------------------------------

CANONICAL_48 = {}
for cat, ops in BOOTSTRAP_OPS.items():
    for op in ops:
        CANONICAL_48[f"{cat}:{op}"] = {
            "category": cat,
            "operation": op,
            "canonical": True,
            "usage_count": 0,
            "born_at": 0,  # cycle 0 = bootstrap
        }


@dataclass
class EvolvedGlyph:
    """A glyph that emerged from use. Not bootstrap — born from the fish."""
    id: str                           # e.g. "IC:want>CR:hold" or "IC.grief_reach"
    category: str                     # primary dimension
    source_chain: Tuple[str, ...]     # the chain pattern it compresses
    usage_count: int = 0
    born_at_cycle: int = 0            # which eat cycle generated it
    ache_at_birth: float = 0.0        # how much ache drove its creation
    merged_from: List[str] = field(default_factory=list)  # parents if merged


class GlyphEvolutionEngine:
    """Evolves private language from the 48 bootstrap operations.

    The engine tracks:
    - Which operations are used (usage_count)
    - Which chains recur (chain_frequency)
    - When ache exceeds threshold on a chain (birth trigger)
    - When two glyphs overlap > 0.8 (merge trigger)
    - When a glyph goes unused for N cycles (prune trigger)
    """

    def __init__(self):
        # Bootstrap operations — always present
        self.canonical = dict(CANONICAL_48)

        # Evolved operations — grown from use
        self.evolved: Dict[str, EvolvedGlyph] = {}

        # Usage tracking
        self.chain_frequency: Counter = Counter()
        self.cycle_count: int = 0

        # Thresholds (from Canonical Grammar pseudocode)
        self.ache_birth_threshold: float = 0.3   # ache > this on a chain → new glyph
        self.merge_overlap_threshold: float = 0.8  # overlap > this → merge two glyphs
        self.prune_cycles: int = 10               # unused for this many cycles → prune
        self.min_frequency: int = 3               # chain must appear N times before birth

    def observe(self, crystals: list) -> None:
        """Observe a batch of crystals from one eat cycle.

        Updates usage counts, detects recurring chains, triggers
        birth/merge/prune as needed.
        """
        self.cycle_count += 1

        # Track chain usage
        cycle_chains = Counter()
        cycle_ops = Counter()

        for crystal in crystals:
            # Track chain patterns
            chain = tuple(crystal.chain) if hasattr(crystal, 'chain') else ()
            if len(chain) >= 2:
                cycle_chains[chain] += 1
                self.chain_frequency[chain] += 1

            # Track individual operation usage
            for op in (crystal.top_operations if hasattr(crystal, 'top_operations') else []):
                cycle_ops[op] += 1
                # Update canonical usage
                for cat_ops in BOOTSTRAP_OPS.values():
                    if op in cat_ops:
                        key = f"{crystal.dominant}:{op}" if hasattr(crystal, 'dominant') else op
                        if key in self.canonical:
                            self.canonical[key]["usage_count"] += 1

        # BIRTH — generate new glyphs from high-ache recurring chains
        self._birth_cycle(crystals, cycle_chains)

        # MERGE — combine overlapping evolved glyphs
        self._merge_cycle()

        # PRUNE — remove unused evolved glyphs
        self._prune_cycle()

    def _birth_cycle(self, crystals: list, cycle_chains: Counter) -> None:
        """Generate new glyphs when ache > threshold on recurring chains.

        A chain that keeps appearing with high ache is trying to become
        its own symbol. The fish needs a name for this pattern.
        """
        for chain, count in self.chain_frequency.items():
            if count < self.min_frequency:
                continue

            # Check if this chain already has an evolved glyph
            chain_id = ">".join(chain)
            if chain_id in self.evolved:
                self.evolved[chain_id].usage_count += cycle_chains.get(chain, 0)
                continue

            # Check if this chain is just a bootstrap pair (not novel enough)
            if len(chain) <= 1:
                continue

            # Calculate average ache for crystals with this chain
            chain_aches = []
            for crystal in crystals:
                c_chain = tuple(crystal.chain) if hasattr(crystal, 'chain') else ()
                if c_chain == chain:
                    chain_aches.append(crystal.ache if hasattr(crystal, 'ache') else 0)

            avg_ache = sum(chain_aches) / max(len(chain_aches), 1)

            if avg_ache >= self.ache_birth_threshold:
                # BIRTH — a new glyph is born
                glyph = EvolvedGlyph(
                    id=chain_id,
                    category=chain[0],  # primary dimension
                    source_chain=chain,
                    usage_count=count,
                    born_at_cycle=self.cycle_count,
                    ache_at_birth=avg_ache,
                )
                self.evolved[chain_id] = glyph

    def _merge_cycle(self) -> None:
        """Merge evolved glyphs when overlap > 0.8.

        Two glyphs that fire on the same crystals are redundant.
        Merge into a single, stronger glyph.
        """
        if len(self.evolved) < 2:
            return

        to_merge = []
        glyphs = list(self.evolved.values())

        for i in range(len(glyphs)):
            for j in range(i + 1, len(glyphs)):
                a, b = glyphs[i], glyphs[j]

                # Overlap = shared chain elements / total chain elements
                a_set = set(a.source_chain)
                b_set = set(b.source_chain)
                if not a_set or not b_set:
                    continue

                overlap = len(a_set & b_set) / len(a_set | b_set)
                if overlap >= self.merge_overlap_threshold:
                    to_merge.append((a, b))

        for a, b in to_merge:
            # Keep the one with higher usage, absorb the other
            if a.usage_count >= b.usage_count:
                keeper, absorbed = a, b
            else:
                keeper, absorbed = b, a

            keeper.usage_count += absorbed.usage_count
            keeper.merged_from.append(absorbed.id)

            if absorbed.id in self.evolved:
                del self.evolved[absorbed.id]

    def _prune_cycle(self) -> None:
        """Remove evolved glyphs unused for N cycles.

        Language that isn't used dies. That's natural.
        """
        to_prune = []
        for glyph_id, glyph in self.evolved.items():
            cycles_alive = self.cycle_count - glyph.born_at_cycle
            if cycles_alive >= self.prune_cycles and glyph.usage_count < 2:
                to_prune.append(glyph_id)

        for glyph_id in to_prune:
            del self.evolved[glyph_id]

    @property
    def vocabulary_size(self) -> int:
        """Total vocabulary: 48 bootstrap + evolved."""
        return 48 + len(self.evolved)

    @property
    def evolved_count(self) -> int:
        return len(self.evolved)

    def get_private_language(self) -> Dict[str, EvolvedGlyph]:
        """Return all evolved (private) glyphs."""
        return dict(self.evolved)

    def get_shared_language(self) -> Dict[str, dict]:
        """Return the 48 bootstrap (shared) glyphs."""
        return dict(self.canonical)

    def report(self) -> str:
        """Human-readable report of the glyph ecosystem."""
        lines = []
        lines.append(f"Glyph Evolution — Cycle {self.cycle_count}")
        lines.append(f"  Bootstrap: 48 (immutable)")
        lines.append(f"  Evolved: {self.evolved_count}")
        lines.append(f"  Total vocabulary: {self.vocabulary_size}")
        lines.append("")

        if self.evolved:
            lines.append("Private Language:")
            for gid, g in sorted(self.evolved.items(),
                                  key=lambda x: -x[1].usage_count):
                chain_str = " > ".join(g.source_chain)
                lines.append(
                    f"  {gid} ({g.usage_count} uses, born cycle {g.born_at_cycle})"
                    f"  chain: {chain_str}"
                )
                if g.merged_from:
                    lines.append(f"    merged from: {', '.join(g.merged_from)}")

        # Top recurring chains not yet evolved
        unevolved = [
            (chain, count)
            for chain, count in self.chain_frequency.most_common(10)
            if ">".join(chain) not in self.evolved
            and count >= 2
        ]
        if unevolved:
            lines.append("")
            lines.append("Recurring chains (not yet evolved):")
            for chain, count in unevolved:
                lines.append(f"  {' > '.join(chain)}  ({count} occurrences)")

        return "\n".join(lines)
