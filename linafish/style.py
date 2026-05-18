"""Style — named voices to think with.

A *style* is a named voice corpus you invoke when you want to think
about something IN that voice. Where a `keeper` (see linafish.keeper)
preserves what a person/project/place HOLDS, a style preserves HOW
something sounds — its cadence, vocabulary, attentional shape — by
crystallizing seed material that exemplifies the voice.

Use case: name a style after an author (your-own-voice / annie-dillard
/ dfw), feed it a corpus of writing in that voice, and then invoke
``linafish style <name> "<theme>"`` to surface the parts of that
voice's material that resonate with the theme. The output is the
voice's existing material relevant to your theme — useful when
drafting in that voice, or when comparing how different voices would
approach the same theme.

Origin: ported from `scripts/fed.py` (anchor's vienna/wyoming/stillness
"keepers as voices to think with"). The linafish generalization decouples
the pattern from anchor-specific keeper names and lets any user define
their own voices via `style add`.

Styles live at ``~/.linafish/voices/<name>/``. The voices/ prefix
distinguishes them from keepers (~/.linafish/<name>-keeper/) and from
general fish (~/.linafish/<name>/).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


VOICES_SUBDIR = "voices"


@dataclass
class StyleInfo:
    name: str
    state_dir: Path
    description: str  # one-liner from style.md, or ""
    crystals: int


def _voices_root(state_root: Optional[Path] = None) -> Path:
    if state_root is None:
        state_root = Path.home() / ".linafish"
    return state_root / VOICES_SUBDIR


def _style_dir(name: str, state_root: Optional[Path] = None) -> Path:
    return _voices_root(state_root) / name


def _readme_path(style_dir: Path) -> Path:
    return style_dir / "style.md"


def _read_description(style_dir: Path) -> str:
    readme = _readme_path(style_dir)
    if not readme.exists():
        return ""
    try:
        for line in readme.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                return line
        return ""
    except OSError:
        return ""


def _crystal_count(style_dir: Path) -> int:
    name = style_dir.name
    crystals = style_dir / f"{name}_crystals.jsonl"
    if not crystals.exists():
        return 0
    try:
        with crystals.open("r", encoding="utf-8", errors="replace") as fh:
            return sum(1 for _ in fh)
    except OSError:
        return 0


def add_style(
    name: str,
    description: str,
    voice_from: Optional[Path] = None,
    state_root: Optional[Path] = None,
) -> StyleInfo:
    """Create a style and (optionally) absorb voice seed material.

    Args:
        name: short style name (e.g. "annie-dillard", "wyoming", "your-own").
        description: one-line description of what register this voice carries.
        voice_from: optional path to seed material (file or dir of files
            written in this voice). If given, ingested immediately.
        state_root: parent dir for state (default ~/.linafish).

    Returns:
        StyleInfo for the created style.
    """
    style_dir = _style_dir(name, state_root)
    style_dir.mkdir(parents=True, exist_ok=True)

    readme = _readme_path(style_dir)
    if not readme.exists():
        readme.write_text(
            f"# style: {name}\n\n"
            f"{description}\n\n"
            f"This is a voice corpus. Add more material via:\n\n"
            f"    linafish listen stdin -n {name} "
            f"--state-dir ~/.linafish/voices < more-in-this-voice.md\n\n"
            f"Invoke via:\n\n"
            f"    linafish style {name} \"<theme>\"\n",
            encoding="utf-8",
        )

    if voice_from is not None:
        voice_from = Path(voice_from).expanduser()
        if not voice_from.exists():
            raise FileNotFoundError(f"voice-from path not found: {voice_from}")
        from .engine import FishEngine
        engine = FishEngine(name=name, state_dir=style_dir)
        engine.eat_path(voice_from)

    return StyleInfo(
        name=name,
        state_dir=style_dir,
        description=_read_description(style_dir),
        crystals=_crystal_count(style_dir),
    )


def list_styles(state_root: Optional[Path] = None) -> list[StyleInfo]:
    """List all defined styles in voices/."""
    voices = _voices_root(state_root)
    if not voices.exists():
        return []
    out: list[StyleInfo] = []
    try:
        for child in sorted(voices.iterdir()):
            if not child.is_dir():
                continue
            out.append(StyleInfo(
                name=child.name,
                state_dir=child,
                description=_read_description(child),
                crystals=_crystal_count(child),
            ))
    except OSError:
        pass
    return out


def info_style(name: str, state_root: Optional[Path] = None) -> Optional[StyleInfo]:
    style_dir = _style_dir(name, state_root)
    if not style_dir.exists():
        return None
    return StyleInfo(
        name=name,
        state_dir=style_dir,
        description=_read_description(style_dir),
        crystals=_crystal_count(style_dir),
    )


def invoke_style(
    name: str,
    theme: str,
    top: int = 5,
    state_root: Optional[Path] = None,
) -> dict:
    """Surface the parts of `name`'s voice corpus relevant to `theme`.

    Returns dict with: name, description, crystals, recall (formatted
    string of top-N hits from the voice's material).
    """
    info = info_style(name, state_root)
    if info is None:
        raise FileNotFoundError(
            f"style '{name}' not found at {_style_dir(name, state_root)} — "
            f"create with: linafish style add {name} 'description'"
        )

    from .engine import FishEngine
    engine = FishEngine(name=info.name, state_dir=info.state_dir)
    recall_text = ""
    try:
        recall_text = engine.recall(theme, top=top) or ""
    except Exception as e:
        recall_text = f"(recall failed: {type(e).__name__}: {e})"

    return {
        "name": info.name,
        "description": info.description,
        "crystals": info.crystals,
        "recall": recall_text,
    }
