"""re_eat() is a writer and must serialize against eat().

Audit finding, 2026-08-01. eat() and flush() held _eat_lock; re_eat() did
not, while being the heaviest writer in the engine — it relearns, replaces
vocab, bumps the epoch, deletes the pending file and rebuilds every
formation. Both callers of re_eat run on their own threads (POST /re_eat on
a request thread, and the background maintenance thread every
re_eat_interval_hours), so on any daemon taking traffic the interleaving was
ordinary operation, not a corner case. A comment inside re_eat asserted
"re_eat() guarantees no concurrent eat() is in flight."

The corruption is silent: a crystal vectorized against a vocab being
replaced under it, or filed into a formation set about to be rebuilt from a
corpus that does not contain it. Nothing raises.

These tests exercise mutual exclusion, not a specific corrupt output —
which of the interleavings you get is genuinely nondeterministic, and a test
that pinned one would be pinning luck.
"""

import json
import threading

from linafish.engine import FishEngine

TEXT = ("The river road at dawn, fog over the water, gravel under the tires, "
        "the long quiet drive home through the bottoms. ")


def _engine(tmp_path):
    """An engine with pending texts, so re_eat runs a real cycle instead of
    short-circuiting on nothing_pending.

    The pending file is written directly. It has to be: no engine path
    produces one. ``FishEngine.eat`` freezes the fish before crystallizing,
    and ``UniversalFish.crystallize_text`` only appends to ``pending`` on its
    pre-freeze branch (crystallizer_v3.py:1392), so eat / eat_many / eat_path
    all leave ``fish.pending`` empty forever. Filed separately — it means the
    engine's re_eat short-circuits on nothing_pending in ordinary use, which
    is a fact about reachability, not about whether the lock belongs here.
    """
    e = FishEngine(state_dir=tmp_path, name="t", git_autocommit=False,
                   save_state_every_n_eats=1)
    for i in range(6):
        e.eat(f"{TEXT} Run {i} of the fixture, with enough words to crystallize.")
    with open(e.fish.pending_path, "w") as f:
        for i in range(4):
            f.write(json.dumps(
                {"text": f"{TEXT} Pending deposit {i}, awaiting the next cycle."}
            ) + "\n")
    return e


def test_re_eat_holds_the_writer_lock(tmp_path):
    """Probed from another thread, since the lock is reentrant for its owner."""
    e = _engine(tmp_path)
    acquired_elsewhere = []

    def probe_from_another_thread():
        got = e._eat_lock.acquire(blocking=False)
        acquired_elsewhere.append(got)
        if got:
            e._eat_lock.release()

    original = e._formative_assess

    def assess_while_probed():
        t = threading.Thread(target=probe_from_another_thread)
        t.start()
        t.join(timeout=5)
        return original()

    e._formative_assess = assess_while_probed
    result = e.re_eat()

    assert result["re_eat"] is True, "fixture did not produce a real re-eat cycle"
    assert acquired_elsewhere == [False], (
        "another thread acquired the writer lock during re_eat")


def test_eat_cannot_interleave_with_re_eat(tmp_path):
    """Park re_eat mid-cycle and prove a concurrent eat() waits.

    Not timing-sensitive in the direction that matters: with the lock held,
    the eat thread is blocked on the lock and CANNOT finish, so the negative
    assertion is deterministic. Without the lock it finishes immediately.
    """
    e = _engine(tmp_path)
    entered = threading.Event()
    release = threading.Event()
    eat_done = threading.Event()
    errors = []

    original = e._formative_assess

    def park():
        entered.set()
        release.wait(timeout=10)
        return original()

    e._formative_assess = park

    def run_re_eat():
        try:
            e.re_eat()
        except Exception as exc:  # surfaced below, not swallowed
            errors.append(("re_eat", exc))

    def run_eat():
        try:
            e.eat(f"{TEXT} A concurrent deposit arriving mid re-eat.")
        except Exception as exc:
            errors.append(("eat", exc))
        finally:
            eat_done.set()

    re_eat_thread = threading.Thread(target=run_re_eat)
    re_eat_thread.start()
    assert entered.wait(timeout=10), "re_eat never reached the park point"

    eat_thread = threading.Thread(target=run_eat)
    eat_thread.start()

    assert not eat_done.wait(timeout=1.0), (
        "eat() completed while re_eat held the corpus mid-rewrite")

    release.set()
    re_eat_thread.join(timeout=30)
    eat_thread.join(timeout=30)

    assert not errors, errors
    assert eat_done.is_set(), "eat() never completed after re_eat released"
    assert not re_eat_thread.is_alive() and not eat_thread.is_alive()


def test_writer_lock_is_reentrant(tmp_path):
    """re_eat holds the lock across rebuild_formations, the gardener, the
    tracker and two saves. If any of those ever calls back into a locked
    method, a plain Lock deadlocks the daemon — a fish that stops recording
    without saying so. flush() stands in for that shape here."""
    e = _engine(tmp_path)
    finished = threading.Event()

    def nested():
        with e._eat_lock:
            e.flush()
        finished.set()

    t = threading.Thread(target=nested, daemon=True)
    t.start()
    assert finished.wait(timeout=10), (
        "deadlock: flush() blocked on a lock already held by this thread")


def test_re_eat_with_nothing_pending_still_returns_cleanly(tmp_path):
    """The early return moved inside the lock; it must not hold or leak it."""
    e = FishEngine(state_dir=tmp_path, name="t", git_autocommit=False,
                   save_state_every_n_eats=1)
    assert e.re_eat() == {"re_eat": False, "reason": "nothing_pending"}
    assert e._eat_lock.acquire(blocking=False), "writer lock leaked"
    e._eat_lock.release()
