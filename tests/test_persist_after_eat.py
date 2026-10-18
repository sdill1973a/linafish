"""exp/persist-after-eat: a crystal's line on disk carries the formation and couplings eat() computed for it.

Before: crystallize_text appended the line, THEN eat() filed and coupled — in memory only; nothing rewrote the log,
so every disk reader saw formation None / couplings [] and every cold load recomputed the tail (measured: 0 of ~13,900
on disk since 2026-08-16; 240 s first eat). Now eat() rewrites its own tail line after filing + coupling.
"""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from linafish.engine import FishEngine  # noqa: E402

TEXTS = [
    "The river carried the lantern downstream past the old mill while the teacher wrote about memory and loss.",
    "A compression protocol carries more with less: the key is small, the body is whole, the record stays on disk.",
    "Breakfast was eggs and coffee on the porch; the dog came home safe before noon and slept in the sun.",
    "The harbour lights came on one by one as the ferry turned; a zeppelin hung over the water at midnight.",
    "She tuned the radio until the static resolved into a voice reading weather for the plains and the coast.",
    "Granite steps led to a library where every book had been read at least once by someone who cared.",
    "The engineer measured twice and cut once; the bridge held, and the town forgot it had ever been afraid.",
    "Rain on the tin roof kept time while the kettle boiled and the cat ignored everyone equally.",
] * 6


def _disk(state_dir: Path):
    log = next(state_dir.rglob("*crystals.jsonl"))
    return [json.loads(l) for l in log.read_text(encoding="utf-8").splitlines() if l.strip()]


def test_tail_line_carries_formation_and_couplings():
    with tempfile.TemporaryDirectory() as td:
        e = FishEngine(state_dir=Path(td), name="persist-test")
        for t in TEXTS:
            e.eat(t, source="test")
        mem = e.fish.crystals
        disk = _disk(Path(td))
        assert len(disk) == len(mem) and [d["id"] for d in disk] == [c.id for c in mem]
        assert sum(1 for d in disk if d.get("formation")) == sum(1 for c in mem if c.formation) == len(mem)
        # each crystal's own couplings (as of its eat) are on disk; the file is still one valid JSONL
        on_disk = sum(1 for d in disk if d.get("couplings"))
        in_mem = sum(1 for c in mem if c.couplings)
        assert in_mem > 0 and on_disk >= in_mem * 0.8
        # a cold load reads them back instead of recomputing from nothing
        e2 = FishEngine(state_dir=Path(td), name="persist-test")
        assert sum(1 for c in e2.fish.crystals if c.formation) == len(mem)
        assert sum(1 for c in e2.fish.crystals if c.couplings) >= on_disk


def test_repersist_refuses_when_tail_moved():
    with tempfile.TemporaryDirectory() as td:
        e = FishEngine(state_dir=Path(td), name="persist-guard")
        for t in TEXTS[:16]:
            e.eat(t, source="test")
        log = next(Path(td).rglob("*crystals.jsonl"))
        before = log.read_text(encoding="utf-8")
        log.write_text(before + '{"id": "someone_else_wrote_this"}\n', encoding="utf-8")
        assert e.fish.repersist_tail(1) == 0           # ids at the offset no longer match: untouched
        assert log.read_text(encoding="utf-8").endswith('{"id": "someone_else_wrote_this"}\n')


def test_repersist_refuses_an_empty_id():
    """Olorina's review (2026-10-18): two crystals in her fish carry id "". repersist_tail verifies by id, so an
    empty id must refuse rather than risk matching the wrong line."""
    import tempfile
    from pathlib import Path
    from linafish.engine import FishEngine
    with tempfile.TemporaryDirectory() as td:
        e = FishEngine(state_dir=Path(td), name="emptyid")
        for i in range(6):
            e.eat(f"sentence number {i} about rivers and lanterns and memory", source="t")
        before = open(e.fish.crystal_log_path, encoding="utf-8").read()
        e.fish.crystals[-1].id = ""
        assert e.fish.repersist_tail(1) == 0
        assert open(e.fish.crystal_log_path, encoding="utf-8").read() == before
