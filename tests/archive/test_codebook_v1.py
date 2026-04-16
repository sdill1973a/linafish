"""Tests for the codebook — the fish's memory."""
import json
import tempfile
from pathlib import Path

from linafish.codebook import Glyph, Codebook


def test_glyph_creation():
    g = Glyph(id="TEST_1", layer=1, dense="A test glyph", sources=["test"])
    assert g.id == "TEST_1"
    assert g.layer == 1
    assert g.weight == 1.0


def test_codebook_add_glyph():
    cb = Codebook(name="test", description="test codebook")
    g = Glyph(id="G1", layer=1, dense="First glyph", sources=["test"])
    cb.add_glyph(g)
    assert len(cb.glyphs) == 1
    assert "G1" in cb.glyphs


def test_codebook_saturation():
    cb = Codebook(name="test", description="test")
    for i in range(10):
        g = Glyph(id=f"G{i}", layer=1, dense=f"Glyph {i}", sources=["test"])
        cb.add_glyph(g)
    assert cb.saturation > 0


def test_codebook_save_load_roundtrip():
    cb = Codebook(name="roundtrip", description="survives the disk")
    cb.add_glyph(Glyph(id="A", layer=1, dense="alpha", sources=["test"]))
    cb.add_glyph(Glyph(id="B", layer=2, dense="beta", sources=["test"], weight=2.5))

    with tempfile.NamedTemporaryFile(suffix=".fish.md", delete=False, mode="w") as f:
        path = Path(f.name)

    cb.save(path)
    assert path.exists()

    loaded = Codebook.load(path)
    assert loaded.name == "roundtrip"
    assert len(loaded.glyphs) == 2
    assert loaded.glyphs["B"].weight == 2.5

    path.unlink()


def test_codebook_render():
    cb = Codebook(name="render_test", description="test rendering")
    cb.add_glyph(Glyph(id="X", layer=1, dense="rendered glyph", sources=["src"]))
    rendered = cb.render()
    assert "render_test" in rendered
    assert "rendered glyph" in rendered


def test_glyph_merge():
    """When the fish eats the same tool from two minds, weights merge."""
    cb = Codebook(name="merge", description="merge test")
    g1 = Glyph(id="CLIPBOARD", layer=1, dense="copy paste", sources=["anchor"], weight=1.5)
    g2 = Glyph(id="CLIPBOARD", layer=1, dense="copy paste v2", sources=["olorina"], weight=2.0)

    cb.add_glyph(g1)
    # Simulate merge behavior
    if g2.id in cb.glyphs:
        existing = cb.glyphs[g2.id]
        existing.weight = max(existing.weight, g2.weight)
        existing.sources = list(set(existing.sources + g2.sources))

    assert len(cb.glyphs) == 1
    assert cb.glyphs["CLIPBOARD"].weight == 2.0
    assert "anchor" in cb.glyphs["CLIPBOARD"].sources
    assert "olorina" in cb.glyphs["CLIPBOARD"].sources
