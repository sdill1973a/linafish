"""Review #85, finding 1 (Olorina, 2026-09-09): once the heartbeat guard moved to the
resource, a whole-document substring scan refused real prose (5.8% of files, 0.67% of
paragraphs). Markers are matched only where a sender can DECLARE shape — the first line,
first MARKER_WINDOW chars (measured default 64: 0 false refusals on 2,299 real paragraphs).
Both directions: prose with the word mid-text passes; a declared pulse is still refused."""
from linafish.habituation import is_heartbeat, MARKER_WINDOW


def test_marker_mid_prose_is_not_a_pulse():
    prose = ("Ask whether the guard is reached, not whether it works. The healthcheck "
             "endpoint is the heartbeat. If it stops responding, everything stops.")
    assert not is_heartbeat(prose)


def test_marker_past_window_on_first_line_is_not_a_pulse():
    assert not is_heartbeat("x" * (MARKER_WINDOW + 1) + " heartbeat")


def test_declared_pulse_is_still_refused():
    assert is_heartbeat("heartbeat")
    assert is_heartbeat("status: heartbeat 12:00 all services up")
    assert is_heartbeat("HEARTBEAT node .35 alive\nsecond line of the same pulse")


def test_prefix_stays_anchored():
    assert is_heartbeat("T^keeper|pulse")
    assert not is_heartbeat("a sentence that mentions T^keeper| later on")
