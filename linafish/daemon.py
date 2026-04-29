"""
Daemon — listen to the federation room. Eat every exchange.

Single entry point:
  linafish room --broker <host> --port <port>

Subscribe to federation MQTT topics (+/conv/+, +/fish/+, +/ice9/+,
room/#, federation/wedge/result) and crystallize each exchange into
a FishEngine-backed fish. The listener becomes a silent participant
in the room; the fish learns.

This module was previously ~638 lines of v1 crystallizer code including
a dead FishDaemon class and a RoomListener that called
batch_ingest/couple_crystals/extend_vocabulary/Crystal directly. The
fork sunset rewrites RoomListener to drive FishEngine (v3) — one
engine, one eat path, one persistence layer. The dead FishDaemon
class is deleted; it was defined but never instantiated anywhere in
the package.

Legacy state migration: on first startup, if {fish_name}.crystals.json
(v1 format) exists in the state_dir and no v3 crystals have loaded,
re-feed each legacy text through FishEngine.eat() to reproduce the
content under v3. Legacy files are renamed with a .legacy suffix so
the migration is idempotent.

State files under v3:
  {state_dir}/{fish_name}_crystals.jsonl     — FishEngine crystals
  {state_dir}/{fish_name}_v3_state.json      — FishEngine state
  {state_dir}/mi_vectorizer.json             — shared vectorizer
  {state_dir}/{fish_name}.fish.md            — FishEngine rebuild
  {state_dir}/{fish_name}.listener.json      — listener-side dedup + stats

Listener sidecar (dedup hashes, exchange count, timestamps) stays
separate from FishEngine state because it's MQTT-protocol state, not
cognitive state. Saved every 10 exchanges alongside engine._save_state.
"""

import json
import os
import time
import signal
import hashlib
import traceback
from pathlib import Path
from typing import Optional
from datetime import datetime

from .engine import FishEngine
from ._dedup_helpers import normalize_for_dedup


def _listener_content_hash(text: str) -> str:
    """Compute the listener plate-dedup hash for a given text.

    Truncates to first 500 chars, then normalizes (strips
    `[timestamp source]\\n` prefix line, lowercases, collapses
    whitespace), then MD5-hashes. This is the canonical listener-
    side dedup key — exposed so tests can assert behavior without
    reimplementing the logic.

    Used by ``RoomListener._on_message`` for inbound MQTT message
    rate-limiting. NOT a storage-layer dedup; see ``_dedup_helpers``
    docstring for the layered-architecture rationale.
    """
    return hashlib.md5(
        normalize_for_dedup(str(text)[:500]).encode("utf-8", errors="replace")
    ).hexdigest()


class RoomListener:
    """Listen to the federation room on MQTT. Crystallize every exchange.

    The fish sits in the room. Minds talk. The codebook grows through
    FishEngine.eat() — no intent other than to communicate.

    Subscribes to +/conv/+ (all federation conversations), +/fish/+
    (health pulses), +/ice9/+ (crystallizer output), room/# (shared
    room), and federation/wedge/result (compute results).
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

        # Resolve state_dir to an absolute path before anything else
        # touches it — FishEngine's crystallizer expects its
        # crystal_log_path to have a non-empty directory component, which
        # fails when state_dir is a bare "." relative path on Windows.
        # Resolving defensively here means callers that pass a relative
        # state_dir still get correct behavior.
        self.state_dir = (Path(state_dir) if state_dir else Path(".")).resolve()
        self.state_dir.mkdir(parents=True, exist_ok=True)

        # FishEngine owns crystallization + coupling + vocab + fish.md.
        # git_autocommit=False because room listener fires on every MQTT
        # message and we don't want a git commit per room turn — the
        # crystals file is the durable record; git history is noise.
        # dedupe=True because migration is safe to re-run: if a previous
        # migration crashed partway, re-ingesting legacy texts will
        # skip any already-crystallized content by text hash (plate
        # item 12). The same dedupe also kills the narrow race where
        # the MQTT-level content_hash set is lost but an identical
        # message arrives twice; the engine catches it on the second
        # pass.
        self.engine = FishEngine(
            state_dir=self.state_dir,
            name=fish_name,
            git_autocommit=False,
            dedupe=True,
        )

        # Listener-side state lives in a sidecar separate from engine
        # state. Holds dedup hashes (content + health) and MQTT exchange
        # bookkeeping. Keeping it separate means migrating engine state
        # and migrating listener state can be reasoned about independently.
        self.sidecar_path = self.state_dir / f"{fish_name}.listener.json"
        self.content_hashes = set()
        self.exchange_count = 0
        self.stats = {
            "exchanges": 0,
            "crystals": len(self.engine.crystals),
            "started": None,
            "last_exchange": None,
        }

        # `vocab` arg is preserved for CLI compatibility but ignored under
        # v3 — MIVectorizer learns its own vocabulary from the corpus.
        # Old callers that passed --vocab get a warning, not a crash.
        if vocab:
            print(
                "WARNING: --vocab is a no-op under v3 "
                "(MIVectorizer learns vocabulary from corpus)"
            )

        self._load_sidecar()
        self._migrate_legacy_if_needed()

        signal.signal(signal.SIGINT, self._shutdown)
        signal.signal(signal.SIGTERM, self._shutdown)

    # -- persistence ----------------------------------------------------

    def _load_sidecar(self):
        """Read dedup hashes + stats from the listener sidecar."""
        if not self.sidecar_path.exists():
            return
        try:
            state = json.loads(self.sidecar_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError) as e:
            print(f"WARNING: sidecar read failed ({e}); starting fresh")
            return
        if not isinstance(state, dict):
            return
        hashes = state.get("content_hashes")
        if isinstance(hashes, list):
            self.content_hashes = set(hashes)
        stored_stats = state.get("stats")
        if isinstance(stored_stats, dict):
            self.stats.update(stored_stats)
        self.exchange_count = self.stats.get("exchanges", 0)
        if self.exchange_count or self.content_hashes:
            print(
                f"Resumed: {self.exchange_count} exchanges, "
                f"{len(self.content_hashes)} dedup hashes"
            )

    def _save_sidecar(self):
        """Write dedup hashes (capped) + stats atomically.

        Cap at 10000 entries to keep the file bounded — older hashes
        age out. The cap matches the pre-rewrite behavior; rationale
        preserved.
        """
        payload = {
            "content_hashes": list(self.content_hashes)[-10000:],
            "stats": self.stats,
        }
        tmp_path = self.sidecar_path.with_suffix(
            self.sidecar_path.suffix + ".tmp"
        )
        try:
            tmp_path.write_text(
                json.dumps(payload, indent=2), encoding="utf-8"
            )
            os.replace(tmp_path, self.sidecar_path)
        except OSError as e:
            print(f"WARNING: sidecar save failed ({e})")
            try:
                tmp_path.unlink()
            except OSError:
                pass

    def _migrate_legacy_if_needed(self):
        """Re-feed v1 room.crystals.json texts into FishEngine on first boot.

        Guarded by ``migration_done_at`` in the sidecar: once that field
        is set, migration never re-runs. Before that field is set, a
        legacy file on disk is treated as not-yet-migrated even if the
        engine already has crystals (survives a crash mid-migration).
        Repeat runs are safe because the engine is initialized with
        ``dedupe=True`` — re-ingesting the same text returns the
        already-crystallized entry instead of duplicating.

        Preserves content, not crystal identity — new v3 crystals get
        fresh IDs but retain the same text + a ``legacy:`` source tag.
        """
        if self.stats.get("migration_done_at"):
            return
        legacy_crystals = self.state_dir / f"{self.fish_name}.crystals.json"
        legacy_state = self.state_dir / f"{self.fish_name}.state.json"
        if not legacy_crystals.exists():
            # No legacy content to migrate — mark done so we never revisit.
            self.stats["migration_done_at"] = datetime.now().isoformat()
            return

        print(f"Migrating legacy room state: {legacy_crystals.name}")
        try:
            data = json.loads(legacy_crystals.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError) as e:
            print(f"  migration aborted: legacy crystals unreadable ({e})")
            return

        migrated = 0
        skipped_dup = 0
        pre_count = len(self.engine.crystals)
        for cd in data.get("crystals", []):
            text = cd.get("text")
            if not isinstance(text, str) or len(text) < 30:
                continue
            legacy_source = cd.get("source", "legacy")
            result = self.engine.eat(text, source=f"legacy:{legacy_source}")
            if isinstance(result, dict) and result.get("crystals_added") == 0:
                skipped_dup += 1
            else:
                migrated += 1
        post_count = len(self.engine.crystals)

        print(
            f"  migrated {migrated} crystals "
            f"({skipped_dup} skipped as duplicates, "
            f"engine grew from {pre_count} to {post_count})"
        )

        # Pull dedup hashes forward if the legacy sidecar state had them.
        # This prevents an immediate re-eat of any live message whose
        # hash was already seen pre-migration.
        if legacy_state.exists():
            try:
                lstate = json.loads(legacy_state.read_text(encoding="utf-8"))
                if isinstance(lstate, dict):
                    lhashes = lstate.get("content_hashes")
                    if isinstance(lhashes, list):
                        self.content_hashes |= set(lhashes)
                    lstats = lstate.get("stats")
                    if isinstance(lstats, dict):
                        self.exchange_count = lstats.get(
                            "exchanges", self.exchange_count
                        )
                        self.stats["exchanges"] = self.exchange_count
            except (OSError, json.JSONDecodeError, UnicodeDecodeError):
                pass

        # Archive legacy files so the next boot skips the re-read entirely
        # (the migration_done flag is the durable guard; rename is the
        # "and we don't even need to open the file again" optimization).
        try:
            legacy_crystals.rename(
                legacy_crystals.with_suffix(".json.legacy")
            )
            if legacy_state.exists():
                legacy_state.rename(
                    legacy_state.with_suffix(".json.legacy")
                )
        except OSError as e:
            print(f"  WARNING: legacy archive failed ({e})")

        # Mark migration complete AFTER the ingest + archive — the flag
        # is the single source of truth for "don't run migration again."
        self.stats["migration_done_at"] = datetime.now().isoformat()

        # Persist the post-migration engine state + sidecar immediately
        # so a crash mid-first-run doesn't lose the flag or the crystals.
        self.engine._save_state()
        self._save_sidecar()

    # -- signal + MQTT handlers -----------------------------------------

    def _shutdown(self, signum, frame):
        print("\nRoom listener shutting down...")
        self.running = False

    def _on_message(self, client, userdata, msg):
        """MQTT message handler. Feed the exchange into FishEngine."""
        try:
            topic = msg.topic
            payload = msg.payload.decode("utf-8", errors="replace")

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

            if len(payload) < 30:
                return

            is_health = (
                ("pulse" in payload.lower() and "CPU" in payload)
                or (len(parts) >= 2 and parts[1] in ("fish", "ice9"))
            )
            if is_health:
                # Downsample health traffic to one crystal per sender per
                # 10-minute bucket — the raw 5-min pulse cadence would
                # drown the fish in structural noise.
                bucket = datetime.now().strftime("%Y%m%d%H%M")[:11] + "0"
                health_key = f"health_{sender}_{bucket}"
                if health_key in self.content_hashes:
                    return
                self.content_hashes.add(health_key)

            # Unwrap a common JSON envelope used by federation bridges:
            # {"raw": "...", "text": "...", "body": "..."} in any order.
            text = payload
            try:
                data = json.loads(payload)
                if isinstance(data, dict):
                    text = data.get(
                        "raw", data.get("text", data.get("body", payload))
                    )
                    if isinstance(text, dict):
                        text = text.get("text", json.dumps(text))
            except (json.JSONDecodeError, TypeError):
                pass

            if len(str(text)) < 30:
                return

            # Listener plate-dedup. The listener's stated intent (per
            # `dedupe=True` on the FishEngine init at line 99 and the
            # docstring "skip any already-crystallized content by text
            # hash") is to rate-limit MQTT bridge near-duplicates.
            # Pre-fix behavior hashed raw text including the per-message
            # timestamp prefix; broadcasts hashed uniquely and bypassed
            # dedup. Empirical against me-fish 2026-04-28: 10,135 ALL
            # MINDS broadcasts → 23 normalized hashes (440x compression).
            # Engine-side ``_content_hash`` stays byte-exact; that's a
            # different layer with different opt-in semantics. See
            # ``_listener_content_hash`` (above) for the canonical
            # implementation; tests share it to avoid drift.
            content_hash = _listener_content_hash(text)
            if content_hash in self.content_hashes:
                return
            self.content_hashes.add(content_hash)

            # Source format uses colon-prefix so downstream /taste filters
            # (e.g. source_prefix="olorin:") pick up cleanly. receiver +
            # timestamp preserved as tail segments for audit.
            source = (
                f"{sender}:room->{receiver}@"
                f"{datetime.now().isoformat()[:16]}"
            )
            self.engine.eat(str(text), source=source)

            self.exchange_count += 1
            self.stats["exchanges"] = self.exchange_count
            self.stats["crystals"] = len(self.engine.crystals)
            self.stats["last_exchange"] = datetime.now().isoformat()

            msg_len = len(str(text))
            tag = "health" if is_health else "broadcast" if msg_len > 500 else ""
            print(
                f"  [{sender}->{receiver}] {msg_len}ch {tag} "
                f"(total crystals: {len(self.engine.crystals)})"
            )

            # Cadence matches pre-rewrite: save every 10 exchanges. The
            # engine rebuilds fish.md internally during _save_state so no
            # separate rebuild cadence is needed.
            if self.exchange_count % 10 == 0:
                self.engine._save_state()
                self._save_sidecar()

        except Exception:
            # Print the full traceback so that a bug in message parsing
            # or crystallization is debuggable — prior versions swallowed
            # the exception with just `print(e)` which hid stack frames
            # and silent-failed under real traffic. Returning (not
            # raising) keeps the listener loop alive through individual
            # bad messages; the daemon should only exit on shutdown or
            # broker rejection.
            traceback.print_exc()

    # -- main loop ------------------------------------------------------

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
                print(
                    f"MQTT connect REJECTED: rc={rc} "
                    f"({rc_labels.get(rc, 'unknown')})"
                )
                self.running = False

        client = mqtt.Client(
            client_id="linafish-room", protocol=mqtt.MQTTv311
        )
        client.on_connect = _on_connect
        client.on_message = self._on_message

        mqtt_user = os.environ.get("LINAFISH_MQTT_USER")
        mqtt_pass = os.environ.get("LINAFISH_MQTT_PASS")
        if mqtt_user and mqtt_pass:
            client.username_pw_set(mqtt_user, mqtt_pass)
            print(
                f"Connecting to room at {self.broker}:{self.port} "
                f"as {mqtt_user}..."
            )
        else:
            print(
                f"Connecting to room at {self.broker}:{self.port} "
                f"(anonymous)..."
            )

        client.connect(self.broker, self.port, keepalive=60)

        # Pump the loop once to let CONNACK arrive before we subscribe.
        # If _on_connect flipped self.running to False, we bail here.
        deadline = time.time() + 5.0
        while (
            _connack["rc"] is None
            and time.time() < deadline
            and self.running
        ):
            client.loop(timeout=0.2)
        if not self.running or _connack["rc"] != 0:
            print("Aborting: broker rejected connection.")
            client.disconnect()
            return

        # Subscribe to all federation traffic — conversations, health,
        # ice-9, room-scoped topics, and wedge compute results.
        client.subscribe("+/conv/+", qos=0)
        client.subscribe("+/fish/+", qos=0)
        client.subscribe("+/ice9/+", qos=0)
        client.subscribe("room/#", qos=0)
        client.subscribe("federation/wedge/result", qos=0)
        print(
            "Listening on +/conv/+ +/fish/+ +/ice9/+ "
            "room/# federation/wedge/result"
        )
        print("The fish is in the room. Press Ctrl+C to leave.\n")

        while self.running:
            client.loop(timeout=1.0)

        client.disconnect()
        self.engine._save_state()
        self._save_sidecar()
        print(
            f"Left the room. {self.exchange_count} exchanges, "
            f"{len(self.engine.crystals)} crystals."
        )
