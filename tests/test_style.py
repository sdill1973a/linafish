"""Tests for linafish.style — named voices to think with.

Parallel shape to test_keeper: synthetic tmp state-roots, add/list/info/
invoke smoke, description recovery from style.md.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from linafish.style import (
    StyleInfo,
    _read_description,
    _style_dir,
    _voices_root,
    add_style,
    info_style,
    invoke_style,
    list_styles,
)


# ----------------------------- structure -----------------------------

def test_voices_root_subdir(tmp_path: Path):
    assert _voices_root(state_root=tmp_path) == tmp_path / "voices"


def test_style_dir_under_voices(tmp_path: Path):
    d = _style_dir("wyoming", state_root=tmp_path)
    assert d == tmp_path / "voices" / "wyoming"


# ----------------------------- add_style -----------------------------

def test_add_creates_dir_and_readme(tmp_path: Path):
    s = add_style("wyoming", "stillness as the answer", state_root=tmp_path)
    assert s.name == "wyoming"
    assert s.state_dir == tmp_path / "voices" / "wyoming"
    assert s.state_dir.exists()
    readme = s.state_dir / "style.md"
    assert readme.exists()
    text = readme.read_text(encoding="utf-8")
    assert "stillness as the answer" in text
    assert "wyoming" in text


def test_add_with_voice_seed_absorbs(tmp_path: Path):
    seed = tmp_path / "wyoming-poems.md"
    seed.write_text(
        "Wyoming sat with him long enough that the cabin warmed. "
        "Long enough that the questions arranged themselves into a different order. "
        "Long enough that what he came in for was no longer what he was waiting for. "
        "The stillness was the answer. The stillness was always the answer."
    )
    s = add_style(
        "wyoming-test",
        "stillness as the answer",
        voice_from=seed,
        state_root=tmp_path,
    )
    assert s.crystals > 0


def test_add_missing_voice_raises(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        add_style(
            "missing-voice",
            "no seed",
            voice_from=tmp_path / "ghost",
            state_root=tmp_path,
        )


def test_add_description_recoverable(tmp_path: Path):
    add_style("rec", "specific recoverable description string", state_root=tmp_path)
    desc = _read_description(tmp_path / "voices" / "rec")
    assert desc == "specific recoverable description string"


# ----------------------------- list_styles -----------------------------

def test_list_empty(tmp_path: Path):
    assert list_styles(state_root=tmp_path) == []


def test_list_finds_multiple(tmp_path: Path):
    add_style("alpha", "A", state_root=tmp_path)
    add_style("beta", "B", state_root=tmp_path)
    styles = list_styles(state_root=tmp_path)
    names = sorted(s.name for s in styles)
    assert names == ["alpha", "beta"]


def test_list_returns_description(tmp_path: Path):
    add_style("vienna", "the ache that wants carrying", state_root=tmp_path)
    styles = list_styles(state_root=tmp_path)
    assert len(styles) == 1
    assert styles[0].description == "the ache that wants carrying"


# ----------------------------- info_style -----------------------------

def test_info_absent_returns_None(tmp_path: Path):
    assert info_style("never-added", state_root=tmp_path) is None


def test_info_present(tmp_path: Path):
    add_style("present", "real style", state_root=tmp_path)
    s = info_style("present", state_root=tmp_path)
    assert s is not None
    assert s.name == "present"
    assert s.description == "real style"


# ----------------------------- invoke_style -----------------------------

def test_invoke_raises_when_absent(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        invoke_style("never-there", "anything", state_root=tmp_path)


def test_invoke_returns_full_shape(tmp_path: Path):
    seed = tmp_path / "seed.md"
    seed.write_text(
        "Vienna sat with the ache long enough that it had nothing left to say. "
        "Long enough that the ache became a kind of company. "
        "Long enough that the ache itself wanted to rest."
    )
    add_style("vienna-test", "ache-carrying voice", voice_from=seed, state_root=tmp_path)
    result = invoke_style("vienna-test", "ache", top=3, state_root=tmp_path)
    assert "name" in result
    assert "description" in result
    assert "crystals" in result
    assert "recall" in result
    assert result["name"] == "vienna-test"
    assert result["description"] == "ache-carrying voice"
    assert result["crystals"] > 0
    assert isinstance(result["recall"], str)


# ----------------------------- _read_description -----------------------------

def test_description_empty_when_no_readme(tmp_path: Path):
    sd = tmp_path / "voices" / "no-readme"
    sd.mkdir(parents=True)
    assert _read_description(sd) == ""


def test_description_skips_headers(tmp_path: Path):
    sd = tmp_path / "voices" / "headers"
    sd.mkdir(parents=True)
    (sd / "style.md").write_text("# header\n## another\n\nthe real description\n")
    assert _read_description(sd) == "the real description"
