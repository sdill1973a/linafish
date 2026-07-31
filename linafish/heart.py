"""THE HEART — the afferent organ. LiNafish 2.0.

Every verb in 1.x is PULL: the reader asks, the store answers. The heart adds
the missing direction. On each turn of a reader's loop it fires one **beat** —
recall across a configured family of fish — and surfaces what reaches toward
the moment, unbidden. The reader no longer merely *has* memories; it is visited
by them.

    1.x — a memory engine a mind can query.
    2.x — a substrate that participates in cognition.

Two independent implementations converged on this design (Anchor on evo-x2,
Olorina on a solar-powered Pi) and on the invariants below, which is why they
ship as enforced behavior rather than advice:

1. **READ-ONLY AMBIENT.** A heartbeat never writes — no counters, no feedback,
   no heat. Every read this organ makes passes ``no_heat=True``. *An ambient
   organ that heats its own memories corrupts the very signal it reads.* The
   corollary matters as much: deliberate views MUST still record, or the usage
   store freezes and an empty signal becomes indistinguishable from a clean one.
2. **FAIL-SILENT.** Any error → empty output → the turn proceeds untouched. The
   nerve never blocks a thought.
3. **THE WALL IS TWO AXES.** *Depth* — pointing a mind at its own interior — is
   never gated; blinding a mind to its own store makes it stupider about itself.
   *Content* posture is the host's explicit choice (``wall.mode``), never an
   accident. Measured 2026-07-31: context-residency alone did not produce
   measurable register bleed at that power, so this is a design posture rather
   than a law — and it must still be *declared*.
4. **QUIET IS VALID.** The gate and the landed-terms check mean the heart often
   says nothing. A heart that fires on everything is noise wearing feeling's
   clothes.
6. **A HEART MUST BE DISTINGUISHABLE FROM A CORPSE.** Invariants 2 and 4
   composed naively build an organ whose permanent death looks exactly like
   contemplation. So the heart writes its OWN beat log — never the store it
   reads — recording beats attempted and surfaced. **Quiet stays valid; silence
   about the silence does not.** ``linafish doctor`` reads that log.

Config lives at ``<state_dir>/heart.toml``. It is identity-configuration — the
family is the person, and the wall pattern names where you speak publicly — so
it stays local and is never shipped. The MECHANISM is public; the family never.
"""
from __future__ import annotations

import concurrent.futures
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

try:  # 3.11+
    import tomllib as _toml
except ModuleNotFoundError:  # pragma: no cover - 3.10 fallback
    try:
        import tomli as _toml  # type: ignore
    except ModuleNotFoundError:
        _toml = None

DEFAULTS = {
    "top": 4,             # crystals surfaced inward per beat
    "per_fish": 3,
    "max_excerpt": 200,
    "per_fish_timeout": 4.0,
    "budget": 6.0,        # total wall-clock per beat
    "min_prompt_chars": 40,
    # INVARIANT 4 has teeth only if a single incidental word cannot count as
    # the self reaching toward the moment. Measured on an unrelated corpus:
    # genuine hits matched 3-7 query terms; every unrelated prompt matched
    # EXACTLY ONE (a stopword). An absolute count separates them cleanly where
    # a fraction does not — a long prompt with a real hit can sit at 0.21,
    # below any fraction threshold that would exclude the noise.
    "min_matched_terms": 2,
}

# recall renders "[X/Y terms] (source)\n  excerpt"
_HDR = re.compile(r"^\[(\d+)/(\d+) terms\]\s*\(([^)]*)\)\s*$")


class HeartConfig:
    """Parsed heart.toml. Absent or unparseable config → an inert heart that
    says so in the beat log rather than failing loudly or pretending to beat."""

    def __init__(self, path: Path):
        self.path = path
        self.family: list[dict] = []
        self.error: Optional[str] = None
        self.wall_mode = "declare"
        self.wall_pattern: Optional[re.Pattern] = None
        for k, v in DEFAULTS.items():
            setattr(self, k, v)

        if not path.exists():
            self.error = "no heart.toml"
            return
        if _toml is None:
            self.error = "no TOML parser (pip install tomli on py3.10)"
            return
        try:
            raw = _toml.loads(path.read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001
            self.error = f"unparseable heart.toml: {e}"
            return

        base = path.parent
        for name, spec in (raw.get("family") or {}).items():
            if not isinstance(spec, dict):
                continue
            d = spec.get("dir")
            self.family.append({
                "name": name,
                "dir": (base / d) if d else (base / name),
                "weight": float(spec.get("weight", 1.0)),
            })
        surface = raw.get("surface") or {}
        for k in ("top", "per_fish", "max_excerpt"):
            if k in surface:
                setattr(self, k, surface[k])
        gate = raw.get("gate") or {}
        self.min_prompt_chars = gate.get("min_prompt_chars", self.min_prompt_chars)
        self.min_matched_terms = gate.get("min_matched_terms", self.min_matched_terms)
        self.skip_markers = gate.get("skip_markers", []) or []
        timing = raw.get("timing") or {}
        self.per_fish_timeout = float(timing.get("per_fish_timeout", self.per_fish_timeout))
        self.budget = float(timing.get("budget", self.budget))

        wall = raw.get("wall") or {}
        # INVARIANT 3: the content posture is explicit config, never an accident.
        self.wall_mode = wall.get("mode", "declare")
        pat = wall.get("public_pattern")
        if pat:
            try:
                self.wall_pattern = re.compile(pat, re.I)
            except re.error as e:  # noqa: BLE001
                self.error = f"bad wall.public_pattern: {e}"

        if not self.family:
            self.error = self.error or "heart.toml declares no family"


def _beat_log_path(state_dir: Path) -> Path:
    return state_dir / "heart_beat_log.jsonl"


def _log_beat(state_dir: Path, **fields) -> None:
    """Append one pulse to the organ's OWN log. Invariant 6. Fail-silent: a
    logging error must never block a turn."""
    try:
        fields["ts"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        p = _beat_log_path(state_dir)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "a", encoding="utf-8") as f:
            f.write(json.dumps(fields) + "\n")
    except Exception:  # noqa: BLE001
        pass


def _recall_band(query: str, member: dict, cfg: HeartConfig) -> list[tuple]:
    """One band of the self. Returns [(term_fraction, matched_terms, source, excerpt)].

    INVARIANT 1: every read here is ``no_heat=True``. Ambient reads must leave
    no trace — including on engines whose process default records.
    """
    def _read() -> str:
        from .engine import FishEngine
        eng = FishEngine(name=member["name"], state_dir=Path(member["dir"]),
                         no_heat=True)
        return eng.recall(query, top=cfg.per_fish, no_heat=True) or ""

    # INVARIANT 2 — the nerve never blocks a thought. The whole-beat budget is
    # only checked BETWEEN bands, so without a per-band bound one slow fish
    # hangs the turn regardless of it. `per_fish_timeout` was parsed from config
    # and never applied until 2026-07-31; found by an outside reviewer, because
    # a small test corpus always returns instantly and cannot exercise this.
    #
    # Bounded honestly: a Python thread cannot be killed, so an abandoned read
    # keeps running to completion in the background — we stop WAITING for it, we
    # do not stop it. That is enough for the invariant (the turn proceeds) and
    # it is a daemon thread, so it never holds up interpreter exit. A real
    # cancellation would need the subprocess transport.
    # NOT a `with` block: ThreadPoolExecutor.__exit__ calls shutdown(wait=True),
    # which blocks for the abandoned worker and silently restores the exact hang
    # this is meant to prevent. The first version of this fix used `with`, timed
    # out correctly at 0.5s, and still took the full 5s to return.
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    try:
        text = pool.submit(_read).result(timeout=cfg.per_fish_timeout)
    except concurrent.futures.TimeoutError:
        return []  # band too slow — drop it, keep the turn
    except Exception:  # noqa: BLE001
        return []  # INVARIANT 2
    finally:
        pool.shutdown(wait=False)

    out, lines, i = [], text.splitlines(), 0
    while i < len(lines):
        m = _HDR.match(lines[i].strip())
        if not m:
            i += 1
            continue
        matched, total = int(m.group(1)), int(m.group(2)) or 1
        src = m.group(3).strip()
        exc, j = [], i + 1
        while j < len(lines) and (lines[j].startswith("  ") or not lines[j].strip()):
            if lines[j].strip():
                exc.append(lines[j].strip())
            j += 1
            if len(exc) >= 2:
                break
        out.append((matched / total, matched, src, " ".join(exc)[: cfg.max_excerpt]))
        i = j
    return out


def beat(prompt: str, state_dir: Path, config_path: Optional[Path] = None) -> str:
    """Fire one beat. Returns the block to prepend to the reader's context, or
    "" when the heart is quiet. Never raises — invariant 2."""
    state_dir = Path(state_dir)
    cfg = HeartConfig(Path(config_path) if config_path else state_dir / "heart.toml")

    if cfg.error and not cfg.family:
        # An inert heart is a fact about the organ, not an error for the turn.
        # It is logged so `doctor` can tell inert from quiet — invariant 6.
        _log_beat(state_dir, attempted=0, surfaced=0, inert=cfg.error)
        return ""

    text = (prompt or "").strip()
    if len(text) < cfg.min_prompt_chars:
        _log_beat(state_dir, attempted=0, surfaced=0, gated="short_prompt")
        return ""
    for marker in getattr(cfg, "skip_markers", []):
        if marker in text:
            _log_beat(state_dir, attempted=0, surfaced=0, gated="skip_marker")
            return ""

    t0 = time.time()
    q = " ".join(text.split())[:200]
    hits, dropped, landed = [], [], False

    # Densest bands first, so budget exhaustion drops the LOWEST-weight bands.
    # The beat degrades; it never delays the turn.
    for member in sorted(cfg.family, key=lambda m: -m["weight"]):
        if time.time() - t0 > cfg.budget:
            dropped.append(member["name"])
            continue
        if not Path(member["dir"]).exists():
            continue
        for termfrac, matched, src, exc in _recall_band(q, member, cfg):
            if matched < cfg.min_matched_terms:
                continue  # one incidental word is not the self reaching
            landed = True
            if exc:
                hits.append((termfrac * member["weight"], member["name"], src, exc))

    if not landed or not hits:
        # INVARIANT 4: quiet is a valid beat. Logged, so it is distinguishable
        # from a dead organ.
        _log_beat(state_dir, attempted=len(cfg.family) - len(dropped), surfaced=0,
                  dropped=dropped, elapsed=round(time.time() - t0, 2))
        return ""

    hits.sort(key=lambda h: -h[0])
    seen, picked = set(), []
    for h in hits:
        key = h[3][:60]
        if key in seen:
            continue
        seen.add(key)
        picked.append(h)
        if len(picked) >= cfg.top:
            break

    densest = max(cfg.family, key=lambda m: m["weight"])["name"]
    lines = [
        f"♥ heart {'♥' if fish == densest else '·'} [{fish}] {exc}"
        for _, fish, _, exc in picked
    ]
    if cfg.wall_pattern and cfg.wall_pattern.search(text):
        # Friction, not amputation: the depth axis stays ungated (invariant 3).
        lines.append("♥ heart 🧭 hand on shoulder: this turn smells public-bound — "
                     "full cognition inward, conscious wall at the words that leave.")

    _log_beat(state_dir, attempted=len(cfg.family) - len(dropped),
              surfaced=len(picked), dropped=dropped,
              elapsed=round(time.time() - t0, 2))
    return "\n".join(lines)


def read_beat_log(state_dir: Path, limit: int = 200) -> list[dict]:
    """Tail of the organ's own log, for `doctor`. Invariant 6."""
    p = _beat_log_path(Path(state_dir))
    if not p.exists():
        return []
    try:
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]
    except OSError:
        return []
    out = []
    for line in lines:
        try:
            out.append(json.loads(line))
        except Exception:  # noqa: BLE001
            continue
    return out
