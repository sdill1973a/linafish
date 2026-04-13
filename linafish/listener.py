"""
LiNafish Listener — Ambient cognition.

The fish sits in the stream. What couples stays. What doesn't washes past.

Sources:
  mqtt://host:port/topic — subscribe to MQTT broker
  folder:/path            — watch directory for changes
  stdin                   — pipe text in

All sources feed FishEngine.eat(). Git commits after each cycle.
Formation changes printed to stdout.
"""

import hashlib
import json
import os
import signal
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional


class FishListener:
    """Unified listener. Feeds any source through FishEngine or School."""

    def __init__(self, engine, min_length: int = 30, dedup_cap: int = 10000,
                 school=None):
        self.engine = engine
        self.school = school  # When set, feed through school instead of engine
        self.min_length = min_length
        self.running = False
        self._content_hashes = set()
        self._dedup_cap = dedup_cap
        self._prev_formations = set()
        self._exchange_count = 0

        # Track formation names for change detection
        if self.engine.formations:
            self._prev_formations = {f.name for f in self.engine.formations}

        signal.signal(signal.SIGINT, self._shutdown)
        signal.signal(signal.SIGTERM, self._shutdown)

    def _shutdown(self, signum=None, frame=None):
        print(f"\nListener shutting down... ({self._exchange_count} exchanges)")
        self.running = False

    def _is_duplicate(self, text: str) -> bool:
        h = hashlib.md5(text[:500].encode("utf-8", errors="replace")).hexdigest()
        if h in self._content_hashes:
            return True
        self._content_hashes.add(h)
        if len(self._content_hashes) > self._dedup_cap:
            # Trim oldest (sets don't preserve order, so just clear half)
            self._content_hashes = set(list(self._content_hashes)[self._dedup_cap // 2:])
        return False

    def _extract_text(self, payload: str) -> str:
        """Extract text from raw payload (may be JSON envelope)."""
        try:
            data = json.loads(payload)
            if isinstance(data, dict):
                text = data.get("raw", data.get("text", data.get("body", payload)))
                if isinstance(text, dict):
                    text = text.get("text", json.dumps(text))
                return str(text)
        except (json.JSONDecodeError, TypeError):
            pass
        return payload

    def _check_formation_changes(self):
        """Print new or lost formations."""
        current = {f.name for f in self.engine.formations}
        new = current - self._prev_formations
        lost = self._prev_formations - current
        for name in new:
            print(f"  + New formation: {name}")
        for name in lost:
            print(f"  - Formation dissolved: {name}")
        self._prev_formations = current

    def feed(self, text: str, source: str = "listen"):
        """Feed one text through the engine (or school if set)."""
        text = self._extract_text(text)
        if len(text) < self.min_length:
            return
        if self._is_duplicate(text):
            return

        self._exchange_count += 1

        if self.school:
            # School mode: feed all members
            result = self.school.eat(text, source=source)
            central_added = result.get("central", {}).get("crystals_added", 0)
            member_grabs = [
                name for name, mr in result.get("members", {}).items()
                if mr.get("crystals_added", 0) > 0
            ]
            if central_added > 0:
                grab_str = f" [{', '.join(member_grabs)}]" if member_grabs else ""
                print(f"  [{source}] +{central_added}c{grab_str}")
                self._check_formation_changes()
        else:
            # Single engine mode (original behavior)
            result = self.engine.eat(text, source=source)
            added = result.get("crystals_added", 0)
            total = result.get("total_crystals", 0)
            fcount = result.get("formations", 0)
            if added > 0:
                print(f"  [{source}] +{added}c (total: {total}c {fcount}f)")
                self._check_formation_changes()

    # -------------------------------------------------------------------
    # SOURCE: MQTT
    # -------------------------------------------------------------------

    def listen_mqtt(self, broker: str, port: int = 1883, topics: str = "+/conv/+",
                    username: str = None, password: str = None):
        """Subscribe to MQTT and eat every message.

        s95 2026-04-13: added username/password support so authenticated
        brokers (port 1884 on .67) can be subscribed to. Called with the
        parsed user:pass@ embedded in the mqtt:// URL from __main__.py.
        """
        try:
            import paho.mqtt.client as mqtt
        except ImportError:
            print("MQTT source requires paho-mqtt: pip install paho-mqtt")
            return

        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                for topic in topics.split(","):
                    client.subscribe(topic.strip())
                    print(f"  Subscribed: {topic.strip()}")
            else:
                print(f"  MQTT connect failed: rc={rc}")

        def on_message(client, userdata, msg):
            topic = msg.topic
            payload = msg.payload.decode("utf-8", errors="replace")
            # Extract sender from topic
            parts = topic.split("/")
            sender = parts[0] if len(parts) >= 1 else "unknown"
            channel = parts[1] if len(parts) >= 2 else "unknown"
            source = f"mqtt://{sender}/{channel}"
            self.feed(payload, source=source)

        client = mqtt.Client(client_id=f"linafish-{self.engine.name}", clean_session=True)
        client.on_connect = on_connect
        client.on_message = on_message
        if username is not None:
            client.username_pw_set(username, password)

        auth_note = f" (auth: {username})" if username else ""
        print(f"Connecting to {broker}:{port}{auth_note}...")
        try:
            client.connect(broker, port, 60)
        except Exception as e:
            print(f"MQTT connection failed: {e}")
            return

        self.running = True
        print(f"Listening on MQTT. The fish sits in the stream.")
        print(f"Ctrl+C to stop.\n")

        client.loop_start()
        try:
            while self.running:
                time.sleep(1)
        finally:
            client.loop_stop()
            client.disconnect()

    # -------------------------------------------------------------------
    # SOURCE: FOLDER
    # -------------------------------------------------------------------

    def listen_folder(self, path: str, interval: int = 30):
        """Watch a directory. Eat new or changed files."""
        folder = Path(path).expanduser().resolve()
        if not folder.is_dir():
            print(f"Not a directory: {folder}")
            return

        SKIP_DIRS = {'.git', '__pycache__', 'node_modules', '.venv', 'venv', '.linafish'}
        EXTENSIONS = {'.txt', '.md', '.py', '.json', '.csv', '.log', '.rst', '.yaml', '.yml', '.toml'}

        # Track file modification times
        seen = {}
        for f in folder.rglob("*"):
            if f.is_file() and f.suffix in EXTENSIONS and not any(p in f.parts for p in SKIP_DIRS):
                seen[str(f)] = f.stat().st_mtime

        self.running = True
        print(f"Watching: {folder} (checking every {interval}s)")
        print(f"Tracking {len(seen)} files. The fish eats what changes.")
        print(f"Ctrl+C to stop.\n")

        while self.running:
            time.sleep(interval)
            if not self.running:
                break

            for f in folder.rglob("*"):
                if not f.is_file() or f.suffix not in EXTENSIONS:
                    continue
                if any(p in f.parts for p in SKIP_DIRS):
                    continue

                fstr = str(f)
                mtime = f.stat().st_mtime
                if fstr not in seen or mtime > seen[fstr]:
                    seen[fstr] = mtime
                    try:
                        text = f.read_text(encoding="utf-8", errors="replace")
                        if len(text) >= self.min_length:
                            source = f"folder://{f.relative_to(folder)}"
                            self.feed(text, source=source)
                    except Exception as e:
                        print(f"  Error reading {f.name}: {e}")

    # -------------------------------------------------------------------
    # SOURCE: STDIN
    # -------------------------------------------------------------------

    def listen_stdin(self):
        """Read from stdin. Each line or paragraph is eaten."""
        self.running = True
        print("Reading from stdin. The fish eats what flows through.")
        print("Ctrl+D (or Ctrl+Z on Windows) to stop.\n")

        buffer = []
        try:
            for line in sys.stdin:
                if not self.running:
                    break
                line = line.rstrip("\n")
                if line:
                    buffer.append(line)
                else:
                    # Empty line = paragraph break, feed buffer
                    if buffer:
                        text = "\n".join(buffer)
                        self.feed(text, source="stdin")
                        buffer = []

            # Feed remaining buffer
            if buffer:
                text = "\n".join(buffer)
                self.feed(text, source="stdin")

        except (EOFError, KeyboardInterrupt):
            if buffer:
                text = "\n".join(buffer)
                self.feed(text, source="stdin")

        print(f"Stdin closed. {self._exchange_count} exchanges.")
