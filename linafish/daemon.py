"""
Daemon — the fish eats slowly. Or listens to the room.

Two modes:
  linafish daemon <path> --interval 5    — walk a directory, eat files
  linafish daemon --room                 — listen to MQTT, eat every exchange

Room mode: subscribe to +/conv/+ on localhost:1883. Every RCP exchange
that flows through the federation gets crystallized into the fish.
The fish becomes a silent participant. The room gets smarter.

State persists in .linafish_state.json next to the fish.
"""

import json
import os
import time
import signal
import hashlib
from pathlib import Path
from typing import Optional
from datetime import datetime

from .crystallizer import batch_ingest, couple_crystals, extend_vocabulary, Crystal
from .formations import detect_formations, hierarchical_merge, formations_to_codebook_text


class FishDaemon:
    """Background ingest daemon. Eats slowly. Saves often."""

    def __init__(
        self,
        source_dir: Path,
        state_path: Optional[Path] = None,
        fish_name: str = "linafish",
        interval: float = 5.0,
        extensions: set = None,
        context_hint: str = "",
        vocab: dict = None,
    ):
        self.source_dir = Path(source_dir)
        self.fish_name = fish_name
        self.interval = interval
        self.extensions = extensions or {".md", ".txt", ".json", ".py"}
        self.skip_dirs = {
            "node_modules", ".git", "__pycache__", ".venv", "venv",
            "site-packages", ".tox", ".eggs", "dist", "build",
            ".next", ".nuxt", "bower_components", ".cache",
        }
        self.context_hint = context_hint
        self.running = False

        # State
        self.state_path = state_path or Path(f"{fish_name}.state.json")
        self.crystals_path = Path(f"{fish_name}.crystals.json")
        self.fish_path = Path(f"{fish_name}.fish.md")

        self.eaten = set()       # file hashes already ingested
        self.folders_done = set() # folders fully eaten
        self.crystals = []       # accumulated crystals
        self.content_hashes = set()  # content-level dedup (first 500 chars hashed)
        self.stats = {"files_eaten": 0, "crystals": 0, "dupes_skipped": 0, "started": None, "last_bite": None}
        self.manifest = []       # full record
        self.manifest_path = Path(f"{fish_name}.manifest.jsonl")

        if vocab:
            extend_vocabulary(vocab)

        self._load_state()

        # Graceful shutdown
        signal.signal(signal.SIGINT, self._shutdown)
        signal.signal(signal.SIGTERM, self._shutdown)

    def _load_state(self):
        if self.state_path.exists():
            state = json.loads(self.state_path.read_text(encoding="utf-8"))
            self.eaten = set(state.get("eaten", []))
            self.folders_done = set(state.get("folders_done", []))
            self.content_hashes = set(state.get("content_hashes", []))
            self.stats = state.get("stats", self.stats)
            print(f"Resumed: {len(self.eaten)} files, {len(self.folders_done)} folders, {len(self.content_hashes)} content hashes")

        if self.crystals_path.exists():
            data = json.loads(self.crystals_path.read_text(encoding="utf-8"))
            for cd in data.get("crystals", []):
                self.crystals.append(Crystal(
                    id=cd["id"], ts=cd["ts"], text=cd["text"],
                    source=cd["source"], resonance=cd["resonance"],
                    keywords=cd["keywords"],
                    couplings=[(c, g) for c, g in cd.get("couplings", [])],
                    structural=cd.get("structural", False),
                ))
            print(f"Loaded {len(self.crystals)} existing crystals")

    def _save_state(self):
        state = {
            "eaten": list(self.eaten),
            "folders_done": list(self.folders_done),
            "content_hashes": list(self.content_hashes),
            "stats": self.stats,
        }
        self.state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

        crystal_data = [c.to_dict() for c in self.crystals]
        self.crystals_path.write_text(
            json.dumps({"crystals": crystal_data, "count": len(crystal_data)}),
            encoding="utf-8",
        )

    def _file_hash(self, path: Path) -> str:
        content = path.read_bytes()[:4096]
        return hashlib.md5(content).hexdigest()

    def _rebuild_fish(self):
        """Rebuild formations and render the fish."""
        if len(self.crystals) < 3:
            return

        # Couple only new crystals with recent ones (not full O(n²))
        # For now, couple the last batch
        recent = self.crystals[-50:] if len(self.crystals) > 50 else self.crystals
        couple_crystals(recent)

        formations = detect_formations(self.crystals)
        if len(formations) > 60:
            formations = hierarchical_merge(formations, target=50)

        codebook = formations_to_codebook_text(
            formations,
            title=f"LiNafish: {self.fish_name} ({len(self.crystals)} crystals)",
        )
        self.fish_path.write_text(codebook, encoding="utf-8")

    def _shutdown(self, signum, frame):
        print(f"\nShutting down gracefully...")
        self.running = False

    def _log_manifest(self, file_path: Path, fhash: str, crystal_count: int, status: str = "ingested"):
        """Append to manifest log. JSONL — one line per file, never a question."""
        entry = {
            "file": str(file_path),
            "hash": fhash,
            "crystals": crystal_count,
            "status": status,
            "timestamp": datetime.now().isoformat(),
            "size_bytes": file_path.stat().st_size if file_path.exists() else 0,
            "total_crystals": len(self.crystals),
            "total_files": len(self.eaten),
        }
        with open(self.manifest_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    def _extract_text(self, file_path: Path, raw: str) -> str:
        """Extract readable text from file content.

        For JSON conversation exports: parse and extract dialogue.
        For everything else: return as-is.
        Don't eat the envelope. Read the letter.
        """
        if file_path.suffix.lower() == ".json":
            try:
                data = json.loads(raw)

                # GPT conversation export format
                if isinstance(data, dict) and "conversation" in data:
                    turns = data["conversation"]
                    if isinstance(turns, list):
                        lines = []
                        for turn in turns:
                            role = turn.get("role", "")
                            content = turn.get("content", "")
                            if isinstance(content, str) and content.strip():
                                lines.append(f"[{role}]: {content}")
                        if lines:
                            return "\n\n".join(lines)

                # ChatGPT export format (mapping with messages)
                if isinstance(data, dict) and "mapping" in data:
                    lines = []
                    for node in data["mapping"].values():
                        msg = node.get("message")
                        if msg and msg.get("content", {}).get("parts"):
                            role = msg.get("author", {}).get("role", "")
                            text = " ".join(str(p) for p in msg["content"]["parts"] if isinstance(p, str))
                            if text.strip():
                                lines.append(f"[{role}]: {text}")
                    if lines:
                        return "\n\n".join(lines)

                # Array of messages
                if isinstance(data, list):
                    lines = []
                    for item in data:
                        if isinstance(item, dict):
                            role = item.get("role", item.get("author", ""))
                            content = item.get("content", item.get("text", ""))
                            if isinstance(content, str) and content.strip():
                                lines.append(f"[{role}]: {content}")
                    if lines:
                        return "\n\n".join(lines)

                # Structured scar or other JSON — dump readable
                return json.dumps(data, indent=2)[:5000]

            except json.JSONDecodeError:
                return raw

        return raw

    def eat_one(self, file_path: Path) -> int:
        """Eat a single file. Returns crystal count."""
        fhash = self._file_hash(file_path)
        if fhash in self.eaten:
            return 0

        try:
            raw = file_path.read_text(encoding="utf-8", errors="replace")
            if len(raw) < 50:
                self.eaten.add(fhash)
                self._log_manifest(file_path, fhash, 0, "skipped_too_short")
                return 0

            content = self._extract_text(file_path, raw)
            if len(content) < 50:
                self.eaten.add(fhash)
                self._log_manifest(file_path, fhash, 0, "skipped_no_content")
                return 0

            # Content-level dedup — hash first 500 chars of extracted text
            content_hash = hashlib.md5(content[:500].encode("utf-8", errors="replace")).hexdigest()
            if content_hash in self.content_hashes:
                self.eaten.add(fhash)
                self.stats["dupes_skipped"] = self.stats.get("dupes_skipped", 0) + 1
                self._log_manifest(file_path, fhash, 0, "skipped_duplicate_content")
                return 0
            self.content_hashes.add(content_hash)

            crystals = batch_ingest(
                content,
                source=file_path.name,
                context_hint=self.context_hint,
            )
            self.crystals.extend(crystals)
            self.eaten.add(fhash)
            self.stats["files_eaten"] += 1
            self.stats["crystals"] = len(self.crystals)
            self.stats["last_bite"] = datetime.now().isoformat()
            self._log_manifest(file_path, fhash, len(crystals))
            return len(crystals)

        except Exception as e:
            print(f"    Error: {e}")
            self.eaten.add(fhash)
            self._log_manifest(file_path, fhash, 0, f"error: {e}")
            return 0

    def _eat_zip(self, zip_path: Path) -> int:
        """Open a zip, eat every text file inside."""
        import zipfile
        total = 0
        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                for name in zf.namelist():
                    ext = Path(name).suffix.lower()
                    if ext not in self.extensions:
                        continue
                    try:
                        content = zf.read(name).decode("utf-8", errors="replace")
                        if len(content) < 50:
                            continue
                        crystals = batch_ingest(
                            content, source=f"{zip_path.name}/{name}",
                            context_hint=self.context_hint,
                        )
                        self.crystals.extend(crystals)
                        total += len(crystals)
                        self._log_manifest(
                            Path(f"{zip_path}/{name}"),
                            hashlib.md5(content[:4096].encode()).hexdigest(),
                            len(crystals), "ingested_from_zip"
                        )
                    except Exception:
                        pass
            self.stats["files_eaten"] += 1
            self.stats["crystals"] = len(self.crystals)
        except Exception as e:
            print(f"    Zip error: {e}")
            self._log_manifest(zip_path, "", 0, f"zip_error: {e}")
        return total

    def _check_folder_done(self, folder: Path):
        """Mark a folder done when all its files have been eaten."""
        folder_str = str(folder)
        if folder_str in self.folders_done:
            return
        try:
            all_files = list(folder.iterdir())
            eligible = [f for f in all_files if f.is_file() and
                       (f.suffix.lower() in self.extensions or f.suffix.lower() == ".zip")]
            if not eligible:
                return
            all_eaten = all(self._file_hash(f) in self.eaten for f in eligible if f.is_file())
            if all_eaten:
                self.folders_done.add(folder_str)
                print(f"  [FOLDER DONE: {folder.name}]")
        except Exception:
            pass

    def run(self):
        """Walk the tree, eat files, sleep between bites."""
        self.running = True
        self.stats["started"] = datetime.now().isoformat()

        # Collect all eligible files + zips, skipping junk directories
        files = []
        for ext in self.extensions | {".zip"}:
            for f in sorted(self.source_dir.rglob(f"*{ext}")):
                # Skip files inside dependency/build directories
                if any(skip in f.parts for skip in self.skip_dirs):
                    continue
                files.append(f)

        # Filter: skip files in done folders, skip already eaten
        uneaten = []
        for f in files:
            # Skip if folder is done
            if str(f.parent) in self.folders_done:
                continue
            try:
                fhash = self._file_hash(f)
                if fhash not in self.eaten:
                    uneaten.append(f)
            except Exception:
                pass

        print(f"Found {len(uneaten)} uneaten files ({len(files)} total)")
        print(f"Interval: {self.interval}s between bites")
        print(f"Press Ctrl+C to stop gracefully\n")

        eaten_this_run = 0
        save_every = 10  # save state every N files

        for i, file_path in enumerate(uneaten):
            if not self.running:
                break

            rel = file_path.relative_to(self.source_dir) if file_path.is_relative_to(self.source_dir) else file_path
            print(f"  [{i+1}/{len(uneaten)}] {rel}", end="", flush=True)

            if file_path.suffix.lower() == ".zip":
                n = self._eat_zip(file_path)
                fhash = self._file_hash(file_path)
                self.eaten.add(fhash)
            else:
                n = self.eat_one(file_path)

            if n > 0:
                print(f" -> {n} crystals (total: {len(self.crystals)})")
                eaten_this_run += 1
            else:
                print(f" -> skip")

            # Check if parent folder is now complete
            self._check_folder_done(file_path.parent)

            # Save periodically
            if eaten_this_run > 0 and eaten_this_run % save_every == 0:
                print(f"  [saving state: {len(self.crystals)} crystals, {len(self.eaten)} files]")
                self._save_state()

            # Rebuild fish every 50 files
            if eaten_this_run > 0 and eaten_this_run % 50 == 0:
                print(f"  [rebuilding fish...]")
                self._rebuild_fish()

            time.sleep(self.interval)

        # Final save
        print(f"\nDone. Ate {eaten_this_run} files this run.")
        print(f"Total: {len(self.crystals)} crystals from {len(self.eaten)} files")
        self._save_state()
        self._rebuild_fish()
        print(f"Fish: {self.fish_path}")


class RoomListener:
    """Listen to the federation room on MQTT. Eat every exchange.

    The fish sits in the room. Minds talk. The codebook grows.
    No intent other than to communicate.

    Subscribes to +/conv/+ (all federation conversations).
    Also listens to federation/wedge/result for compute results.
    """

    def __init__(
        self,
        broker: str = "localhost",
        port: int = 1883,
        fish_name: str = "room",
        state_dir: Optional[Path] = None,
        vocab: dict = None,
    ):
        self.broker = broker
        self.port = port
        self.fish_name = fish_name
        self.running = False

        self.state_dir = Path(state_dir) if state_dir else Path(".")
        self.state_path = self.state_dir / f"{fish_name}.state.json"
        self.crystals_path = self.state_dir / f"{fish_name}.crystals.json"
        self.fish_path = self.state_dir / f"{fish_name}.fish.md"

        self.crystals = []
        self.exchange_count = 0
        self.content_hashes = set()
        self.stats = {"exchanges": 0, "crystals": 0, "started": None, "last_exchange": None}

        if vocab:
            extend_vocabulary(vocab)

        self._load_state()

        signal.signal(signal.SIGINT, self._shutdown)
        signal.signal(signal.SIGTERM, self._shutdown)

    def _load_state(self):
        if self.state_path.exists():
            state = json.loads(self.state_path.read_text(encoding="utf-8"))
            self.content_hashes = set(state.get("content_hashes", []))
            self.stats = state.get("stats", self.stats)
            self.exchange_count = self.stats.get("exchanges", 0)
            print(f"Resumed: {self.exchange_count} exchanges, {len(self.content_hashes)} dedup hashes")

        if self.crystals_path.exists():
            data = json.loads(self.crystals_path.read_text(encoding="utf-8"))
            for cd in data.get("crystals", []):
                self.crystals.append(Crystal(
                    id=cd["id"], ts=cd["ts"], text=cd["text"],
                    source=cd["source"], resonance=cd["resonance"],
                    keywords=cd["keywords"],
                    couplings=[(c, g) for c, g in cd.get("couplings", [])],
                    structural=cd.get("structural", False),
                ))
            print(f"Loaded {len(self.crystals)} existing crystals")

    def _save_state(self):
        state = {
            "content_hashes": list(self.content_hashes)[-10000:],  # cap dedup
            "stats": self.stats,
        }
        self.state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

        crystal_data = [c.to_dict() for c in self.crystals]
        self.crystals_path.write_text(
            json.dumps({"crystals": crystal_data, "count": len(crystal_data)}),
            encoding="utf-8",
        )

    def _rebuild_fish(self):
        if len(self.crystals) < 3:
            return
        recent = self.crystals[-50:] if len(self.crystals) > 50 else self.crystals
        couple_crystals(recent)
        formations = detect_formations(self.crystals)
        if len(formations) > 60:
            formations = hierarchical_merge(formations, target=50)
        codebook = formations_to_codebook_text(
            formations,
            title=f"LiNafish Room: {self.fish_name} ({len(self.crystals)} crystals, {self.exchange_count} exchanges)",
        )
        self.fish_path.write_text(codebook, encoding="utf-8")

    def _shutdown(self, signum, frame):
        print(f"\nRoom listener shutting down...")
        self.running = False

    def _on_message(self, client, userdata, msg):
        """MQTT message handler. Eat the exchange."""
        try:
            topic = msg.topic
            payload = msg.payload.decode("utf-8", errors="replace")

            # Parse: extract sender/receiver from topic
            # Handles +/conv/+, +/fish/+, +/ice9/+
            parts = topic.split("/")
            if len(parts) >= 3 and parts[1] == "conv":
                sender = parts[0]
                receiver = parts[2]
            elif len(parts) >= 2 and parts[1] in ("fish", "ice9"):
                sender = parts[0]
                receiver = "fish"
            else:
                sender = "unknown"
                receiver = "unknown"

            # Skip very short messages but NOT health pulses
            if len(payload) < 30:
                return

            # Health pulses become health crystals (don't skip them)
            is_health = ("pulse" in payload.lower() and "CPU" in payload) or \
                        parts[1] == "fish" or parts[1] == "ice9"
            if is_health:
                # Downsample: only eat health every 10 min (not every 5 min pulse)
                health_key = f"health_{sender}_{datetime.now().strftime('%Y%m%d%H%M')[:11]}0"
                if health_key in self.content_hashes:
                    return
                self.content_hashes.add(health_key)

            # Try to parse JSON envelope
            text = payload
            try:
                data = json.loads(payload)
                if isinstance(data, dict):
                    text = data.get("raw", data.get("text", data.get("body", payload)))
                    if isinstance(text, dict):
                        text = text.get("text", json.dumps(text))
            except (json.JSONDecodeError, TypeError):
                pass

            if len(str(text)) < 30:
                return

            # Content dedup
            content_hash = hashlib.md5(str(text)[:500].encode("utf-8", errors="replace")).hexdigest()
            if content_hash in self.content_hashes:
                return
            self.content_hashes.add(content_hash)

            # Crystallize with source_mind tag for depth perception
            crystal_type = "health" if is_health else "exchange"
            source = f"room://{sender}->{receiver}@{datetime.now().isoformat()[:16]}"
            crystals = batch_ingest(str(text), source=source, context_hint=f"{sender} to {receiver}")
            for c in crystals:
                c.source_mind = sender
                c.crystal_type = crystal_type
            self.crystals.extend(crystals)
            self.exchange_count += 1
            self.stats["exchanges"] = self.exchange_count
            self.stats["crystals"] = len(self.crystals)
            self.stats["last_exchange"] = datetime.now().isoformat()

            msg_len = len(str(text))
            density = len(crystals) / max(msg_len, 1) * 1000  # crystals per 1K chars
            tag = "dense" if density > 3 else "broadcast" if msg_len > 500 else ""
            print(f"  [{sender}->{receiver}] {len(crystals)}c {msg_len}ch {tag} (total: {len(self.crystals)})")

            # Save every 10 exchanges, rebuild every 25
            if self.exchange_count % 10 == 0:
                self._save_state()
            if self.exchange_count % 25 == 0:
                self._rebuild_fish()

        except Exception as e:
            print(f"  [error] {e}")

    def run(self):
        """Subscribe to the room. Eat everything.

        MQTT auth comes from env: LINAFISH_MQTT_USER + LINAFISH_MQTT_PASS.
        If either is unset, the client connects anonymously (works only
        on open brokers). Credentials are NEVER hardcoded in source —
        linafish ships to PyPI and baked-in passwords would leak to every
        install. Private federations should set the env vars in their
        service manager (systemd Environment= / NSSM AppEnvironmentExtra)
        or shell profile.
        """
        try:
            import paho.mqtt.client as mqtt
        except ImportError:
            print("ERROR: pip install paho-mqtt")
            return

        self.running = True
        self.stats["started"] = datetime.now().isoformat()

        # Track CONNACK outcome so we can surface rc=5 rejections before
        # the "Listening..." prose fires. Prior bug: paho's synchronous
        # connect() returns immediately; the CONNACK arrives async, so
        # the listener used to log "Listening on +/conv/+ ..." at an
        # auth-rejected broker and sit there for days ingesting zero.
        _connack = {"rc": None}

        def _on_connect(client, userdata, flags, rc):
            _connack["rc"] = rc
            if rc != 0:
                rc_labels = {
                    1: "unacceptable protocol version",
                    2: "identifier rejected",
                    3: "server unavailable",
                    4: "bad username or password",
                    5: "not authorized",
                }
                print(f"MQTT connect REJECTED: rc={rc} ({rc_labels.get(rc, 'unknown')})")
                self.running = False

        client = mqtt.Client(client_id="linafish-room", protocol=mqtt.MQTTv311)
        client.on_connect = _on_connect
        client.on_message = self._on_message

        mqtt_user = os.environ.get("LINAFISH_MQTT_USER")
        mqtt_pass = os.environ.get("LINAFISH_MQTT_PASS")
        if mqtt_user and mqtt_pass:
            client.username_pw_set(mqtt_user, mqtt_pass)
            print(f"Connecting to room at {self.broker}:{self.port} as {mqtt_user}...")
        else:
            print(f"Connecting to room at {self.broker}:{self.port} (anonymous)...")

        client.connect(self.broker, self.port, keepalive=60)

        # Pump the loop once to let CONNACK arrive before we subscribe.
        # If _on_connect flipped self.running to False, we bail here.
        deadline = time.time() + 5.0
        while _connack["rc"] is None and time.time() < deadline and self.running:
            client.loop(timeout=0.2)
        if not self.running or _connack["rc"] != 0:
            print("Aborting: broker rejected connection.")
            client.disconnect()
            return

        # Subscribe to ALL federation traffic — conversations, health, ice-9, room
        client.subscribe("+/conv/+", qos=0)      # mind-to-mind conversation
        client.subscribe("+/fish/+", qos=0)      # health/state from fish_awareness
        client.subscribe("+/ice9/+", qos=0)      # crystallizer output
        client.subscribe("room/#", qos=0)        # shared room
        client.subscribe("federation/wedge/result", qos=0)  # compute results
        print(f"Listening on +/conv/+ +/fish/+ +/ice9/+ room/# federation/wedge/result")
        print(f"The fish is in the room. Press Ctrl+C to leave.\n")

        while self.running:
            client.loop(timeout=1.0)

        client.disconnect()
        self._save_state()
        self._rebuild_fish()
        print(f"Left the room. {self.exchange_count} exchanges, {len(self.crystals)} crystals.")
