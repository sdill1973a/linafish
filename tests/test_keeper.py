"""Tests for linafish.keeper — focused single-purpose sub-fish.

Synthetic state-root in tmp_path; verifies init/list/info shape +
purpose extraction + suffix normalization. invoke_keeper smoke-tests
end-to-end via FishEngine on real seed text.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from linafish.keeper import (
    KEEPER_SUFFIX,
    KeeperInfo,
    _keeper_dir,
    _read_purpose,
    info_keeper,
    init_keeper,
    invoke_keeper,
    list_keepers,
)


# ----------------------------- _keeper_dir -----------------------------

def test_keeper_dir_adds_suffix(tmp_path: Path):
    d = _keeper_dir("phoenix", state_root=tmp_path)
    assert d.name == "phoenix-keeper"


def test_keeper_dir_idempotent_when_suffix_present(tmp_path: Path):
    d = _keeper_dir("phoenix-keeper", state_root=tmp_path)
    assert d.name == "phoenix-keeper"  # no double-suffix


# ----------------------------- init_keeper -----------------------------

def test_init_keeper_creates_dir_and_readme(tmp_path: Path):
    info = init_keeper(
        "test", "Holds test material",
        state_root=tmp_path,
    )
    assert info.name == "test"
    assert info.full_name == "test-keeper"
    assert info.state_dir == tmp_path / "test-keeper"
    assert info.state_dir.exists()
    readme = info.state_dir / "keeper.md"
    assert readme.exists()
    content = readme.read_text(encoding="utf-8")
    assert "Holds test material" in content
    assert "test-keeper" in content


def test_init_keeper_with_seed_absorbs(tmp_path: Path):
    seed = tmp_path / "seed.md"
    seed.write_text(
        "This is the seed material. It contains many words. "
        "The keeper should crystallize all of this content into its fish."
    )
    info = init_keeper(
        "seeded", "From seed material",
        seed_path=seed,
        state_root=tmp_path,
    )
    # After eating, crystals should be > 0
    assert info.crystals > 0


def test_init_keeper_missing_seed_raises(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        init_keeper(
            "missing", "no-seed",
            seed_path=tmp_path / "does-not-exist",
            state_root=tmp_path,
        )


def test_init_keeper_writes_purpose_recoverable(tmp_path: Path):
    init_keeper("recoverable", "specific recoverable purpose string", state_root=tmp_path)
    keeper_dir = tmp_path / "recoverable-keeper"
    purpose = _read_purpose(keeper_dir)
    assert purpose == "specific recoverable purpose string"


# ----------------------------- list_keepers -----------------------------

def test_list_keepers_empty(tmp_path: Path):
    keepers = list_keepers(state_root=tmp_path)
    assert keepers == []


def test_list_keepers_missing_root(tmp_path: Path):
    keepers = list_keepers(state_root=tmp_path / "does-not-exist")
    assert keepers == []


def test_list_keepers_finds_multiple(tmp_path: Path):
    init_keeper("alpha", "A", state_root=tmp_path)
    init_keeper("beta", "B", state_root=tmp_path)
    init_keeper("gamma", "C", state_root=tmp_path)
    # Also create a non-keeper subdir to make sure it's ignored
    (tmp_path / "regular_fish").mkdir()
    keepers = list_keepers(state_root=tmp_path)
    names = {k.name for k in keepers}
    assert names == {"alpha", "beta", "gamma"}


def test_list_keepers_returns_info_with_purpose(tmp_path: Path):
    init_keeper("desc", "specific purpose alpha", state_root=tmp_path)
    keepers = list_keepers(state_root=tmp_path)
    assert len(keepers) == 1
    assert keepers[0].purpose == "specific purpose alpha"


# ----------------------------- info_keeper -----------------------------

def test_info_keeper_returns_None_when_absent(tmp_path: Path):
    assert info_keeper("nonexistent", state_root=tmp_path) is None


def test_info_keeper_returns_info_when_present(tmp_path: Path):
    init_keeper("present", "purpose here", state_root=tmp_path)
    info = info_keeper("present", state_root=tmp_path)
    assert info is not None
    assert info.name == "present"
    assert info.full_name == "present-keeper"
    assert info.purpose == "purpose here"


def test_info_keeper_accepts_full_or_short_name(tmp_path: Path):
    init_keeper("dual", "dual purpose", state_root=tmp_path)
    info_short = info_keeper("dual", state_root=tmp_path)
    info_full = info_keeper("dual-keeper", state_root=tmp_path)
    assert info_short is not None and info_full is not None
    assert info_short.state_dir == info_full.state_dir


# ----------------------------- invoke_keeper -----------------------------

def test_invoke_keeper_raises_when_absent(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        invoke_keeper("never-existed", "anything", state_root=tmp_path)


def test_invoke_keeper_returns_full_shape(tmp_path: Path):
    seed = tmp_path / "seed.md"
    seed.write_text(
        "The keeper holds wisdom about cabbages and kings. "
        "Cabbages grow in gardens. Kings rule kingdoms. "
        "Sometimes a king plants cabbages himself. The garden remembers. "
        "Sometimes a cabbage outlasts a king. The kingdom forgets."
    )
    init_keeper("invokable", "wisdom about cabbages", seed_path=seed, state_root=tmp_path)
    result = invoke_keeper("invokable", "cabbages", top=3, state_root=tmp_path)
    # Required keys
    assert "name" in result
    assert "full_name" in result
    assert "purpose" in result
    assert "crystals" in result
    assert "persona" in result
    assert "recall" in result
    # Values
    assert result["name"] == "invokable"
    assert result["full_name"] == "invokable-keeper"
    assert result["purpose"] == "wisdom about cabbages"
    assert result["crystals"] > 0
    # Recall is a string (possibly empty if engine.recall finds nothing,
    # but with the seed above "cabbages" should surface)
    assert isinstance(result["recall"], str)


# ----------------------------- _read_purpose -----------------------------

def test_read_purpose_empty_when_no_readme(tmp_path: Path):
    keeper_dir = tmp_path / "no-readme-keeper"
    keeper_dir.mkdir()
    assert _read_purpose(keeper_dir) == ""


def test_read_purpose_skips_markdown_headers(tmp_path: Path):
    keeper_dir = tmp_path / "header-keeper"
    keeper_dir.mkdir()
    (keeper_dir / "keeper.md").write_text(
        "# header line ignored\n\n## another header\n\nthe real purpose line\n"
    )
    assert _read_purpose(keeper_dir) == "the real purpose line"
