"""
LiNafish School — the river and the nets.

One stream. N fish. Each grabs what resonates. Nothing lost.

Captain's directive (April 7, 2026):
"information is power — we let the mind decide"

The central fish is the mouth — everything enters there.
Each member fish has its own vocabulary, d, gamma, centroid
settings. When the school eats, every member gets offered
the same text. Coupling math decides what sticks. What
doesn't couple slides past as an uncoupled observation.

The central crystal log keeps everything. When a member's
perspective evolves (new formations, shifted vocabulary),
refeed replays the central corpus through the updated member.
Nothing is ever lost at the center. The nets get finer.

Usage:
    from linafish.school import School

    school = School(state_dir=Path("~/.linafish/school"))
    school.eat("Scott said build is your autonomic response")
    print(school.status())
    school.refeed("captain")
    print(school.docket())
"""

import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

from .engine import FishEngine


DEFAULT_MANIFEST = {
    "central": "anchor-writing",
    "members": {}
}


class School:
    """The river and the nets. One stream, N fish, coupling decides."""

    def __init__(self, state_dir: Optional[Path] = None,
                 manifest_path: Optional[Path] = None,
                 central_state_dir: Optional[Path] = None):
        """Load or create a school.

        Args:
            state_dir: Root directory for school state. Members get subdirs.
                       Defaults to ~/.linafish/school/
            manifest_path: Path to school.json manifest. Defaults to
                          state_dir/school.json
            central_state_dir: Where the central fish lives. Defaults to
                              ~/.linafish/ (the standard fish location)
        """
        self.state_dir = (state_dir or Path.home() / ".linafish" / "school").resolve()
        self.state_dir.mkdir(parents=True, exist_ok=True)

        self.manifest_path = manifest_path or (self.state_dir / "school.json")
        self.central_state_dir = central_state_dir or Path.home() / ".linafish"

        # Load or create manifest
        if self.manifest_path.exists():
            self.manifest = json.loads(
                self.manifest_path.read_text(encoding="utf-8")
            )
        else:
            self.manifest = dict(DEFAULT_MANIFEST)

        # Central fish engine — the mouth
        central_name = self.manifest.get("central", "anchor-writing")
        self.central = FishEngine(
            state_dir=self.central_state_dir,
            name=central_name,
        )

        # Member engines — the nets
        self.members: Dict[str, FishEngine] = {}
        for name, config in self.manifest.get("members", {}).items():
            member_dir = self.state_dir / name
            member_dir.mkdir(parents=True, exist_ok=True)
            self.members[name] = FishEngine(
                state_dir=member_dir,
                name=name,
                d=config.get("d", 4.0),
                min_gamma=config.get("min_gamma"),
                subtract_centroid=config.get("subtract_centroid", False),
                vocab_size=config.get("vocab_size", 200),
            )

    def save_manifest(self):
        """Write manifest to disk."""
        self.manifest_path.write_text(
            json.dumps(self.manifest, indent=2),
            encoding="utf-8",
        )

    def add_member(self, name: str, d: float = 4.0,
                   subtract_centroid: bool = False,
                   min_gamma: float = None,
                   vocab_size: int = 200):
        """Add a new member fish to the school."""
        config = {
            "d": d,
            "subtract_centroid": subtract_centroid,
            "min_gamma": min_gamma,
            "vocab_size": vocab_size,
        }
        self.manifest.setdefault("members", {})[name] = config
        self.save_manifest()

        member_dir = self.state_dir / name
        member_dir.mkdir(parents=True, exist_ok=True)
        self.members[name] = FishEngine(
            state_dir=member_dir,
            name=name,
            d=d,
            min_gamma=min_gamma,
            subtract_centroid=subtract_centroid,
            vocab_size=vocab_size,
        )

    def eat(self, text: str, source: str = "session") -> dict:
        """Feed text through the school. Central first, then all members.

        The central fish always eats. Each member's coupling math
        decides whether the crystal sticks or slides past.

        Returns dict with central result + per-member results.
        """
        if not text or len(text.strip()) < 10:
            return {"central": {"crystals_added": 0}, "members": {}}

        # Central fish eats first — the permanent record
        central_result = self.central.eat(text, source=source)

        # Each member gets offered the same text
        member_results = {}
        for name, engine in self.members.items():
            try:
                result = engine.eat(text, source=source)
                member_results[name] = result
            except Exception as e:
                member_results[name] = {"error": str(e)}

        return {
            "central": central_result,
            "members": member_results,
        }

    def eat_path(self, path: Path, source: str = None) -> dict:
        """Feed a file or directory through the school."""
        from .ingest import ingest_directory, ingest_file

        if path.is_dir():
            chunks = ingest_directory(path)
        else:
            chunks = ingest_file(path)
            if not chunks:
                text = path.read_text(encoding="utf-8", errors="replace")
                chunks = [type('Chunk', (), {'text': text, 'source': path.name})()]

        if not chunks:
            return {"central": {"crystals_added": 0}, "members": {}}

        src = source or str(path.name)
        results = {"central": {"crystals_added": 0}, "members": {n: {"crystals_added": 0} for n in self.members}}

        for chunk in chunks:
            if chunk.text and len(chunk.text.strip()) > 10:
                r = self.eat(chunk.text, source=src)
                results["central"]["crystals_added"] += r["central"].get("crystals_added", 0)
                for name in self.members:
                    if name in r["members"]:
                        results["members"][name]["crystals_added"] = (
                            results["members"][name].get("crystals_added", 0)
                            + r["members"][name].get("crystals_added", 0)
                        )

        # Save final counts
        results["central"]["total_crystals"] = len(self.central.crystals)
        results["central"]["formations"] = len(self.central.formations)
        for name, engine in self.members.items():
            results["members"][name]["total_crystals"] = len(engine.crystals)
            results["members"][name]["formations"] = len(engine.formations)

        return results

    def refeed(self, member_name: str) -> dict:
        """Replay the central crystal log through a member with a FRESH engine.

        This is the "perspective shift" path. When a member's parameters
        change (new d, centroid settings, evolved vocabulary), refeed
        rebuilds the member from scratch using the central corpus.

        The member's state is reset — fresh engine, fresh vocabulary,
        fresh formations. The central crystal log is the source of truth.
        Previous crystals are not preserved. This is a rebuild, not an append.
        """
        if member_name not in self.members:
            return {"error": f"Unknown member: {member_name}"}

        config = self.manifest.get("members", {}).get(member_name, {})

        # Read central crystal log
        central_name = self.manifest.get("central", "anchor-writing")
        crystal_log = self.central_state_dir / f"{central_name}_crystals.jsonl"

        if not crystal_log.exists():
            return {"error": f"Central crystal log not found: {crystal_log}"}

        # Reset the member — fresh engine with same config
        member_dir = self.state_dir / member_name
        # Clear existing state files
        for f in member_dir.glob("*_crystals.jsonl"):
            f.unlink()
        for f in member_dir.glob("*_v3_state.json"):
            f.unlink()
        for f in member_dir.glob("*_pending.jsonl"):
            f.unlink()
        for f in member_dir.glob("mi_vectorizer.json"):
            f.unlink()

        engine = FishEngine(
            state_dir=member_dir,
            name=member_name,
            d=config.get("d", 4.0),
            min_gamma=config.get("min_gamma"),
            subtract_centroid=config.get("subtract_centroid", False),
            vocab_size=config.get("vocab_size", 200),
        )
        self.members[member_name] = engine

        count = 0
        fed = 0
        with open(crystal_log, encoding="utf-8", errors="replace") as f:
            for line in f:
                count += 1
                try:
                    d = json.loads(line)
                    text = d.get("text", "")
                    if text and len(text.strip()) > 10:
                        source = d.get("source", "refeed")
                        engine.eat(text, source=f"refeed:{source}")
                        fed += 1
                except Exception:
                    pass

                # Progress every 50
                if count % 50 == 0:
                    print(f"  [{count}] {fed} fed, "
                          f"{len(engine.crystals)} crystals, "
                          f"{len(engine.formations)} formations",
                          file=sys.stderr)

        return {
            "member": member_name,
            "central_crystals_read": count,
            "fed": fed,
            "total_crystals": len(engine.crystals),
            "formations": len(engine.formations),
        }

    def status(self) -> dict:
        """Status of all members + central."""
        result = {
            "central": {
                "name": self.central.name,
                "crystals": len(self.central.crystals),
                "formations": len(self.central.formations),
                "epoch": self.central.fish.epoch,
            },
            "members": {},
            "member_count": len(self.members),
        }

        for name, engine in self.members.items():
            config = self.manifest.get("members", {}).get(name, {})
            result["members"][name] = {
                "crystals": len(engine.crystals),
                "formations": len(engine.formations),
                "d": config.get("d", 4.0),
                "subtract_centroid": config.get("subtract_centroid", False),
                "epoch": engine.fish.epoch,
                "top_formations": [f.name for f in engine.formations[:3]],
            }

        return result

    def docket(self) -> str:
        """Aggregate open-state sections from all member fish.md files.

        Scans each member's fish.md for patterns like:
        - Standing Orders / Upcoming / NEEDS_WORK / STALE
        - TODO / OPEN / UNRESOLVED / BLOCKERS
        - Unchecked markdown checkboxes: - [ ]

        Returns consolidated text grouped by member.
        """
        # Patterns that indicate open work
        section_patterns = re.compile(
            r'^#+\s*(standing\s*orders?|upcoming|needs?\s*work|stale|'
            r'todo|open|unresolved|blockers?|quick\s*actions?|'
            r'genuine\s*blockers?|in\s*flight)',
            re.IGNORECASE
        )
        checkbox_pattern = re.compile(r'^-\s*\[\s*\]')

        lines_out = ["# School Docket\n"]
        lines_out.append(f"*Generated {time.strftime('%Y-%m-%d %H:%M')} "
                         f"from {len(self.members)} members*\n")

        for name, engine in sorted(self.members.items()):
            fish_path = engine.fish_file
            if not fish_path.exists():
                continue

            text = fish_path.read_text(encoding="utf-8", errors="replace")
            member_items = []

            # Extract open-state sections
            in_section = False
            section_name = ""
            for line in text.split("\n"):
                if section_patterns.match(line.strip()):
                    in_section = True
                    section_name = line.strip().lstrip("#").strip()
                    continue
                elif line.startswith("#") and in_section:
                    in_section = False

                if in_section and line.strip():
                    member_items.append(line.rstrip())

                # Also catch standalone checkboxes anywhere
                if checkbox_pattern.match(line.strip()):
                    if line.rstrip() not in member_items:
                        member_items.append(line.rstrip())

            if member_items:
                lines_out.append(f"\n## {name} ({len(engine.crystals)}c / "
                                 f"{len(engine.formations)}f)")
                for item in member_items:
                    lines_out.append(item)

        if len(lines_out) <= 2:
            lines_out.append("\n*No open items found in any member fish.*")

        return "\n".join(lines_out)
