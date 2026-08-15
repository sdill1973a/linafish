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

    def __init__(self, op_level: bool = False):
        # ng2 lock 7: when True, coin from op-level (dim:op) chains instead of
        # dim-level. Default False preserves shipped behavior; the 2.0 build
        # flips it on after the copy-fish measurement proves the delta.
        self.op_level = op_level

        # Bootstrap operations — always present
        self.canonical = dict(CANONICAL_48)

        # Evolved operations — grown from use
        self.evolved: Dict[str, EvolvedGlyph] = {}

        # Usage tracking
        self.chain_frequency: Counter = Counter()
        self.cycle_count: int = 0

        # Thresholds (from Canonical Grammar pseudocode)
        self.ache_birth_threshold: float = 0.3   # absolute FLOOR only (see gate below)
        self.merge_overlap_threshold: float = 0.8  # overlap > this → merge two glyphs
        self.prune_cycles: int = 10               # unused for this many cycles → prune
        self.min_frequency: int = 3               # chain must appear N times before birth

        # ng2 P1 gate (Olorina's #32 review, 2026-08-15: "wire both").
        # The old gate was a LOTTERY: cumulative frequency but per-cycle ache,
        # a fresh independent draw every cycle a chain reappeared, and an
        # absolute 0.3 bar on a 0-9+ ache scale that refused 0.01% of chains.
        # Now: each chain is evaluated ONCE, at maturity (min_frequency),
        # against its CUMULATIVE average ache, with a percentile bar drawn
        # from the mature population at that moment.
        #
        # SEMANTICS, stated so it is not rediscovered as a bug: the bar is
        # scale-free but NOT time-invariant — two chains maturing at
        # different times face the corpus as it stands at their maturity.
        # One draw whose difficulty depends on when it happens is strictly
        # better than N independent draws; it is not a constant bar.
        #
        # ESCAPE HATCH (hers): a refused chain may re-plead exactly once,
        # iff its cumulative average later crosses the strictly higher
        # revision bar — revision costs more than birth. Without this, a
        # chain that matures during a quiet week is never a word no matter
        # what it becomes.
        # Defaults measured on the joint corpus 2026-08-15 (posted to #32):
        # p75 refused the alphabet's mass words (CR>EW, 1,478 uses, all-three
        # attested, killed on middling AVERAGE ache) and collapsed vocab to
        # 14; p50 preserves the attested core while still refusing half the
        # mature population — a real gate. The percentile is an operator
        # dial; the default is the measured one, not a guessed one.
        self.birth_percentile: float = 50.0
        self.revision_percentile: float = 75.0
        # Cumulative ache mass per chain (sum; count lives in chain_frequency).
        self.chain_ache_sum: Counter = Counter()
        # chain_id -> bar it was refused at (evaluated-once record).
        self.refused: Dict[str, float] = {}
        # chain_ids that already used their single re-plead.
        self.repleaded: Set[str] = set()

    def _chain_of(self, crystal) -> tuple:
        """The chain this crystal coins from.

        op_level → op-level (dim:op) firing order from ``chain_ops`` (ng2 lock 7,
        48-op coinage); else the dim-level firing order. Canon-aligned in both
        cases — every token is a canonical-48 letter, so the base handshake holds.
        Falls back to the dim-level chain if op_level is on but ``chain_ops`` is
        empty for this crystal.
        """
        if self.op_level:
            ops = getattr(crystal, "chain_ops", None)
            if ops:
                return tuple(ops)
        return tuple(crystal.chain) if hasattr(crystal, 'chain') else ()

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
            # Track chain patterns (op-level when op_level is on — ng2 lock 7)
            chain = self._chain_of(crystal)
            if len(chain) >= 2:
                cycle_chains[chain] += 1
                self.chain_frequency[chain] += 1
                # Cumulative ache mass. getattr, not hasattr: 'ache' is a
                # dataclass default so hasattr is always-true dead code, and
                # a crystal shipped WITHOUT ache loads as a measured 0.0 —
                # absence-as-zero dilutes averages silently the day a
                # substrate stops carrying ache. Measured negligible today
                # (0.01%/0.07% on a 17.6K store); this line is where it
                # would go wrong, so this is where the warning lives.
                self.chain_ache_sum[chain] += getattr(crystal, 'ache', 0.0) or 0.0

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

    def _cumulative_avg(self, chain) -> float:
        """Cumulative average ache of a chain over its whole observed life."""
        n = self.chain_frequency.get(chain, 0)
        return (self.chain_ache_sum.get(chain, 0.0) / n) if n else 0.0

    def _percentile_bar(self, percentile: float) -> float:
        """The gate's bar: the given percentile of cumulative averages over
        all MATURE chains (count >= min_frequency), floored at the absolute
        ache_birth_threshold so a tiny corpus cannot set a degenerate bar.
        Computed against the population as it stands NOW — see the semantics
        note in __init__: scale-free, not time-invariant."""
        avgs = sorted(
            self._cumulative_avg(c)
            for c, n in self.chain_frequency.items() if n >= self.min_frequency
        )
        if not avgs:
            return self.ache_birth_threshold
        k = (len(avgs) - 1) * percentile / 100.0
        f = int(k)
        c = min(f + 1, len(avgs) - 1)
        bar = avgs[f] + (avgs[c] - avgs[f]) * (k - f)
        return max(bar, self.ache_birth_threshold)

    def _birth_cycle(self, crystals: list, cycle_chains: Counter) -> None:
        """Generate new glyphs — evaluated ONCE at maturity, not by lottery.

        A chain that keeps appearing with high ache is trying to become its
        own symbol. Each chain gets ONE decision, at the moment it crosses
        min_frequency, judged on its cumulative average against the mature
        population's percentile bar. A refusal is recorded and permanent —
        except for the single re-plead at the strictly higher revision bar
        (see __init__). The gate says no on purpose, not by lottery.
        """
        for chain, count in self.chain_frequency.items():
            if count < self.min_frequency:
                continue
            if len(chain) <= 1:
                continue

            chain_id = ">".join(chain)
            if chain_id in self.evolved:
                self.evolved[chain_id].usage_count += cycle_chains.get(chain, 0)
                continue

            avg = self._cumulative_avg(chain)

            if chain_id in self.refused:
                # Evaluated once already. One re-plead, at the higher bar,
                # and only once — revision costs more than birth. The plea
                # is spent only on NEW EVIDENCE: the cumulative avg must
                # first cross the bar it originally failed. Without this,
                # a daily-recurring chain burns its plea the very next
                # cycle on unchanged evidence (measured: 42/42 refused
                # chains re-pleaded immediately on the joint corpus).
                if chain_id in self.repleaded:
                    continue
                if avg <= self.refused[chain_id]:
                    continue          # no new evidence; the plea keeps
                self.repleaded.add(chain_id)
                if avg < self._percentile_bar(self.revision_percentile):
                    continue
            else:
                # Maturity: the one evaluation.
                if avg < self._percentile_bar(self.birth_percentile):
                    self.refused[chain_id] = self._percentile_bar(
                        self.birth_percentile)
                    continue

            self.refused.pop(chain_id, None)
            self.evolved[chain_id] = EvolvedGlyph(
                id=chain_id,
                category=chain[0],  # primary dimension
                source_chain=chain,
                usage_count=count,
                born_at_cycle=self.cycle_count,
                ache_at_birth=avg,
            )

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

                # Overlap over ORDERED adjacent pairs — direction is the
                # verb, and set() erased it: ("CR","EW") vs ("EW","CR") was
                # overlap 1.0 and an unconditional merge (#32 review, B).
                # Reversed chains now share no bigrams and never merge.
                a_set = set(zip(a.source_chain, a.source_chain[1:]))
                b_set = set(zip(b.source_chain, b.source_chain[1:]))
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
