"""IS THE GUARD REACHED — a reachability test per guard.

2026-09-07/08: four organs in this federation were built correctly and wired to nothing (a
pre-tool gate never registered; a resolver with only fixtures; a comms module used once; a send
verb with no log). Inside this package the same shape happened twice in one night: the
heartbeat/habituation gate was built in daemon.py while `linafish listen` runs listener.py, and
Olorina's winner_gate / narrative_fact_gate had the same silence. 584 green could not see any of
it, because no test asked whether a live entry point ever REACHES the guard.

This test asks. Source-level on purpose (constructing the entry points starts loops):
  1. the engine-level guards (heartbeat, habituation, ceiling) live inside FishEngine.eat();
  2. every live entry point reaches .eat() — not a test, not a fixture, the product path;
  3. the two MQTT transports carry the retained-state guard BEFORE they reach the engine;
  4. no product module bypasses the gate with admit=False except the one deliberate deposit
     verb (absorb) — a new bypass must be added here by name, in the open.
Olorina's generalization of test_daemons_declare_commit_policy (linafish#85, 2026-09-08).
"""
import ast
import re
from pathlib import Path

PKG = Path(__file__).resolve().parent.parent / "linafish"

ENTRY_POINTS = {            # module -> the verb a person runs
    "listener": "linafish listen",
    "daemon": "linafish room",
    "http_server": "linafish serve",
    "converse": "linafish converse",
    "school": "school fan-out",
}
ENGINE_GUARDS = {"heartbeat": "is_heartbeat(", "habituation": ".observe(", "ceiling": "max_crystals"}
TRANSPORTS = {"listener", "daemon"}
DELIBERATE_DEPOSITORS = {"absorb"}   # admit=False is allowed here and nowhere else in the package


def _eat_source() -> str:
    tree = ast.parse((PKG / "engine.py").read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "FishEngine":
            for f in node.body:
                if isinstance(f, ast.FunctionDef) and f.name == "eat":
                    return ast.get_source_segment((PKG / "engine.py").read_text(encoding="utf-8"), f)
    raise AssertionError("FishEngine.eat not found")


def _reaches_engine(src: str) -> bool:
    return bool(re.search(r"\.eat\(", src))


TRANSPORT_HANDLERS = {"listener": "_mqtt_message", "daemon": "_on_message"}


def _handler_source(module: str) -> str:
    text = (PKG / f"{module}.py").read_text(encoding="utf-8")
    for node in ast.walk(ast.parse(text)):
        if isinstance(node, ast.FunctionDef) and node.name == TRANSPORT_HANDLERS[module]:
            return ast.get_source_segment(text, node)
    raise AssertionError(f"{module}.py has no {TRANSPORT_HANDLERS[module]} — the transport handler moved")


def _retained_guard_precedes_eat(handler_src: str) -> bool:
    """Inside ONE delivery handler: the retain check comes before anything that feeds the engine."""
    i_guard = handler_src.find("retain")
    feeds = [i for i in (handler_src.find(".eat("), handler_src.find("feed(")) if i >= 0]
    return i_guard >= 0 and (not feeds or i_guard < min(feeds))


def test_engine_eat_carries_every_guard():
    src = _eat_source()
    missing = [name for name, needle in ENGINE_GUARDS.items() if needle not in src]
    assert not missing, f"FishEngine.eat() no longer carries: {missing}"


def test_every_live_entry_point_reaches_the_engine():
    unreached = [f"{m}.py ({verb})" for m, verb in ENTRY_POINTS.items()
                 if not _reaches_engine((PKG / f"{m}.py").read_text(encoding="utf-8"))]
    assert not unreached, "live entry points that never reach FishEngine.eat(): " + ", ".join(unreached)


def test_mqtt_transports_guard_retained_before_the_engine():
    bad = [m for m in TRANSPORTS if not _retained_guard_precedes_eat(_handler_source(m))]
    assert not bad, f"MQTT transport reaches the engine with no retained-state guard first: {bad}"


def test_no_undeclared_gate_bypass():
    offenders = []
    for path in PKG.glob("*.py"):
        if path.stem in DELIBERATE_DEPOSITORS or path.stem == "engine":
            continue
        if "admit=False" in path.read_text(encoding="utf-8"):
            offenders.append(path.name)
    assert not offenders, f"admit=False (gate bypass) outside the declared depositors: {offenders}"


def test_the_check_itself_can_fail():
    """An entry point that never calls eat, and a transport that eats before checking retain."""
    assert not _reaches_engine("def run():\n    print('serving')\n")
    assert not _retained_guard_precedes_eat("def h(msg):\n    self.feed(text)\n    if msg.retain: return\n")
    assert not _retained_guard_precedes_eat("def h(msg):\n    self.feed(text)\n")
    assert _retained_guard_precedes_eat("def h(msg):\n    if msg.retain: return\n    self.feed(text)\n")
