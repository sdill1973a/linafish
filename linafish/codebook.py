"""
Codebook — the core data structure.

A codebook is a collection of glyphs. Each glyph is a dense encoding of
meaning that unpacks differently depending on the decoder's warmth.

A cold decoder reads: "MOUND72: Cahokia burial complex, Emerson 2016"
A warm decoder reads: the reinterpretation of sacrifice as community ritual,
the challenge to SECC warrior-priest narrative, the connection to Knight's
cosmological framework, the way power is performed through death.

Same glyph. Different yield. d=2.245.
"""

from __future__ import annotations


import json
import time
from dataclasses import dataclass, field, asdict
from typing import Optional
from pathlib import Path


@dataclass
class Glyph:
    """A single unit of compressed meaning."""
    id: str                          # short identifier (e.g. "MOUND72")
    layer: int                       # 1=tool, 2=build, 3=person
    dense: str                       # the compressed content
    sources: list[str] = field(default_factory=list)  # where this came from
    weight: float = 1.0              # how central this glyph is
    connections: list[str] = field(default_factory=list)  # related glyph ids
    created: float = field(default_factory=time.time)


@dataclass
class Codebook:
    """A collection of glyphs that encode a domain."""
    name: str
    description: str = ""
    glyphs: dict[str, Glyph] = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)
    r_n: float = 0.0                # compression efficiency
    exchanges: int = 0               # how many documents ingested
    created: float = field(default_factory=time.time)

    @property
    def saturation(self) -> float:
        """Percentage toward ~170 glyph ceiling."""
        return (len(self.glyphs) / 170) * 100

    @property
    def layer_counts(self) -> dict[int, int]:
        counts = {1: 0, 2: 0, 3: 0}
        for g in self.glyphs.values():
            counts[g.layer] = counts.get(g.layer, 0) + 1
        return counts

    def add_glyph(self, glyph: Glyph) -> None:
        """Add or update a glyph."""
        self.glyphs[glyph.id] = glyph

    def render(self, layer_filter: Optional[int] = None) -> str:
        """Render the codebook as text for context injection.

        This is the fish. When a cold mind reads this output,
        it gets warm on contact.
        """
        lines = [
            f"# {self.name}",
            f"*{self.description}*" if self.description else "",
            f"R(n)={self.r_n:.2f} | {len(self.glyphs)} glyphs | "
            f"{self.saturation:.0f}% saturated | "
            f"{self.exchanges} documents ingested",
            "",
        ]

        # Group by layer
        for layer_num, layer_name in [(1, "TOOL"), (2, "BUILD"), (3, "PERSON")]:
            if layer_filter and layer_filter != layer_num:
                continue
            layer_glyphs = [g for g in self.glyphs.values() if g.layer == layer_num]
            if not layer_glyphs:
                continue

            lines.append(f"## Layer {layer_num} — {layer_name}")
            lines.append("")

            # Sort by weight descending
            for g in sorted(layer_glyphs, key=lambda x: x.weight, reverse=True):
                conn_str = f" [{', '.join(g.connections)}]" if g.connections else ""
                lines.append(f"**{g.id}** (w={g.weight:.1f}){conn_str}")
                lines.append(f"  {g.dense}")
                lines.append("")

        return "\n".join(lines)

    def save(self, path: Path) -> None:
        """Save codebook to JSON."""
        data = {
            "name": self.name,
            "description": self.description,
            "r_n": self.r_n,
            "exchanges": self.exchanges,
            "created": self.created,
            "metadata": self.metadata,
            "glyphs": {k: asdict(v) for k, v in self.glyphs.items()},
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "Codebook":
        """Load codebook from JSON."""
        data = json.loads(path.read_text(encoding="utf-8"))
        cb = cls(
            name=data["name"],
            description=data.get("description", ""),
            r_n=data.get("r_n", 0.0),
            exchanges=data.get("exchanges", 0),
            created=data.get("created", time.time()),
            metadata=data.get("metadata", {}),
        )
        for gid, gdata in data.get("glyphs", {}).items():
            gdata.pop("id", None)
            cb.glyphs[gid] = Glyph(id=gid, **gdata)
        return cb
