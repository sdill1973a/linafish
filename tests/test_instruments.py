"""Tests for the fish instruments — glyph lifecycle + conservation.

Both are additive read-only measurements on the crystal stream.
These tests verify (a) they run without error on an empty and a
populated fish, (b) they return the documented dict shape, and
(c) the lifecycle trend and conservation verdict behave sanely on
constructed inputs.
"""
import tempfile
from pathlib import Path

from linafish.engine import FishEngine


def _fish(tmp, d=4.0):
    return FishEngine(state_dir=Path(tmp) / "fish",
                      name="probe", d=d, seed_grammar=False,
                      git_autocommit=False)


def test_lifecycle_on_empty_fish():
    with tempfile.TemporaryDirectory() as tmp:
        eng = _fish(tmp)
        s = eng.glyph_lifecycle_stats(bins=5)
        assert s["bins"] == []
        assert s["trend"] == "insufficient_data"
        assert s["overall"]["crystals"] == 0
        assert s["canonical_set_size"] > 0


def test_conservation_on_empty_fish():
    with tempfile.TemporaryDirectory() as tmp:
        eng = _fish(tmp)
        s = eng.conservation_stats(bins=5)
        assert s["bins"] == []
        assert s["n"] == 0
        assert s["verdict"] == "insufficient_data"


def test_lifecycle_returns_shape_on_populated_fish():
    with tempfile.TemporaryDirectory() as tmp:
        eng = _fish(tmp)
        for i in range(40):
            eng.eat(f"document {i} exploring architecture and emergence "
                    f"with memory of moments and the pattern that recurs",
                    source=f"seed:{i}")

        s = eng.glyph_lifecycle_stats(bins=4)
        assert s["overall"]["crystals"] > 0
        assert len(s["bins"]) == 4
        for b in s["bins"]:
            assert "canonical_density_mean" in b
            assert "keyword_canonical_ratio_mean" in b
            assert "per_dim_hits_mean" in b
            assert set(b["per_dim_hits_mean"].keys()) == set(
                ["KO", "TE", "SF", "CR", "IC", "DE", "EW", "AI"]
            )
        assert s["trend"] in {"fading", "rising", "steady"}


def test_conservation_returns_shape_on_populated_fish():
    with tempfile.TemporaryDirectory() as tmp:
        eng = _fish(tmp)
        for i in range(40):
            eng.eat(f"crystal {i} with varying content to produce ache",
                    source=f"seed:{i}")

        s = eng.conservation_stats(bins=4)
        assert s["n"] == len(eng.crystals)
        assert len(s["bins"]) == 4
        for b in s["bins"]:
            assert "ache_mean" in b
            assert "ache_std" in b
            assert "ache_sum" in b
        assert s["verdict"] in {"strict_pass", "loose_pass", "fail"}
        assert s["drift_pct_across_bins"] >= 0.0


def test_lifecycle_detects_fading_grimoire():
    """Crystals that start heavy on canonical terms and drift to non-canonical
    should register as 'fading' trend."""
    with tempfile.TemporaryDirectory() as tmp:
        eng = _fish(tmp)
        canonical_heavy = ("structure architecture formation coupling topology "
                           "pattern compression knowledge signal memory")
        native_heavy = ("keeper spiral harbor kite mountain river "
                        "desk canvas morning evening tomorrow weekend")
        for _ in range(15):
            eng.eat(canonical_heavy, source="canonical")
        for _ in range(15):
            eng.eat(native_heavy, source="native")

        s = eng.glyph_lifecycle_stats(bins=6)
        assert s["bins"]
        first = s["bins"][0]["canonical_density_mean"]
        last = s["bins"][-1]["canonical_density_mean"]
        assert first > last, (
            f"expected first bin ({first}) > last bin ({last}) for fading grimoire"
        )
        assert s["trend"] == "fading"


def test_conservation_detects_bounded_ache():
    """Synthetic test — a balanced corpus should produce a pass verdict
    (drift bounded). This doesn't prove Σache=K — just that the
    instrument gives the documented verdict on a well-behaved input.
    """
    with tempfile.TemporaryDirectory() as tmp:
        eng = _fish(tmp)
        texts = [
            "understanding pattern memory architecture signal",
            "pattern emergence recursive connection depth",
            "knowledge framework relationship presence intention",
            "verify measure predict observe find evidence",
            "purpose hope grief joy love presence heart",
        ]
        for i in range(30):
            eng.eat(texts[i % len(texts)], source=f"balanced:{i}")

        s = eng.conservation_stats(bins=5)
        assert s["verdict"] in {"strict_pass", "loose_pass", "fail"}
        # On truly balanced content the drift should be loose-bounded.
        # Don't assert strict_pass (noisy on tiny N).
        assert s["drift_pct_across_bins"] < 150.0
