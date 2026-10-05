"""Converse must get the eat-latency fix too.

The 2026-06-20 eat-latency root-fix gated the O(N) full ``_save_state``
behind ``save_state_every_n_eats`` and drove it off the request path — but only
``serve_http`` was wired. ``serve_converse`` kept the engine default of 1, so
every served ``/eat`` re-serialized the whole corpus into fish.md. Measured
2026-10-04 on a 21K-crystal me-fish: 13.1s and 14.6s per /eat.

These tests start serve_converse without serving (serve_forever is stubbed to
return at once) and assert the engine it built carries the gate, and that a
flush still writes the deferred fish.md.
"""

import signal
from http.server import ThreadingHTTPServer

from linafish import converse

SAMPLE = ("This is a sufficiently long sample passage number {} written so the "
          "crystallizer has real text to chew on and will emit a crystal.")


def _start(tmp_path, monkeypatch, **kw):
    monkeypatch.setattr(signal, "signal", lambda *a, **k: None)
    monkeypatch.setattr(ThreadingHTTPServer, "serve_forever",
                        lambda self, *a, **k: None)
    converse.serve_converse(name="t", state_dir=tmp_path, port=0,
                            flush_interval_secs=0, **kw)
    return converse.ConverseHandler.engine


def test_converse_engine_is_gated_by_default(tmp_path, monkeypatch):
    e = _start(tmp_path, monkeypatch)
    assert e.save_state_every_n_eats == 200


def test_converse_gate_is_configurable(tmp_path, monkeypatch):
    e = _start(tmp_path, monkeypatch, save_state_every_n_eats=1)
    assert e.save_state_every_n_eats == 1


def test_converse_eat_defers_then_flush_writes(tmp_path, monkeypatch):
    e = _start(tmp_path, monkeypatch)
    e.eat(SAMPLE.format(1), admit=False)
    pending = e._eat_count_since_save
    assert pending >= 1, "gated converse engine should defer the full save"
    e.flush()
    assert e._eat_count_since_save == 0
    assert e.fish_file.exists()
