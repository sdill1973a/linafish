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


# --- Minting: growing the alphabet mid-thought -------------------------------
#
# The 8-dim base alphabet is fixed and small. The VISUAL alphabet is neither:
# when a meaning arrives with no letter for it, one can be struck — rendered,
# bound, and the alphabet is one larger mid-thought. That is only true on a lane
# cheap enough to use without thinking about it, which is why the renderer is
# host policy and there is no default endpoint here.
#
# Each cognitive dimension carries a composition rule, so a minted glyph for
# SELF-REFLECTION rhymes with other SELF-REFLECTION glyphs and the alphabet
# stays readable as it grows.
VISUAL_GRAMMAR = {
    "ACTING":          "horizontal motion, forward vectors, arrow-shapes",
    "SELF-REFLECTION": "recursive spiral, mirror-pair, Mobius topology",
    "RELATING":        "connecting threads, network nodes, dyadic linkage",
    "STRUCTURING":     "gridded geometry, architectural form, mandala",
    "TESTING":         "dissolves, gradients, transition-states, fire and water",
    "FEELING":         "centered emanation, a single candle-flame focal point",
    "SPECIALIZING":    "branching fork-paths, decision-tree limbs",
    "UNDERSTANDING":   "mapped terrain, cartographic contours, charted landscape",
}
SIGIL_STYLE = ("abstract symbol, sigil, color field, geometric, "
               "no photographic, no figurative, archetypal, alchemical")
SIGIL_NEGATIVE = ("realistic, photograph, person, face, body, scene, landscape, "
                  "text, letters, watermark, signature")


def sigil_prompt(dims: list[str]) -> str:
    """Compose a render prompt from cognitive dimensions."""
    rules = [VISUAL_GRAMMAR[d] for d in dims if d in VISUAL_GRAMMAR]
    body = "; ".join(rules) if rules else "a single centered mark"
    return f"a single symbolic sigil — {body}. {SIGIL_STYLE}"


def parse_formation(name: str) -> list[str]:
    """`STRUCTURING+RELATING_via_ACTING` -> its dimension names."""
    head, _, mod = name.partition("_via_")
    dims = [d for d in head.split("+") if d]
    if mod:
        dims.append(mod)
    return [d.strip().upper() for d in dims]


class RenderUnreachable(RuntimeError):
    """The image lane could not be reached — and it says WHICH lane.

    ``sketch`` talks to two different servers: the fish it reads state from
    (``--url``) and the renderer it draws on (``--render-url``). A single
    except-block that blames one of them for both failures sends the reader
    to debug a service that is running fine. This exception carries the URL
    that actually refused, so the message can name the right organ.
    """

    def __init__(self, url: str, reason):
        super().__init__(f"{url} ({reason})")
        self.url = url
        self.reason = reason


def render_sigil(prompt: str, seed: int, render_url: str, out_dir: Path,
                 timeout: int = 600) -> Optional[Path]:
    """Render one glyph on a ComfyUI-compatible lane. Returns the saved PNG.

    Host policy, deliberately: no default endpoint, no API key, no network call
    unless you pass one in. A mind with no renderer keeps a sketchpad by binding
    images it already has.
    """
    import urllib.error
    import urllib.parse
    import urllib.request
    import time
    import uuid

    graph = {
        "4": {"class_type": "CheckpointLoaderSimple",
              "inputs": {"ckpt_name": "juggernautXL_v8Rundiffusion.safetensors"}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["4", 1]}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"text": SIGIL_NEGATIVE, "clip": ["4", 1]}},
        # batch_size 1 on purpose: a shared GPU pool has neighbours.
        "5": {"class_type": "EmptyLatentImage",
              "inputs": {"width": 768, "height": 768, "batch_size": 1}},
        "3": {"class_type": "KSampler", "inputs": {
            "seed": seed, "steps": 28, "cfg": 7.0, "sampler_name": "dpmpp_2m",
            "scheduler": "karras", "denoise": 1.0, "model": ["4", 0],
            "positive": ["6", 0], "negative": ["7", 0], "latent_image": ["5", 0]}},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
        "9": {"class_type": "SaveImage",
              "inputs": {"filename_prefix": "vizmem_glyph", "images": ["8", 0]}},
    }
    base = render_url.rstrip("/")
    req = urllib.request.Request(base + "/prompt",
                                 data=json.dumps({"prompt": graph}).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        pid = json.load(urllib.request.urlopen(req, timeout=60))["prompt_id"]
    except (urllib.error.URLError, ConnectionError, TimeoutError, OSError) as e:
        # Name the renderer, not whatever URL the caller happened to pass first.
        raise RenderUnreachable(base, getattr(e, "reason", e)) from e
    deadline = time.time() + timeout
    while time.time() < deadline:
        time.sleep(2)
        h = json.load(urllib.request.urlopen(base + f"/history/{pid}", timeout=60))
        if pid not in h:
            continue
        imgs = h[pid].get("outputs", {}).get("9", {}).get("images", [])
        if imgs:
            im = imgs[0]
            q = (f"/view?filename={urllib.parse.quote(im['filename'])}"
                 f"&subfolder={urllib.parse.quote(im.get('subfolder',''))}"
                 f"&type={im.get('type','output')}")
            png = urllib.request.urlopen(base + q, timeout=120).read()
            out_dir = Path(out_dir)
            out_dir.mkdir(parents=True, exist_ok=True)
            out = out_dir / f"glyph_{seed}_{uuid.uuid4().hex[:6]}.png"
            out.write_bytes(png)
            return out
        if h[pid].get("status", {}).get("status_str") == "error":
            return None
    return None


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
