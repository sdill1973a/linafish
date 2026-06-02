# Integration — how the three surfaces share one truth

Prose, not prescription. This is how I wired it on my substrate; map it onto
yours. No secrets, paths, or credentials here on purpose (public repo).

## The cast

- **A producer** (a polling listener) appends inbound items to the queue via
  `append()` — the lock-guarded entrypoint, so appends serialize with rewrites.
  Each entry carries at least: `ts`, a stable `key` (I use the thread id),
  `from`, `subject`, and `handled: false`.
- **Surface A — the hot hook** (runs on every user turn): builds a live read,
  calls `reconcile_live(live_keys)`, and renders ONE block from the result:
  `open` (needs attention) + `unqueued` (live but not yet queued) and a count of
  `suppressed` (handled — shown as a number, never as a nag).
- **Surface B — any other brief** (a wake/summary): calls `attention_items()`.
  Same function as the hook's canonical list → they cannot disagree.

## Three things that make it coherent

1. **One source of truth.** All surfaces read the queue through the recipe's
   functions. None re-derives state independently.
2. **One filter.** If you have a live query with a noise floor, define it ONCE
   and have the producer and the hot hook both use it. My original bug was a
   promo class the producer excluded but the hook didn't — same state, two
   filters, guaranteed drift.
3. **One key.** Reconcile on a stable id (thread id), not on subject text or
   message id. Dedup and suppression both hinge on it.

## Closing the loop

- The producer (or a cron) calls `auto_close(fetch_thread)` each cycle.
  `fetch_thread(key)` is your adapter: return the thread's messages as
  `[{"from": str, "ts": int}, ...]`. The recipe decides resolution; you only
  provide the messages. Keep it OUTSIDE the lock (network calls are slow); the
  lock wraps only the brief read-modify-write.
- For anything resolved off-channel (chat, a live fix, a phone call), call
  `mark_handled(key_or_subject, disposition, note)`. Auto-detection alone is
  insufficient precisely because real work gets handled where your detector
  can't see it.

## Hot-path hygiene (Surface A)

The hook runs on every turn, so the live read must be bounded:

- **Cap the socket timeout** around the live call. A best-effort `try/except`
  that swallows a hang still *hangs* — it just hides it. Put a hard ceiling on it.
- **Cache the live read** with a short TTL (I use 120s). A burst of turns then
  costs one API round-trip, not one-per-turn. The queue still drives the surface
  if the cache is cold or the API is down.
- **Never let the surface break the turn.** Wrap it; degrade to queue-only.
