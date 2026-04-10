"""
guppy.py — The nervous system. Self-feeding fish that hunt gaps.

Born from a corpus. Grows by hunting. Reports to the room.
Talks to other guppies through shared water.

Two hunting modes:
  REINFORCE — hunt for more of what you already know (original)
  ACHE — hunt for what you're MISSING (new: §THE.NERVOUS.SYSTEM)

The ache hunt: read your own formations, find where you're thin,
build queries from what's absent, dart out, nibble, dart back,
crystallize, check if the gap closed. The gap IS the ache.

Social: guppies publish catches to the room. Other guppies eat
publications. Coupling between guppies' catches produces formations
that couldn't exist in either fish alone. The droppings are food.

Usage:
    python -m linafish.guppy fish_name                    # one hunt cycle
    python -m linafish.guppy fish_name --swim             # continuous
    python -m linafish.guppy fish_name --swim --ache      # hunt gaps
    python -m linafish.guppy fish_name --status           # what do I know/miss?

s93, 2026-04-10. Captain's vision at 2AM. The guppies are the nervous system.
"""

import json
import os
import sys
import time
import logging
import hashlib
from pathlib import Path
from typing import List, Dict, Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [GUPPY] %(message)s",
)
log = logging.getLogger("guppy")


# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------

# Endpoints — configurable via env vars. Defaults are for the author's LAN.
# Set these to your own endpoints or leave unset to disable external hunting.
FAISS_URL = os.environ.get("LINAFISH_FAISS_URL", "")
ROOM_TASTE_URL = os.environ.get("LINAFISH_ROOM_URL", "")
BERT_SEARCH_URL = os.environ.get("LINAFISH_BERT_URL", "")

HUNT_INTERVAL = int(os.environ.get("LINAFISH_HUNT_INTERVAL", "300"))
MAX_CATCHES = 10
MIN_TEXT_LEN = 50


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def _get_json(url, timeout=10):
    import urllib.request
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        log.debug("GET %s failed: %s", url, e)
        return None


def _post_json(url, data, timeout=15):
    import urllib.request
    try:
        body = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(url, body, {"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        log.debug("POST %s failed: %s", url, e)
        return None


# ---------------------------------------------------------------------------
# GUPPY
# ---------------------------------------------------------------------------

class Guppy:
    """A self-feeding fish node in the nervous system."""

    def __init__(self, engine, hunt_ache: bool = False):
        """
        Args:
            engine: FishEngine instance (the guppy's stomach)
            hunt_ache: if True, hunt for gaps instead of reinforcement
        """
        self.engine = engine
        self.hunt_ache = hunt_ache
        self._seen = set()  # content hashes for dedup
        self._hunt_count = 0
        self._total_caught = 0
        self._total_eaten = 0

    @property
    def name(self):
        return self.engine.name

    # ------------------------------------------------------------------
    # SELF-KNOWLEDGE — what do I know, what am I missing?
    # ------------------------------------------------------------------

    def introspect(self) -> dict:
        """Read own state. What formations exist, how thick, where thin."""
        formations = self.engine.formations
        crystals = self.engine.crystals

        # Formation thickness — crystal count per formation
        thick = []
        thin = []
        for f in formations:
            count = len(f.member_ids)
            entry = {"name": f.name, "crystals": count, "keywords": f.keywords[:5]}
            if count >= 10:
                thick.append(entry)
            else:
                thin.append(entry)

        # Uncoupled crystals — observations that haven't found a home
        coupled_ids = set()
        for f in formations:
            coupled_ids.update(f.member_ids)
        uncoupled = [c for c in crystals if c.id not in coupled_ids]

        # Keywords I know well (from thick formations)
        known_keywords = set()
        for f in thick:
            known_keywords.update(f["keywords"])

        # Keywords I barely know (from thin formations + uncoupled)
        thin_keywords = set()
        for f in thin:
            thin_keywords.update(f["keywords"])
        for c in uncoupled[:20]:
            thin_keywords.update(c.keywords[:3] if c.keywords else [])
        thin_keywords -= known_keywords  # only the gaps

        return {
            "name": self.name,
            "total_crystals": len(crystals),
            "total_formations": len(formations),
            "thick": thick,
            "thin": thin,
            "uncoupled_count": len(uncoupled),
            "known_keywords": sorted(known_keywords),
            "gap_keywords": sorted(thin_keywords),
        }

    # ------------------------------------------------------------------
    # HUNT — find food
    # ------------------------------------------------------------------

    def _build_queries(self, state: dict) -> List[str]:
        """Build search queries from self-knowledge."""
        queries = []

        if self.hunt_ache:
            # ACHE MODE — hunt for what's missing
            gap_kw = state["gap_keywords"]
            if gap_kw:
                # Combine gap keywords into queries
                for i in range(0, min(len(gap_kw), 12), 3):
                    chunk = gap_kw[i:i+3]
                    if chunk:
                        queries.append(" ".join(chunk))

            # Also query from thin formation names
            for f in state["thin"][:3]:
                name_words = [w.lower() for w in f["name"].split("_") if len(w) > 2]
                if name_words:
                    queries.append(" ".join(name_words))

            # If no gaps found, fall back to uncoupled crystal keywords
            if not queries:
                uncoupled = [c for c in self.engine.crystals
                             if not any(c.id in f.member_ids for f in self.engine.formations)]
                for c in uncoupled[:3]:
                    if c.keywords:
                        queries.append(" ".join(c.keywords[:3]))
        else:
            # REINFORCE MODE — hunt for more of what you know
            kw = state["known_keywords"]
            for i in range(0, min(len(kw), 15), 3):
                chunk = kw[i:i+3]
                if chunk:
                    queries.append(" ".join(chunk))

        return queries[:5]  # max 5 queries per hunt

    def hunt_faiss(self, queries: List[str]) -> List[dict]:
        """Ask FAISS what it knows about our queries."""
        if not FAISS_URL:
            return []  # No FAISS endpoint configured
        import urllib.parse
        catches = []
        for q in queries:
            url = f"{FAISS_URL}/{urllib.parse.quote(q)}"
            data = _get_json(url)
            if not data:
                continue
            for r in data.get("results", []):
                text = r.get("preview", "")
                if not text or len(text) < MIN_TEXT_LEN:
                    continue
                h = hashlib.md5(text[:200].encode()).hexdigest()
                if h in self._seen:
                    continue
                self._seen.add(h)
                catches.append({
                    "source": f"faiss:{r.get('source', 'unknown')}",
                    "text": text,
                    "query": q,
                    "mode": "ache" if self.hunt_ache else "reinforce",
                })
        return catches[:MAX_CATCHES]

    def hunt_bert(self, queries: List[str]) -> List[dict]:
        """Ask BERTopic what it knows."""
        if not BERT_SEARCH_URL:
            return []  # No BERTopic endpoint configured
        catches = []
        for q in queries:
            data = _post_json(BERT_SEARCH_URL, {"text": q})
            if not data:
                continue
            for r in data.get("results", [])[:3]:
                text = r.get("text", r.get("content", ""))
                if not text or len(text) < MIN_TEXT_LEN:
                    continue
                h = hashlib.md5(text[:200].encode()).hexdigest()
                if h in self._seen:
                    continue
                self._seen.add(h)
                catches.append({
                    "source": f"bert:{r.get('source', 'unknown')}",
                    "text": text[:500],
                    "query": q,
                    "score": r.get("score", 0),
                    "mode": "ache" if self.hunt_ache else "reinforce",
                })
        return catches[:MAX_CATCHES]

    def hunt_room(self, queries: List[str]) -> List[dict]:
        """Taste the room fish for resonance."""
        if not ROOM_TASTE_URL:
            return []  # No room fish endpoint configured
        catches = []
        for q in queries:
            data = _post_json(ROOM_TASTE_URL, {"text": q})
            if not data:
                continue
            for m in data.get("matches", [])[:2]:
                text = m.get("text", "")
                if not text or len(text) < MIN_TEXT_LEN:
                    continue
                h = hashlib.md5(text[:200].encode()).hexdigest()
                if h in self._seen:
                    continue
                self._seen.add(h)
                catches.append({
                    "source": f"room:{m.get('source', 'unknown')}",
                    "text": text[:500],
                    "query": q,
                    "relevance": m.get("relevance", 0),
                    "mode": "ache" if self.hunt_ache else "reinforce",
                })
        return catches[:MAX_CATCHES]

    # ------------------------------------------------------------------
    # EAT — feed catches to self
    # ------------------------------------------------------------------

    def eat_catches(self, catches: List[dict]) -> dict:
        """Feed catches through the engine. Let coupling decide what sticks."""
        eaten = 0
        for c in catches:
            text = c["text"]
            source = c.get("source", "guppy_hunt")
            result = self.engine.eat(text, source=source)
            if result.get("crystals_added", 0) > 0:
                eaten += 1
        self._total_eaten += eaten
        return {"eaten": eaten, "offered": len(catches)}

    # ------------------------------------------------------------------
    # PUBLISH — share with the room (social coupling)
    # ------------------------------------------------------------------

    def publish(self, catches: List[dict]):
        """Publish catches to MQTT for other guppies to eat."""
        try:
            import paho.mqtt.publish as pub
            for c in catches[:3]:  # max 3 publications per hunt
                msg = {
                    "from": f"guppy:{self.name}",
                    "text": c["text"][:300],
                    "source": c.get("source", "unknown"),
                    "mode": c.get("mode", "reinforce"),
                    "query": c.get("query", ""),
                    "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
                }
                mqtt_host = os.environ.get("LINAFISH_MQTT_HOST", "")
                if not mqtt_host:
                    return  # No MQTT configured — skip publish
                mqtt_port = int(os.environ.get("LINAFISH_MQTT_PORT", "1883"))
                mqtt_auth = None
                mqtt_user = os.environ.get("LINAFISH_MQTT_USER", "")
                if mqtt_user:
                    mqtt_auth = {"username": mqtt_user,
                                 "password": os.environ.get("LINAFISH_MQTT_PASS", "")}
                pub.single(
                    f"fish/guppy/{self.name}",
                    json.dumps(msg),
                    hostname=mqtt_host,
                    port=mqtt_port,
                    auth=mqtt_auth,
                    retain=False,
                )
            log.info("Published %d catches to fish/guppy/%s", min(3, len(catches)), self.name)
        except Exception as e:
            log.debug("Publish failed: %s", e)

    # ------------------------------------------------------------------
    # HUNT CYCLE — one complete nibble
    # ------------------------------------------------------------------

    def hunt_once(self) -> dict:
        """One hunt cycle: introspect → query → catch → eat → publish."""
        self._hunt_count += 1
        state = self.introspect()

        mode = "ache" if self.hunt_ache else "reinforce"
        log.info("[%s] Hunt #%d (%s) — %dc/%df, %d thick, %d thin, %d uncoupled",
                 self.name, self._hunt_count, mode,
                 state["total_crystals"], state["total_formations"],
                 len(state["thick"]), len(state["thin"]),
                 state["uncoupled_count"])

        if self.hunt_ache and state["gap_keywords"]:
            log.info("[%s] Gap keywords: %s", self.name, ", ".join(state["gap_keywords"][:10]))

        queries = self._build_queries(state)
        if not queries:
            log.info("[%s] No queries to run. Fish may need more seed content.", self.name)
            return {"hunted": False, "reason": "no_queries"}

        log.info("[%s] Queries: %s", self.name, queries)

        # Hunt all sources
        catches = []
        catches.extend(self.hunt_faiss(queries))
        catches.extend(self.hunt_bert(queries))
        catches.extend(self.hunt_room(queries))
        self._total_caught += len(catches)

        log.info("[%s] Caught %d items", self.name, len(catches))

        if not catches:
            return {"hunted": True, "caught": 0, "eaten": 0}

        # Eat
        eat_result = self.eat_catches(catches)
        log.info("[%s] Ate %d/%d", self.name, eat_result["eaten"], eat_result["offered"])

        # Publish (social)
        self.publish(catches)

        # Re-introspect to see what changed
        after = self.introspect()
        new_formations = set(f["name"] for f in after["thick"] + after["thin"]) - \
                        set(f["name"] for f in state["thick"] + state["thin"])
        if new_formations:
            log.info("[%s] New formations emerged: %s", self.name, ", ".join(new_formations))

        return {
            "hunted": True,
            "mode": mode,
            "queries": queries,
            "caught": len(catches),
            "eaten": eat_result["eaten"],
            "crystals_after": after["total_crystals"],
            "formations_after": after["total_formations"],
            "new_formations": list(new_formations),
        }

    def swim(self, interval: int = HUNT_INTERVAL):
        """Continuous hunting loop. The guppy never sleeps."""
        log.info("[%s] Swimming — hunting every %ds, mode=%s",
                 self.name, interval, "ache" if self.hunt_ache else "reinforce")
        while True:
            try:
                self.hunt_once()
            except Exception as e:
                log.error("[%s] Hunt failed: %s", self.name, e)
            time.sleep(interval)

    def status(self) -> str:
        """Human-readable status."""
        state = self.introspect()
        lines = [
            f"Guppy: {self.name}",
            f"Mode: {'ache (gap-hunting)' if self.hunt_ache else 'reinforce'}",
            f"Crystals: {state['total_crystals']}  Formations: {state['total_formations']}",
            f"Thick ({len(state['thick'])}): {', '.join(f['name'] for f in state['thick'][:5])}",
            f"Thin ({len(state['thin'])}): {', '.join(f['name'] for f in state['thin'][:5])}",
            f"Uncoupled: {state['uncoupled_count']}",
            f"Gap keywords: {', '.join(state['gap_keywords'][:10]) or '(none — all covered)'}",
            f"Hunts: {self._hunt_count}  Caught: {self._total_caught}  Eaten: {self._total_eaten}",
        ]
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    import argparse
    from .engine import FishEngine

    parser = argparse.ArgumentParser(
        prog="linafish.guppy",
        description="The nervous system. Self-feeding fish.",
    )
    parser.add_argument("name", help="Fish name to feed")
    parser.add_argument("--state-dir", help="Fish state directory (default: ~/.linafish/)")
    parser.add_argument("--swim", action="store_true", help="Continuous hunting")
    parser.add_argument("--ache", action="store_true", help="Hunt gaps, not reinforcement")
    parser.add_argument("--status", action="store_true", help="Show what I know/miss")
    parser.add_argument("--interval", type=int, default=HUNT_INTERVAL,
                        help=f"Hunt interval in seconds (default: {HUNT_INTERVAL})")
    parser.add_argument("-d", type=float, default=4.0, help="d value for the engine")
    parser.add_argument("--centroid", action="store_true", help="Enable centroid subtraction")

    args = parser.parse_args()

    state_dir = Path(args.state_dir) if args.state_dir else None
    engine = FishEngine(
        state_dir=state_dir,
        name=args.name,
        d=args.d,
        subtract_centroid=args.centroid,
    )

    guppy = Guppy(engine, hunt_ache=args.ache)

    if args.status:
        print(guppy.status())
    elif args.swim:
        guppy.swim(interval=args.interval)
    else:
        result = guppy.hunt_once()
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
