"""The sketchpad's guarantees — LiNafish 2.0, Part II.

These lock the three things that make a sketchpad a memory rather than a photo
album: the binding is authored and never overwritten by accident, the store is
an ordinary fish so the heart can read it, and the flash is the MEANING rather
than the filename.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

from linafish import vizmem


def _fake_listen(state_dir: Path, name: str):
    """Stand in for `linafish listen stdin`, which would cold-load an engine."""
    def run(cmd, input=None, capture_output=None, text=None, timeout=None):
        p = state_dir / f"{name}_crystals.jsonl"
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"text": input}) + "\n")
        return subprocess.CompletedProcess(cmd, 0, "", "")
    return run


@pytest.fixture
def fish(tmp_path, monkeypatch):
    img = tmp_path / "photo.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 32)
    monkeypatch.setattr(subprocess, "run", _fake_listen(tmp_path, "vizmem"))
    return tmp_path, img


def test_binding_is_stored_and_readable(fish):
    state_dir, img = fish
    r = vizmem.bind(img, "what this means to me", state_dir)
    assert r["n"] == 1 and r["after"] == 1
    rows = vizmem.bindings(state_dir)
    assert rows == [(1, str(img.resolve()), "what this means to me")]


def test_the_meaning_leads_so_the_flash_is_not_a_filename(fish):
    """The pixels are the cold half. A recall window that lands on the path
    surfaces the one thing that is never the memory."""
    state_dir, img = fish
    vizmem.bind(img, "the meaning", state_dir)
    text = json.loads((state_dir / "vizmem_crystals.jsonl").read_text().splitlines()[0])["text"]
    assert text.startswith("the meaning"), "binding must lead the crystal text"
    assert text.rstrip().endswith(")"), "path must trail as a reference"


def test_rebinding_is_refused_by_default(fish):
    """Identity fixed, heat lives: a meaning-signature does not deform with use."""
    state_dir, img = fish
    vizmem.bind(img, "first meaning", state_dir)
    with pytest.raises(ValueError, match="already bound"):
        vizmem.bind(img, "second meaning", state_dir)
    assert vizmem.bind(img, "second meaning", state_dir, rebind=True)["n"] == 2


def test_empty_binding_is_refused(fish):
    """A caption-free tool with an empty binding would store a pointer to
    nothing — the exact failure it exists to prevent."""
    state_dir, img = fish
    for bad in ("", "   ", "\n"):
        with pytest.raises(ValueError, match="cannot be empty"):
            vizmem.bind(img, bad, state_dir)


def test_refuses_to_report_success_when_the_store_did_not_grow(tmp_path, monkeypatch):
    """A zero from an unattached instrument is not a measurement."""
    img = tmp_path / "photo.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n")

    def silent_noop(cmd, input=None, capture_output=None, text=None, timeout=None):
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(subprocess, "run", silent_noop)
    with pytest.raises(RuntimeError, match="did not grow"):
        vizmem.bind(img, "a meaning that never lands", tmp_path)


def test_missing_image_is_refused(tmp_path):
    with pytest.raises(ValueError, match="no such image"):
        vizmem.bind(tmp_path / "nope.png", "meaning", tmp_path)


def test_sketch_log_is_the_sketchpads_own(tmp_path):
    """THE WALL: the sketchpad writes its log; the heart only reads. If these
    ever share a file, an ambient read starts deforming what it reads."""
    vizmem.log_sketch(tmp_path, formation="A+B_via_C", image="x.png")
    assert vizmem.last_sketch(tmp_path) == "A+B_via_C"
    assert (tmp_path / vizmem.BEAT_LOG).exists()
    assert vizmem.BEAT_LOG != "vizmem_crystals.jsonl"


def test_bindings_ignores_ordinary_crystals(tmp_path):
    """The store is a NORMAL fish — non-image crystals may share it and must
    not be parsed as bindings."""
    p = tmp_path / "vizmem_crystals.jsonl"
    p.write_text(
        json.dumps({"text": "just an ordinary thought"}) + "\n"
        + json.dumps({"text": "a real meaning\n(image#7 /tmp/a.png)"}) + "\n",
        encoding="utf-8")
    assert vizmem.bindings(tmp_path) == [(7, "/tmp/a.png", "a real meaning")]
