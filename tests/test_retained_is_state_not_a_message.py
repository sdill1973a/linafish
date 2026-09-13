"""A RETAINED MQTT delivery is state replay, not a message. Neither transport entry point eats it.

THX, 2026-09-10 (.147 OOM, recurring): the listener subscribes on every (re)connect; the broker
answers every new subscription with the retained value of each topic; eaten naively each replay is
a distinct crystal. OOM -> restart -> resubscribe -> replay -> OOM. 80,673 -> 130,757 crystals in
20 days. His candidate fix was clean_session=False; that only helps a client that does not
re-subscribe. The honest signal is the retain flag on the delivery itself. Both ways, both paths.
"""
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from linafish.listener import FishListener


class _Recorder:
    def __init__(self):
        self.fed = []
        self._refused = {"heartbeat": 0, "habituated": 0, "retained": 0}
    def feed(self, text, source="listen"):
        self.fed.append((text, source))


def _listener_stub():
    lst = FishListener.__new__(FishListener)       # no engine, no broker
    rec = _Recorder()
    lst._refused = rec._refused
    lst.feed = rec.feed
    return lst, rec


def test_listener_refuses_retained_delivery():
    lst, rec = _listener_stub()
    lst._mqtt_message("thx/fish/state", "x" * 400, retain=True)
    assert rec.fed == []
    assert lst._refused["retained"] == 1


def test_listener_feeds_a_live_delivery():
    """The organ must be seen to pass the other way: a non-retained message reaches feed()."""
    lst, rec = _listener_stub()
    lst._mqtt_message("olorin/conv/anchor", "a real sentence from a sibling " * 4, retain=False)
    assert len(rec.fed) == 1
    assert rec.fed[0][1] == "mqtt://olorin/conv"
    assert lst._refused["retained"] == 0


def test_room_daemon_refuses_retained_delivery():
    from linafish.daemon import RoomListener
    room = RoomListener.__new__(RoomListener)
    skipped = []
    room._skip = lambda why: skipped.append(why)
    touched = []
    room.engine = SimpleNamespace(eat=lambda *a, **k: touched.append(a))
    msg = SimpleNamespace(topic="thx/fish/state", payload=b"y" * 400, retain=True)
    room._on_message(None, None, msg)
    assert skipped == ["retained"]
    assert touched == []
