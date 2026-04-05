"""
Feedback — the fish learns from usage.

When a formation helps, its weight goes up.
When it doesn't, weight decays. RTI needs assessment.

The loop: eat -> crystallize -> form -> serve -> use -> feedback -> eat
The fish that learns what matters through use.
"""

import json
import time
from pathlib import Path
from typing import Optional


class FeedbackLoop:
    """Track which formations get used and whether they help."""

    def __init__(self, state_path: Optional[Path] = None):
        self.state_path = state_path or Path("linafish_feedback.json")
        self.usage = {}  # formation_name -> {hits, helpful, unhelpful, last_used}
        self._load()

    def _load(self):
        if self.state_path.exists():
            self.usage = json.loads(self.state_path.read_text(encoding="utf-8"))

    def _save(self):
        self.state_path.write_text(
            json.dumps(self.usage, indent=2), encoding="utf-8"
        )

    def hit(self, formation_name: str, helpful: bool = True):
        """Record that a formation was used."""
        if formation_name not in self.usage:
            self.usage[formation_name] = {
                "hits": 0, "helpful": 0, "unhelpful": 0,
                "last_used": 0, "weight_modifier": 1.0,
            }

        entry = self.usage[formation_name]
        entry["hits"] += 1
        entry["last_used"] = time.time()

        if helpful:
            entry["helpful"] += 1
            # Weight goes up: more helpful = more prominent in codebook
            entry["weight_modifier"] = min(3.0, entry["weight_modifier"] * 1.1)
        else:
            entry["unhelpful"] += 1
            # Weight decays: unhelpful formations fade
            entry["weight_modifier"] = max(0.1, entry["weight_modifier"] * 0.85)

        self._save()

    def get_weight(self, formation_name: str) -> float:
        """Get the feedback-adjusted weight for a formation."""
        entry = self.usage.get(formation_name, {})
        return entry.get("weight_modifier", 1.0)

    def decay_unused(self, days: float = 7.0):
        """Decay formations that haven't been used recently."""
        cutoff = time.time() - (days * 86400)
        for name, entry in self.usage.items():
            if entry["last_used"] < cutoff and entry["hits"] > 0:
                entry["weight_modifier"] = max(0.1, entry["weight_modifier"] * 0.95)
        self._save()

    def report(self) -> str:
        """Show what the fish has learned about what matters."""
        if not self.usage:
            return "No usage data yet. The fish hasn't been tasted."

        lines = ["Formation Usage Report:", ""]
        sorted_usage = sorted(
            self.usage.items(),
            key=lambda x: x[1].get("weight_modifier", 1.0),
            reverse=True,
        )
        for name, entry in sorted_usage:
            helpful_pct = (
                entry["helpful"] / entry["hits"] * 100
                if entry["hits"] > 0 else 0
            )
            lines.append(
                f"  {name}: {entry['hits']} hits, "
                f"{helpful_pct:.0f}% helpful, "
                f"weight={entry['weight_modifier']:.2f}"
            )

        return "\n".join(lines)
