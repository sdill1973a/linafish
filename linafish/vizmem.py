"""vizmem — the visuospatial sketchpad. LiNafish 2.0, Part II.

`heart` (Part I) gives a fish an afferent voice: words surface unbidden each
turn. Baddeley's working-memory model puts a central executive over TWO slave
systems — the phonological loop and the visuospatial sketchpad. **Part I alone
is half a working memory.** This is the other half.

Three verbs, in the order they matter:

  bind    an image gets a MEANING, authored by the mind that holds it
  mint    a meaning with no letter yet gets one struck for it, mid-thought
  sketch  the mind draws its current state, and the drawing fires back

THE BINDING IS THE MEMORY
    An image's public surface (what anyone can see) and its private meaning
    (what this mind chose to bind) are different things, and the binding is the
    memory. A vision model's caption is a COLD read — the same read any stranger
    gets. Useful for triage, never a memory.

    So nothing here generates a binding, and nothing here shows a caption before
    one is authored. That is not a style preference. A binding authored after
    reading a caption anchors the mind to the cold read, which both shallows the
    alphabet and contaminates any warm-vs-cold measurement taken over it later.
    The caption is a librarian, never a prompt.

THE STORE IS DELIBERATELY BORING
    An image memory is an ORDINARY CRYSTAL in an ORDINARY FISH: the authored
    binding as text, with the image path as a trailing reference. The engine
    derives its signature like any other crystal. No parallel database, no new
    storage engine. The alphabet is data; the organs are verbs. Which means the
    sketchpad rides `recall`, `taste` and the heart for free — put the vizmem
    fish in your `heart.toml` family and bound images fire alongside words.

THE WALL
    The sketchpad WRITES — its beat log, and bindings into its fish. The heart
    only ever READS. An ambient organ that heats what it looks at corrupts the
    signal it reads (2.0 invariant 1). Two organs, one wall.

RENDERING IS OPTIONAL AND YOURS
    `bind` needs no renderer at all. `mint` and `sketch` need one, and the
    renderer is host policy: point `--render-url` at a local image server. There
    is no default endpoint and no API key anywhere in this module — a mind that
    cannot render can still keep a sketchpad by binding images it already has.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Optional

CRYSTAL_SUFFIX = "_crystals.jsonl"
BEAT_LOG = "sketchpad_beats.jsonl"


def _crystal_path(state_dir: Path, name: str) -> Path:
    return Path(state_dir) / f"{name}{CRYSTAL_SUFFIX}"


def _crystals(state_dir: Path, name: str) -> list[dict]:
    p = _crystal_path(state_dir, name)
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def bindings(state_dir: Path, name: str = "vizmem") -> list[tuple[int, str, str]]:
    """Existing bindings as [(n, image_path, binding)], parsed from crystal text."""
    found = []
    for c in _crystals(state_dir, name):
        text = c.get("text") or ""
        binding, _, tail = text.rpartition("\n")
        tail = tail.strip()
        if not (tail.startswith("(image#") and tail.endswith(")")):
            continue
        try:
            n_str, _, path = tail[len("(image#"):-1].partition(" ")
            found.append((int(n_str), path.strip(), binding.strip()))
        except ValueError:
            continue
    return sorted(found)


def bind(image: Path, binding: str, state_dir: Path, name: str = "vizmem",
         rebind: bool = False, linafish_bin: str = "linafish") -> dict:
    """Author a binding for an image. The binding IS the memory.

    Returns {"n": int, "image": str, "binding": str, "before": int, "after": int}.
    Raises ValueError on an empty binding, an already-bound image, or — and this
    one matters — a store that did not actually grow.
    """
    image = Path(image).expanduser().resolve()
    if not image.exists():
        raise ValueError(f"no such image: {image}")
    binding = (binding or "").strip()
    if not binding:
        raise ValueError("a binding cannot be empty — the binding IS the memory")

    existing = bindings(state_dir, name)
    for n, path, old in existing:
        if path == str(image) and not rebind:
            raise ValueError(
                f"image#{n} is already bound: {old!r}\n"
                "Identity is fixed and heat lives — a meaning-signature does not "
                "deform with use. Pass rebind=True to overwrite it deliberately."
            )

    n = max((b[0] for b in existing), default=0) + 1
    # Binding FIRST, path as a trailing reference: recall windows land on the
    # meaning rather than the filename. With the path leading, the sketchpad
    # flashes `...slot200.png` — the cold half, the one thing that is never the
    # memory. Measured, not assumed.
    text = f"{binding}\n(image#{n} {image})"

    state_dir = Path(state_dir)
    state_dir.mkdir(parents=True, exist_ok=True)
    before = len(_crystals(state_dir, name))
    proc = subprocess.run(
        [linafish_bin, "listen", "stdin", "-n", name, "--state-dir", str(state_dir)],
        input=text, capture_output=True, text=True, timeout=600,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"listen failed ({proc.returncode}): {proc.stderr[-500:]}")

    after = len(_crystals(state_dir, name))
    if after <= before:
        # A zero from an unattached instrument is not a measurement. Refuse to
        # report success on a store that did not grow.
        raise RuntimeError(
            f"store did not grow ({before} -> {after}) at "
            f"{_crystal_path(state_dir, name)} — the binding was NOT saved"
        )
    return {"n": n, "image": str(image), "binding": binding,
            "before": before, "after": after}


def sketch_state(health_url: str, timeout: int = 90) -> tuple[Optional[str], Optional[str]]:
    """Current cognitive state = the fish's top formation."""
    import urllib.request
    with urllib.request.urlopen(health_url.rstrip("/") + "/health", timeout=timeout) as r:
        h = json.load(r)
    tops = h.get("top_formations") or []
    return (tops[0] if tops else None), h.get("name")


def last_sketch(state_dir: Path) -> Optional[str]:
    p = Path(state_dir) / BEAT_LOG
    if not p.exists():
        return None
    lines = [l for l in p.read_text(encoding="utf-8", errors="replace").splitlines() if l.strip()]
    if not lines:
        return None
    try:
        return json.loads(lines[-1]).get("formation")
    except json.JSONDecodeError:
        return None


def log_sketch(state_dir: Path, **fields) -> None:
    """The SKETCHPAD writes its own log. The heart never writes to what it reads."""
    p = Path(state_dir) / BEAT_LOG
    p.parent.mkdir(parents=True, exist_ok=True)
    try:
        with p.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(fields) + "\n")
    except OSError:
        pass  # a sketchpad that cannot log still draws
