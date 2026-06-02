"""Keeper pattern — focused single-purpose sub-fish you invoke by name.

A *keeper* is a small, deliberately-scoped fish that holds one
specific kind of material (a person's identity, a manuscript's
canon, a relationship's texture, a domain's conventions) and is
designed to be invoked when that scope is the load-bearing one.

The pattern is a focused single-purpose keeper —
each scoped to one domain — a focused
fish + a Claude Code subagent definition that queries it. This
module ships the CLI half of that pattern: any user can `init` a
keeper from seed material and `invoke` it with a theme query.

The keeper differs from a general fish in three ways:

  1. Purpose-tagged. Each keeper has a one-line description of what
     it holds, written into its keeper.md README. The description
     surfaces in `linafish keeper list` so future-you remembers
     why each keeper exists.

  2. Convention-named. Keepers live at ~/.linafish/<name>-keeper/
     (the -keeper suffix is the marker). `linafish keeper list`
     scans that suffix.

  3. Invoke-shape. `linafish keeper invoke <name> "<theme>"` returns
     a structured response (persona one-liner + top-K relevant
     crystals) — same shape every time, so calling code doesn't
     have to reformat per-keeper.

Backed by FishEngine — keepers are just fish with discipline.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


KEEPER_SUFFIX = "-keeper"


@dataclass
class KeeperInfo:
    name: str           # e.g. "research"  (not "research-keeper")
    full_name: str      # e.g. "research-keeper"
    state_dir: Path     # ~/.linafish/research-keeper/
    purpose: str        # one-liner from keeper.md, or ""
    crystals: int       # current crystal count (0 if no fish yet)


def _keeper_dir(name: str, state_root: Optional[Path] = None) -> Path:
    """Resolve a keeper's state directory.

    `name` may be "research" or "research-keeper" — we normalize to add
    the -keeper suffix if missing.
    """
    if state_root is None:
        state_root = Path.home() / ".linafish"
    full_name = name if name.endswith(KEEPER_SUFFIX) else f"{name}{KEEPER_SUFFIX}"
    return state_root / full_name


def _readme_path(keeper_dir: Path) -> Path:
    return keeper_dir / "keeper.md"


def _read_purpose(keeper_dir: Path) -> str:
    """Pull the one-liner purpose from keeper.md (first non-empty line)."""
    readme = _readme_path(keeper_dir)
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


def _crystal_count(keeper_dir: Path) -> int:
    """Count lines in the crystals jsonl, 0 if absent."""
    name = keeper_dir.name
    crystals = keeper_dir / f"{name}_crystals.jsonl"
    if not crystals.exists():
        return 0
    try:
        with crystals.open("r", encoding="utf-8", errors="replace") as fh:
            return sum(1 for _ in fh)
    except OSError:
        return 0


def init_keeper(
    name: str,
    purpose: str,
    seed_path: Optional[Path] = None,
    state_root: Optional[Path] = None,
) -> KeeperInfo:
    """Create a keeper and (optionally) absorb seed material.

    Args:
        name: short keeper name (e.g. "anchor"). The on-disk dir gets
            the -keeper suffix added automatically.
        purpose: one-line description of what this keeper holds. Saved
            as the first prose line of keeper.md so future invocations
            can surface it.
        seed_path: optional file or directory to absorb on init. If
            given, the keeper is seeded immediately; if None, the
            keeper is created empty and the caller can feed it later
            via `linafish listen stdin -n <name>-keeper`.
        state_root: parent dir for keeper state (default ~/.linafish).

    Returns:
        KeeperInfo describing the created keeper.
    """
    keeper_dir = _keeper_dir(name, state_root)
    full_name = keeper_dir.name
    keeper_dir.mkdir(parents=True, exist_ok=True)

    # Write the README first so purpose is captured even if seeding fails.
    readme = _readme_path(keeper_dir)
    if not readme.exists():
        readme.write_text(
            f"# {full_name}\n\n"
            f"{purpose}\n\n"
            f"This is a keeper — a focused, single-purpose fish. Invoke via:\n\n"
            f"    linafish keeper invoke {name.removesuffix(KEEPER_SUFFIX)} "
            f"\"<theme>\"\n\n"
            f"Feed via:\n\n"
            f"    linafish listen stdin -n {full_name} < material.md\n",
            encoding="utf-8",
        )

    # Optional seed ingestion.
    if seed_path is not None:
        seed_path = Path(seed_path).expanduser()
        if not seed_path.exists():
            raise FileNotFoundError(f"seed path not found: {seed_path}")
        # Defer import so this module loads fast even if engine isn't needed.
        from .engine import FishEngine
        engine = FishEngine(name=full_name, state_dir=keeper_dir)
        engine.eat_path(seed_path)

    return KeeperInfo(
        name=name.removesuffix(KEEPER_SUFFIX),
        full_name=full_name,
        state_dir=keeper_dir,
        purpose=_read_purpose(keeper_dir),
        crystals=_crystal_count(keeper_dir),
    )


def list_keepers(state_root: Optional[Path] = None) -> list[KeeperInfo]:
    """List all keepers in the state root (dirs ending in -keeper)."""
    if state_root is None:
        state_root = Path.home() / ".linafish"
    if not state_root.exists():
        return []
    out: list[KeeperInfo] = []
    try:
        for child in sorted(state_root.iterdir()):
            if child.is_dir() and child.name.endswith(KEEPER_SUFFIX):
                short = child.name.removesuffix(KEEPER_SUFFIX)
                out.append(KeeperInfo(
                    name=short,
                    full_name=child.name,
                    state_dir=child,
                    purpose=_read_purpose(child),
                    crystals=_crystal_count(child),
                ))
    except OSError:
        pass
    return out


def info_keeper(
    name: str,
    state_root: Optional[Path] = None,
) -> Optional[KeeperInfo]:
    """Return info for a single keeper, or None if absent."""
    keeper_dir = _keeper_dir(name, state_root)
    if not keeper_dir.exists():
        return None
    return KeeperInfo(
        name=name.removesuffix(KEEPER_SUFFIX),
        full_name=keeper_dir.name,
        state_dir=keeper_dir,
        purpose=_read_purpose(keeper_dir),
        crystals=_crystal_count(keeper_dir),
    )


def invoke_keeper(
    name: str,
    theme: str,
    top: int = 5,
    state_root: Optional[Path] = None,
) -> dict:
    """Query a keeper with a theme; return persona + top hits.

    Args:
        name: keeper short name.
        theme: query string.
        top: max recall hits to return (default 5).
        state_root: parent dir for keeper state.

    Returns:
        Dict with:
          - name, full_name, purpose, crystals (KeeperInfo fields)
          - persona: one-line cognitive summary (top formation interpretation)
            or "" if no formations yet
          - recall: formatted multi-line string of top-N hits (the same
            output shape `linafish recall` produces). A future enhancement
            may add a `hits: list[dict]` field once engine.recall gains
            a structured-return mode; until then `recall` is the string.
    """
    info = info_keeper(name, state_root)
    if info is None:
        raise FileNotFoundError(
            f"keeper '{name}' not found at {_keeper_dir(name, state_root)} — "
            f"create it with: linafish keeper init {name} 'purpose'"
        )

    # Defer engine import for fast-path on info/list verbs.
    from .engine import FishEngine
    engine = FishEngine(name=info.full_name, state_dir=info.state_dir)

    # Persona = top formation interpretation, if any.
    persona = ""
    if engine.formations:
        try:
            from .formations import formation_rank_key, interpret_formation
            top_f = sorted(
                engine.formations, key=formation_rank_key, reverse=True
            )[0]
            persona = interpret_formation(top_f)
        except Exception:
            persona = ""

    # Recall — engine.recall returns a formatted multi-line string with
    # "[N/M terms] (source)\n  excerpt..." blocks. We pass it through;
    # callers display it directly. For programmatic consumers wanting
    # structured hits, that's a follow-up enhancement (engine.recall
    # could grow a return_format='dict' kwarg later).
    recall_text = ""
    try:
        recall_text = engine.recall(theme, top=top) or ""
    except Exception as e:
        recall_text = f"(recall failed: {type(e).__name__}: {e})"

    return {
        "name": info.name,
        "full_name": info.full_name,
        "purpose": info.purpose,
        "crystals": info.crystals,
        "persona": persona,
        "recall": recall_text,
    }
