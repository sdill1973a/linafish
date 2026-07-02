"""Eat-latency root-fix — decouple per-eat durability from full O(N) save.

Root cause (runbook fish_engine_eat_latency_root_fix_2026-06-20): every
``eat()`` triggered a full ``_save_state()`` that re-serializes the entire
corpus into fish.md — O(N) in corpus size, ~2s on a 454K-crystal room.
Under burst from multiple schedulers this serialized past n8n's 10s timeout.

The fix: crystals stay durable via the append-only JSONL (``_persist_crystal``,
already per-eat); the expensive full ``_save_state`` is gated behind
``save_state_every_n_eats`` (default 1 = legacy behavior) and a public
``flush()`` for daemons (background timer + shutdown). A writer lock
serializes concurrent eats.

These tests assert:
  1. default behavior unchanged (saves every eat)
  2. gated save defers the O(N) fish.md write while keeping crystals durable
  3. crystals survive a "crash" (no flush) — loaded from JSONL on reopen
  4. flush() forces the deferred save
  5. concurrent eats don't corrupt state (writer lock)
"""

import json
import re
import threading
from pathlib import Path

from linafish.engine import FishEngine

SAMPLE = ("This is a sufficiently long sample passage number {} written so the "
          "crystallizer has real text to chew on and will emit a crystal.")


def _jsonl_count(engine) -> int:
    p = Path(engine.fish.crystal_log_path)
    if not p.exists():
        return 0
    with p.open(encoding="utf-8", errors="replace") as f:
        return sum(1 for line in f if line.strip())


def _fishmd_crystal_count(engine):
    """Parse crystal_count from the fish.md FISH_STATE footer, or None if
    the fish.md has not been written yet."""
    if not engine.fish_file.exists():
        return None
    txt = engine.fish_file.read_text(encoding="utf-8")
    m = re.search(r"FISH_STATE.*?<!--\s*(\{.*?\})\s*-->", txt, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(1)).get("crystal_count")
    except json.JSONDecodeError:
        return None


def test_default_saves_every_eat(tmp_path):
    """Backward compatibility: with no knob, fish.md reflects each eat
    immediately (legacy behavior)."""
    e = FishEngine(state_dir=tmp_path, name="t", git_autocommit=False)
    e.eat(SAMPLE.format(1))
    assert _jsonl_count(e) == 1
    assert _fishmd_crystal_count(e) == 1


def test_gated_save_defers_fishmd(tmp_path):
    """With save_state_every_n_eats=5, the first four eats are durable in
    JSONL but the O(N) fish.md write is deferred until the fifth."""
    e = FishEngine(state_dir=tmp_path, name="t", git_autocommit=False,
                   save_state_every_n_eats=5)
    for i in range(4):
        e.eat(SAMPLE.format(i))
    assert _jsonl_count(e) == 4                 # durable
    assert _fishmd_crystal_count(e) in (None, 0)  # fish.md not yet rewritten
    e.eat(SAMPLE.format(99))                    # fifth eat triggers the save
    assert _fishmd_crystal_count(e) == 5


def test_durability_without_flush(tmp_path):
    """Simulated crash: gated saves, no flush, no clean shutdown — a fresh
    engine on the same state dir recovers every crystal from the JSONL."""
    e = FishEngine(state_dir=tmp_path, name="t", git_autocommit=False,
                   save_state_every_n_eats=100)
    for i in range(7):
        e.eat(SAMPLE.format(i))
    assert _jsonl_count(e) == 7
    # No flush — drop the engine and reopen (cold load).
    e2 = FishEngine(state_dir=tmp_path, name="t", git_autocommit=False)
    assert len(e2.fish.crystals) == 7


def test_flush_forces_save(tmp_path):
    """flush() forces the deferred full save (for daemon timer/shutdown)."""
    e = FishEngine(state_dir=tmp_path, name="t", git_autocommit=False,
                   save_state_every_n_eats=100)
    for i in range(3):
        e.eat(SAMPLE.format(i))
    assert _fishmd_crystal_count(e) in (None, 0)
    e.flush()
    assert _fishmd_crystal_count(e) == 3


def test_flush_noop_when_nothing_pending(tmp_path):
    """flush() with no un-saved eats does not error and does not regress
    a previously-written fish.md."""
    e = FishEngine(state_dir=tmp_path, name="t", git_autocommit=False,
                   save_state_every_n_eats=100)
    e.eat(SAMPLE.format(1))
    e.flush()
    assert _fishmd_crystal_count(e) == 1
    e.flush()  # nothing pending — must be a clean no-op
    assert _fishmd_crystal_count(e) == 1


def test_concurrent_eats_no_corruption(tmp_path):
    """The writer lock serializes concurrent eats: 20 distinct texts from
    20 threads all crystallize, none raise, and all are durable."""
    e = FishEngine(state_dir=tmp_path, name="t", git_autocommit=False,
                   save_state_every_n_eats=100)
    errors = []

    def worker(n):
        try:
            e.eat(SAMPLE.format(n) + " distinct-marker-" + ("z" * (n + 1)))
        except Exception as ex:  # noqa: BLE001 — test captures any failure
            errors.append(ex)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"concurrent eats raised: {errors}"
    e.flush()
    assert _jsonl_count(e) == 20
    e2 = FishEngine(state_dir=tmp_path, name="t", git_autocommit=False)
    assert len(e2.fish.crystals) == 20
