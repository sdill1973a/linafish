"""
moment.py — What enters the engine.

A Moment is not just text. It's text + when + where + everything else:
ache state, relationship distance, felt state, prior chain, modifiers
from the environment. For a stranger running `linafish go ~/journal`,
the Moment is just text + source + timestamp. Context is empty. That's
fine — the engine degrades gracefully. With more channels, richer crystals.

For Lina.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone


@dataclass
class Moment:
    """A unit of experience entering the metabolic engine.

    The minimum viable moment is text + source. Everything else enriches
    but is never required. The engine runs on whatever you feed it.
    """
    text: str
    source: str
    timestamp: str = ""
    context: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    @property
    def ache_state(self) -> float:
        return self.context.get("ache_state", 0.0)

    @property
    def relationship_d(self) -> float:
        """Distance to author. stranger=6, acquaintance=4, friend=2, captain=1."""
        return self.context.get("relationship_d", 6.0)

    @property
    def felt_state(self) -> Optional[Dict]:
        return self.context.get("felt_state")

    @property
    def prior_chain(self) -> Optional[List[str]]:
        return self.context.get("prior_chain")

    @property
    def modifiers(self) -> Dict[str, float]:
        return self.context.get("modifiers", {})


@dataclass
class Residue:
    """What one metabolic pathway produces from a Moment.

    Not a score. Not a label. The compressed output of digestion
    through one cognitive organ. What survived.
    """
    pathway: str                              # which organ: KO/TE/SF/CR/IC/DE/EW/AI
    activation: float                         # how strongly the pathway fired (0-1)
    operations: List[str] = field(default_factory=list)  # which QUANTUM ops detected
    fragments: List[str] = field(default_factory=list)   # text fragments that triggered
    chain_position: Optional[str] = None      # where in the chain: 'initiator', 'responder', 'bridge'
    ache: float = 0.0                         # what this pathway lost in compression


@dataclass
class MetabolicCrystal:
    """What the engine produces. A moment fully digested.

    Eight residues from eight pathways. The chain is the order
    they fired. The ache is what didn't survive. The glyph is
    the compressed identity — category.hash.
    """
    id: str
    moment: Moment
    residues: Dict[str, Residue] = field(default_factory=dict)  # pathway -> residue
    dominant: str = ""                        # which pathway did the most work
    chain: List[str] = field(default_factory=list)  # firing order
    ache: float = 0.0                         # total compression loss
    glyph: str = ""                           # compressed id: e.g. "IC.4f2a"

    @property
    def dimension_vector(self) -> List[float]:
        """8-dim vector for compatibility with v0.3 coupling."""
        dims = ["KO", "TE", "SF", "CR", "IC", "DE", "EW", "AI"]
        return [self.residues[d].activation if d in self.residues else 0.0 for d in dims]

    @property
    def top_operations(self) -> List[str]:
        """All operations detected across all pathways."""
        ops = []
        for r in self.residues.values():
            ops.extend(r.operations)
        return ops

    @property
    def metabolic_signature(self) -> str:
        """QLP notation of the crystal's metabolism.
        e.g. IC:want > CR:hold > EW:give
        """
        if not self.chain:
            return self.dominant
        parts = []
        for dim in self.chain:
            r = self.residues.get(dim)
            if r and r.operations:
                parts.append(f"{dim}:{r.operations[0]}")
            else:
                parts.append(dim)
        return " > ".join(parts)
