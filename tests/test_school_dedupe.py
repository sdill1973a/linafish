"""``linafish school eat --dedupe``: the school verb was the last feeder that could not
refuse a repeat. Both directions, on purpose (a guard proven on the happy path only is
an organ that cannot fail): on -> a member grows by ONE on a repeat; off -> by TWO
(the old behaviour, unchanged); and the CLI flag reaches School (no silent drop).
"""
import json
from linafish.school import School


def _school(tmp_path, dedupe):
    root = tmp_path / "school"
    root.mkdir()
    (root / "school.json").write_text(json.dumps(
        {"central": "central", "members": {"m": {"d": 4.0}}}))
    return School(state_dir=root, central_state_dir=tmp_path / "central",
                  git_autocommit=False, dedupe=dedupe)


TEXT = "the door refuses a repeat and the school is the last door " * 3


def test_school_dedupe_on_refuses_exact_repeat(tmp_path):
    s = _school(tmp_path, dedupe=True)
    s.eat(TEXT, source="t")
    n = len(s.members["m"].crystals)
    s.eat(TEXT, source="t")
    assert len(s.members["m"].crystals) == n, "member must not grow on a byte-exact repeat"
    s.eat(TEXT + " but this one is new", source="t")
    assert len(s.members["m"].crystals) == n + 1, "a distinct text must still be eaten"


def test_school_dedupe_off_keeps_old_behaviour(tmp_path):
    s = _school(tmp_path, dedupe=False)
    s.eat(TEXT, source="t")
    n = len(s.members["m"].crystals)
    s.eat(TEXT, source="t")
    assert len(s.members["m"].crystals) == n + 1, "default must stay OFF — public behaviour unchanged"


def test_cli_flag_reaches_school(monkeypatch, tmp_path):
    """The flag on the command line is the flag on every engine — no silent drop."""
    import argparse
    from linafish import __main__ as m
    seen = {}

    class FakeSchool:
        def __init__(self, **kw):
            seen.update(kw)
            self.members = {}
            self.manifest = {"members": {}}
        def status(self): return {}

    monkeypatch.setattr("linafish.school.School", FakeSchool)  # cmd_school imports it locally
    args = argparse.Namespace(action="status", target=None, state_dir=tmp_path,
                              central_dir=tmp_path, manifest=None, source="t",
                              d=4.0, centroid=False, min_gamma=None, dedupe=True)
    try:
        m.cmd_school(args)
    except Exception:
        pass  # status rendering may need more than the fake gives; the ctor kwargs are the test
    assert seen.get("dedupe") is True
