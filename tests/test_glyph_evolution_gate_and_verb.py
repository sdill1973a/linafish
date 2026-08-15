"""ng2 P1 wiring tests — Olorina's #32 review (c5300564413): "wire both."

A: the birth gate was a lottery — cumulative frequency but per-cycle ache,
   with a fresh independent draw every cycle a chain reappeared. Now each
   chain is evaluated ONCE at maturity against its CUMULATIVE average, with
   a percentile bar computed from the mature population, and a single
   escape hatch: a refused chain may re-plead once iff its cumulative avg
   later crosses a strictly higher bar (revision costs more than birth).

B: the merge was direction-blind — set() erased the verb. (\"CR\",\"EW\") and
   (\"EW\",\"CR\") merged unconditionally at overlap 1.0. Now overlap is over
   ORDERED adjacent pairs, so reversed chains share nothing.

Both tests in TestOldDefects fail on the pre-wiring engine (verified before
the fix landed — the observed-failure discipline)."""

from dataclasses import dataclass, field
from typing import List

from linafish.glyph_evolution import GlyphEvolutionEngine


@dataclass
class _C:
    chain: tuple
    ache: float = 0.0
    top_operations: List[str] = field(default_factory=list)


def _feed(engine, chains_with_ache):
    engine.observe([_C(chain=c, ache=a) for c, a in chains_with_ache])


class TestDirectionIsTheVerb:
    def test_reversed_chains_do_not_merge(self):
        e = GlyphEvolutionEngine()
        # Birth both directions: high ache, past min_frequency.
        batch = [(("CR", "EW"), 9.0)] * 3 + [(("EW", "CR"), 9.0)] * 3
        _feed(e, batch)
        assert "CR>EW" in e.evolved and "EW>CR" in e.evolved
        # Ten more cycles of merge opportunity.
        for _ in range(10):
            _feed(e, batch)
        assert "CR>EW" in e.evolved and "EW>CR" in e.evolved, \
            "direction is the verb — reversed chains are different words"

    def test_subset_chains_still_do_not_merge_below_bar(self):
        e = GlyphEvolutionEngine()
        batch = [(("CR", "EW", "KO"), 9.0)] * 3 + [(("CR", "EW"), 9.0)] * 3
        _feed(e, batch)
        # ordered-bigram overlap {CR>EW, EW>KO} vs {CR>EW} = 1/2 < 0.8
        assert len(e.evolved) == 2


class TestGateIsNotALottery:
    def test_refusal_is_decided_once_not_redrawn(self):
        e = GlyphEvolutionEngine()
        # Population rich enough for a percentile bar: nine hot chains...
        hot = [((f"D{i}", f"E{i}"), 8.0 + i * 0.1) for i in range(9)]
        _feed(e, [(c, a) for c, a in hot for _ in range(3)])
        # ...and one cold chain that matures cold.
        _feed(e, [(("IC", "EW"), 0.5)] * 3)
        assert "IC>EW" in e.refused and "IC>EW" not in e.evolved
        # Old engine: next cycle's fresh draw with hot ache births it.
        # New engine: no fresh draw; cumulative avg stays below the
        # revision bar (p90 of a hot population), so refusal holds.
        _feed(e, [(("IC", "EW"), 8.0)] * 2)
        assert "IC>EW" not in e.evolved, \
            "a refused chain does not get a fresh independent draw per cycle"

    def test_escape_hatch_replead_once_at_higher_bar(self):
        e = GlyphEvolutionEngine()
        # Small mature population so bars are computable and modest.
        _feed(e, [(("D1", "E1"), 5.0)] * 3 + [(("D2", "E2"), 6.0)] * 3)
        _feed(e, [(("IC", "EW"), 0.1)] * 3)          # matures cold -> refused
        assert "IC>EW" in e.refused
        # Cumulative avg climbs decisively past every bar.
        _feed(e, [(("IC", "EW"), 9.5)] * 30)
        assert "IC>EW" in e.evolved, "one re-plead at the higher bar is allowed"
        assert e.evolved["IC>EW"].usage_count >= 3

    def test_gate_can_refuse_and_pass_on_same_corpus(self):
        e = GlyphEvolutionEngine()
        hot = [((f"H{i}", f"K{i}"), 9.0) for i in range(6)]
        cold = [((f"C{i}", f"L{i}"), 0.2) for i in range(6)]
        _feed(e, [(c, a) for c, a in hot + cold for _ in range(3)])
        born = sum(1 for c, _ in hot if f"{c[0]}>{c[1]}" in e.evolved)
        refused = sum(1 for c, _ in cold if f"{c[0]}>{c[1]}" in e.refused)
        assert born >= 4 and refused >= 4, (born, refused)
