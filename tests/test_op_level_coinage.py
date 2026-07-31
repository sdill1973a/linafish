"""ng2 lock 7 — op-level (48-op) coinage.

Locks the behavior added on build/native-glyph-2.0: GlyphEvolutionEngine can coin
from op-level (dim:op) chains, not just dimension-bigrams, behind an op_level toggle
(default OFF so shipped behavior is unchanged). Also asserts the metabolic layer
populates chain_ops from the parser's op_chains.

There was NO test exercising glyph_evolution.observe() before this — part of why the
coinage drifted unverified for eight cycles. This is the lock.
"""
from linafish.glyph_evolution import GlyphEvolutionEngine
from linafish.metabolism import MetabolicEngine
from linafish.moment import Moment


class _StubCrystal:
    """Minimal shape observe() reads: chain / chain_ops / ache / dominant / top_operations."""

    def __init__(self, chain, chain_ops, ache=1.0, dominant="IC", top_operations=()):
        self.chain = list(chain)
        self.chain_ops = list(chain_ops)
        self.ache = ache
        self.dominant = dominant
        self.top_operations = list(top_operations)


def _crystals(n, chain, chain_ops):
    return [_StubCrystal(chain, chain_ops) for _ in range(n)]


def test_default_is_dim_level_unchanged():
    """Default op_level=False coins from .chain (dim-level) — shipped behavior."""
    eng = GlyphEvolutionEngine()
    assert eng.op_level is False
    eng.observe(_crystals(3, ["IC", "EW"], ["IC:want", "EW:build"]))
    private = eng.get_private_language()
    assert "IC>EW" in private          # coined the dim-level bigram
    assert "IC:want>EW:build" not in private
    assert all(":" not in gid for gid in private)  # no op-level ids leaked in


def test_op_level_coins_dimop_chains():
    """op_level=True coins from .chain_ops — genuine dim:op glyphs."""
    eng = GlyphEvolutionEngine(op_level=True)
    assert eng.op_level is True
    eng.observe(_crystals(3, ["IC", "EW"], ["IC:want", "EW:build"]))
    private = eng.get_private_language()
    assert "IC:want>EW:build" in private   # coined at 48-op granularity
    assert "IC>EW" not in private
    assert ":" in "IC:want>EW:build"
    # every token is canon-aligned (carries a dimension prefix) -> base handshake holds
    born = private["IC:want>EW:build"]
    assert all(":" in tok for tok in born.source_chain)


def test_op_level_falls_back_to_dim_when_chain_ops_empty():
    """op_level=True but no chain_ops for a crystal -> falls back to dim chain.

    Guards mixed corpora where the parser found a dimension but no specific op.
    """
    eng = GlyphEvolutionEngine(op_level=True)
    eng.observe(_crystals(3, ["KO", "CR"], []))   # empty chain_ops
    private = eng.get_private_language()
    assert "KO>CR" in private   # fell back to dim-level rather than coining nothing


def test_below_threshold_does_not_coin():
    """min_frequency must be cleared — 2 occurrences should not birth a glyph."""
    eng = GlyphEvolutionEngine(op_level=True)
    eng.observe(_crystals(2, ["IC", "EW"], ["IC:want", "EW:build"]))  # only 2 < min_frequency(3)
    assert eng.get_private_language() == {}


def test_metabolic_layer_populates_chain_ops():
    """Integration: digest() fills chain_ops from parse.op_chains, genuinely op-level."""
    me = MetabolicEngine()
    mc = me.digest(Moment(
        text="I want to build this because the grief needs structure and a plan",
        source="test",
    ))
    assert mc.chain_ops, "chain_ops should be populated from parse.op_chains"
    assert any(":" in tok for tok in mc.chain_ops), "should carry genuine dim:op tokens"
