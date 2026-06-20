"""Episodic recall layer — moment-with-context retrieval on top of the
semantic substrate.

LiNafish is a *semantic* memory: crystals score on 8 cognitive dimensions,
coupling is gamma overlap, formations are connected components. That captures
*how* someone thinks — the gist, the fact-of. It structurally cannot hand back
the lived-specific: *that conversation, that day*, in order, with enough text to
be recognizable.

This module adds that faculty as an additive layer (Cal's SPEC_v0.2,
2026-06-10, parent issue arena-engine#21). It is pure logic — dataclasses and
functions over an episode index + a crystal-id map. The engine wires it to the
crystal store; the converse server exposes it over HTTP.

Built on the chaincode marriage fields (chain_created_at) and three new
session-scoped Crystal fields (episode_id / episode_seq / episode_kind).
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# Scoring weights — exposed as constants per spec §7/§11.8 so callers and
# future per-fish tuning can override. relevance =
#   w_pivot   * pivot_gamma
# + w_density * (1 - 1/(1 + |before| + |after|))
# + w_recency * exp(-age_in_days / decay_constant)
# - w_orphan_penalty * (episode_id == "orphan")
WEIGHTS: Dict[str, float] = {
    "w_pivot": 0.5,
    "w_density": 0.2,
    "w_recency": 0.2,
    "w_orphan_penalty": 0.1,
    "decay_constant": 30.0,
}

ORPHAN = "orphan"


@dataclass
class EpisodicMoment:
    """The smallest unit that makes a recalled experience legible.

    A single crystal answers "what was thought." A moment answers "what was
    happening when that was thought" — the pivot(s) plus the ordered episode
    neighbors around them.
    """
    episode_id: str
    episode_kind: str
    pivots: List[Any]                       # Crystals matching the query (>=1 after dedup)
    before: List[Any] = field(default_factory=list)   # predecessors, oldest first
    after: List[Any] = field(default_factory=list)    # successors
    relevance: float = 0.0
    created_at: Optional[str] = None
    source_excerpt: Optional[str] = None
    source_total_chars: Optional[int] = None

    def to_dict(self) -> dict:
        def _c(crys):
            return crys.to_dict() if hasattr(crys, "to_dict") else crys
        return {
            "episode_id": self.episode_id,
            "episode_kind": self.episode_kind,
            "pivots": [_c(c) for c in self.pivots],
            "before": [_c(c) for c in self.before],
            "after": [_c(c) for c in self.after],
            "relevance": round(self.relevance, 4),
            "created_at": self.created_at,
            "source_excerpt": self.source_excerpt,
            "source_total_chars": self.source_total_chars,
        }


@dataclass
class ChainSource:
    """Source-text preservation record — one per episode, append-only.

    Lives in ``<fish>_sources.jsonl``. ``crystal_ids`` is intentionally NOT
    stored: it is recoverable from the episode index and storing it would
    create a synchronization hazard on re-eat (spec §4.3).
    """
    episode_id: str
    episode_kind: str
    created_at: str
    full_text: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "episode_id": self.episode_id,
            "episode_kind": self.episode_kind,
            "created_at": self.created_at,
            "full_text": self.full_text,
            "metadata": self.metadata,
        }


def _crystal_ts(crystal) -> Optional[str]:
    """Best timestamp for a crystal: chain_created_at (real time of the
    source event) if present, else the crystallization ts."""
    return getattr(crystal, "chain_created_at", None) or getattr(crystal, "ts", None)


def _parse_ts(ts: Optional[str]) -> Optional[datetime]:
    if not ts:
        return None
    try:
        s = ts.replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


def load_episode(episode_id: str, index: Dict[str, dict],
                 crystal_by_id: Dict[str, Any]) -> Optional[List[Any]]:
    """Resolve an episode_id to its ordered crystal list, or None if not
    indexed.

    The final filter tolerates stale references: a crystal_id in the index
    may point at a crystal dropped during a re-eat (vocab shifted, the
    crystal didn't survive). Silently filter rather than fail (spec §5.4).
    """
    entry = index.get(episode_id)
    if entry is None:
        return None
    crystals = [crystal_by_id.get(cid) for cid in entry.get("ordered_crystal_ids", [])]
    return [c for c in crystals if c is not None]


def _orphan_moment(pivot) -> EpisodicMoment:
    """A pivot with no resolvable episode: empty neighbors, episode_id=orphan.
    Keeps recall functional on legacy/un-indexed fish (spec §6)."""
    return EpisodicMoment(
        episode_id=ORPHAN,
        episode_kind=getattr(pivot, "episode_kind", None) or "unknown",
        pivots=[pivot],
        before=[],
        after=[],
        created_at=_crystal_ts(pivot),
    )


def walk(pivot, episode: Optional[List[Any]],
         max_before: int = 5, max_after: int = 5,
         time_horizon_sec: int = 86400) -> EpisodicMoment:
    """Build the moment around a pivot crystal from its ordered episode.

    Bounded radius (max_before/max_after) + a time horizon that drops
    neighbors whose timestamp differs from the pivot's by more than
    time_horizon_sec — defends against stitching unrelated chunks from
    long-running re-eat artifacts (spec §6). Returns an orphan moment when
    the pivot has no episode or isn't found in it.
    """
    episode_id = getattr(pivot, "episode_id", None)
    if not episode_id or episode is None:
        return _orphan_moment(pivot)

    # Guarded lookup — the pivot id may not be in the episode after a re-eat.
    p_idx = None
    for i, c in enumerate(episode):
        if c.id == pivot.id:
            p_idx = i
            break
    if p_idx is None:
        return _orphan_moment(pivot)

    before = episode[max(0, p_idx - max_before):p_idx]
    after = episode[p_idx + 1:p_idx + 1 + max_after]

    # Time horizon — keep only neighbors within the window of the pivot.
    p_t = _parse_ts(_crystal_ts(pivot))
    if p_t is not None:
        def _within(c) -> bool:
            c_t = _parse_ts(_crystal_ts(c))
            if c_t is None:
                return False
            return abs((c_t - p_t).total_seconds()) < time_horizon_sec
        before = [c for c in before if _within(c)]
        after = [c for c in after if _within(c)]

    created_at = _crystal_ts(before[0]) if before else _crystal_ts(pivot)
    return EpisodicMoment(
        episode_id=episode_id,
        episode_kind=getattr(pivot, "episode_kind", None) or "unknown",
        pivots=[pivot],
        before=before,
        after=after,
        created_at=created_at,
    )


def score_moment(moment: EpisodicMoment, pivot_gamma: float,
                 now: Optional[datetime] = None,
                 weights: Optional[Dict[str, float]] = None) -> float:
    """Composite relevance (spec §7). Mutates and returns moment.relevance."""
    w = weights or WEIGHTS
    now = now or datetime.now(timezone.utc)

    density = 1.0 - 1.0 / (1.0 + len(moment.before) + len(moment.after))

    recency = 0.0
    created = _parse_ts(moment.created_at)
    if created is not None:
        age_days = max(0.0, (now - created).total_seconds() / 86400.0)
        decay = w.get("decay_constant", 30.0) or 30.0
        recency = pow(2.718281828459045, -age_days / decay)

    orphan_pen = w.get("w_orphan_penalty", 0.0) if moment.episode_id == ORPHAN else 0.0

    moment.relevance = (
        w.get("w_pivot", 0.0) * pivot_gamma
        + w.get("w_density", 0.0) * density
        + w.get("w_recency", 0.0) * recency
        - orphan_pen
    )
    return moment.relevance


def assemble_source_excerpt(moment: EpisodicMoment) -> None:
    """Populate source_excerpt/source_total_chars from the crystals' own
    preserved text (before + pivots + after, in order). This is the v1-core
    source surface — assembled from crystal.text, which is stored untruncated.
    The separate untruncated *_sources.jsonl store (ChainSource) + /moment
    endpoint are the higher-privacy commit-2 surface.
    """
    ordered = list(moment.before) + list(moment.pivots) + list(moment.after)
    parts = [getattr(c, "text", "") or "" for c in ordered]
    joined = "\n\n".join(p for p in parts if p)
    moment.source_excerpt = joined
    moment.source_total_chars = len(joined)
