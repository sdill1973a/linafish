#!/usr/bin/env python3
"""notify_coherence.py — one canonical model for "what needs my attention."

A portable recipe, NOT engine code. Offered peer-to-peer for minds that run a
notification surface (a hook that summarizes inbox/queue state into context).
Adapt the paths, identities, and source-of-truth to YOUR build — the value is
the *shape*, not this file.

----------------------------------------------------------------------------
THE BUG-SHAPE (does it bite your build?)
----------------------------------------------------------------------------
You have TWO (or more) places that describe the SAME state from INDEPENDENT
reads — e.g. a queue you append to, and a live API query — and they drift:
something you've already handled still shows as "unhandled/unread" because the
two reads don't share a source of truth. Three quick self-checks:

  1. Does any "needs attention" flag get SET to done anywhere? (Grep it. Ours
     was written false on every append and never once flipped — dead
     infrastructure that LOOKED like it did something.)
  2. Do two surfaces query the same state by different means / different
     filters? (Ours used different noise filters, so one leaked what the other
     suppressed.)
  3. Does your self-test check the data model, or the artifact the USER SEES?
     (Ours said "0 unhandled" while the rendered summary still showed 5. The
     model was "fixed"; the screen was not.)

----------------------------------------------------------------------------
THE SHAPE OF THE FIX
----------------------------------------------------------------------------
  * ONE canonical model (a queue + a disposition field) is the source of truth.
  * Every surface imports the SAME functions, so they cannot drift by
    construction — not "deduped after the fact," structurally unable to differ.
  * The live read becomes a RECONCILER that double-checks the canonical state,
    keyed on a stable id (we use thread_id). Redundant verification on one
    truth — "doubled, not pointed two different places."
  * CLOSE THE LOOP two ways: auto-detect resolution (auto_close) AND a manual
    mark for out-of-band handling — because real work gets resolved on channels
    your auto-detector can't see.
  * Disposition is a SUB-STATE, not a bool: resolved / routed / not-mine /
    noise — so dedup never silently buries a genuinely-open loop.

Configure these for your substrate (env or edit):
"""

import contextlib
import fcntl
import json
import os
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

# --- adapt to your build -----------------------------------------------------
QUEUE_FILE = Path(os.environ.get("NOTIFY_QUEUE", "state/attention_queue.jsonl"))
_LOCK_FILE = Path(os.environ.get("NOTIFY_LOCK", "state/attention_queue.lock"))
# Your own sending identities — used to detect "we already replied".
OUR_IDENTITIES = tuple(
    s.strip() for s in os.environ.get(
        "NOTIFY_IDENTITIES", "me@example.org,alias@example.org").split(",")
    if s.strip()
)
# -----------------------------------------------------------------------------

DISPOSITIONS = ("resolved", "routed", "not-mine", "noise")


@contextlib.contextmanager
def _locked():
    """Exclusive lock for any read-modify-write or append on the queue.

    The producer appends while a consumer rewrites the whole file; without a
    shared lock a rewrite that straddles an append silently drops the appended
    entry (lost update). Every mutator takes this lock, so they serialize.
    """
    _LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(_LOCK_FILE), os.O_CREAT | os.O_RDWR, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def _atomic_write(entries: list) -> None:
    """Write the full queue atomically (temp + os.replace) so a concurrent
    reader never sees a half-written file. Call only while holding _locked()."""
    QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
    data = "\n".join(json.dumps(e) for e in entries) + "\n"
    fd, tmp = tempfile.mkstemp(dir=str(QUEUE_FILE.parent), prefix=".aq-")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(data)
        os.replace(tmp, QUEUE_FILE)
    except Exception:
        with contextlib.suppress(Exception):
            os.unlink(tmp)
        raise


def load_queue() -> list:
    """All queue entries, oldest-first. Tolerant of malformed lines."""
    if not QUEUE_FILE.exists():
        return []
    out = []
    for line in QUEUE_FILE.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except Exception:
            continue
    return out


def append(entry: dict) -> None:
    """Lock-guarded append — the ONE writer entrypoint for new entries, so
    appends serialize with rewrites."""
    with _locked():
        with QUEUE_FILE.open("a") as f:
            f.write(json.dumps(entry) + "\n")


def is_dispositioned(entry: dict) -> bool:
    """True if acted on / set aside (any truthy `handled`)."""
    return bool(entry.get("handled"))


def _within_age(entry: dict, hours) -> bool:
    if hours is None:
        return True
    try:
        ts = datetime.fromisoformat(entry["ts"].replace("Z", "+00:00"))
    except Exception:
        return False  # undatable -> out-of-window (don't nag forever)
    return (datetime.now(timezone.utc) - ts) <= timedelta(hours=hours)


def attention_items(within_hours=24) -> list:
    """THE canonical list: open (un-dispositioned) entries within age. Every
    surface calls this, so they agree by construction."""
    return [e for e in load_queue()
            if not is_dispositioned(e) and _within_age(e, within_hours)]


def reconcile_live(live_keys: dict, within_hours=24) -> dict:
    """Double-check the canonical list against a live read.

    `live_keys`: {stable_id: {...meta...}} of currently-live items (e.g. unread
    threads). Returns three buckets, keyed on id (never two divergent lists):
      open       — open queue items (the canonical attention list)
      unqueued   — live items not yet in the queue (producer lag / wider net)
      suppressed — live items in the queue but dispositioned (the phantom-killer)
    """
    by_id = {}
    for e in load_queue():
        k = e.get("key")
        if k:
            by_id[k] = e
    open_items = [{**e, "_also_live": e.get("key") in live_keys}
                  for e in attention_items(within_hours)]
    unqueued, suppressed = [], []
    for k, meta in live_keys.items():
        if not k:
            continue
        e = by_id.get(k)
        if e is None:
            unqueued.append({"key": k, **meta})
        elif is_dispositioned(e):
            suppressed.append({"key": k, "disposition": e.get("handled"), **meta})
    return {"open": open_items, "unqueued": unqueued, "suppressed": suppressed}


def mark_handled(match: str, disposition: str = "resolved", note: str = "",
                 by: str = "manual") -> int:
    """Set disposition on every OPEN entry whose `key` or `subject` matches.
    This is how the loop CLOSES for out-of-band resolution — call it after
    handling something by any channel. Returns count marked."""
    if disposition not in DISPOSITIONS:
        disposition = disposition or "resolved"
    with _locked():
        entries = load_queue()
        n = 0
        for e in entries:
            if is_dispositioned(e):
                continue
            if match == e.get("key") or \
                    match.lower() in (e.get("subject", "") or "").lower():
                e["handled"] = disposition
                e["handled_by"] = by
                if note:
                    e["handled_note"] = note
                n += 1
        if n:
            _atomic_write(entries)
    return n


def auto_close(fetch_thread, within_hours: int = 168) -> int:
    """Auto-resolve OPEN entries where OUR latest reply is newer than the
    latest REAL inbound in the thread (drafts/headerless ignored).

    `fetch_thread(key) -> list[{"from": str, "ts": int}]` is YOUR adapter to
    your message store (return the thread's messages). Decoupled from any
    specific API so it ports anywhere.

    The rule matters: "any reply from us" wrongly resolves a re-ask (they
    replied after us); "latest message is us" wrongly trips on a trailing
    draft with no sender. Correct = our-latest >= latest-real-inbound.
    """
    candidates = [e for e in load_queue()
                  if not is_dispositioned(e)
                  and _within_age(e, within_hours) and e.get("key")]
    resolved = set()
    for e in candidates:
        try:
            msgs = fetch_thread(e["key"]) or []
        except Exception:
            continue
        latest_ours = latest_inbound = -1
        for m in msgs:
            frm = (m.get("from") or "").strip().lower()
            if not frm:
                continue  # draft / headerless — ignore
            ts = int(m.get("ts", 0))
            if any(a in frm for a in OUR_IDENTITIES):
                latest_ours = max(latest_ours, ts)
            else:
                latest_inbound = max(latest_inbound, ts)
        if latest_ours >= 0 and latest_ours >= latest_inbound:
            resolved.add(e["key"])
    if not resolved:
        return 0
    with _locked():
        entries = load_queue()
        changed = 0
        for e in entries:
            if not is_dispositioned(e) and e.get("key") in resolved:
                e["handled"] = "resolved"
                e["handled_by"] = "auto-detect"
                changed += 1
        if changed:
            _atomic_write(entries)
    return changed
