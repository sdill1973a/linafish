"""#57: revectorize_all() recomputed every vector and never wrote them —
211 seconds of computation, zero durable effect (Olorina's receipt: byte-
identical stored vectors across a run + restart). The crystal log is
append-only and no code path rewrote it.

The fix adds an atomic crystal-log rewrite to Phase 5. These tests FAIL on
the unpatched engine (fail-first discipline)."""

import json
import pytest
from linafish.engine import FishEngine

DOCS = [
    "the river runs past the old mill and the water is cold in the morning",
    "grain and olives and wine were counted at the palace stores",
    "the keeper walks the wall at night and counts the lanterns",
    "a letter arrived from the coast with news of the fleet",
    "the scribe pressed the tablet twice and sealed it with wax",
    "wind moved through the orchard and the children counted apples",
]


def _grown_engine(tmp_path):
    eng = FishEngine(state_dir=tmp_path, name="t57")
    for d in DOCS[:3]:
        eng.eat(d, source="test")
    for d in DOCS[3:]:
        eng.eat(d, source="test")          # past the freeze -> digest gap
    return eng


def test_revectorize_persists_across_reload(tmp_path):
    eng = _grown_engine(tmp_path)
    out = eng.revectorize_all(vocab_size=24)
    assert out["revectorized"]
    in_memory = {c.id: list(c.mi_vector) for c in eng.fish.crystals if c.text}

    reloaded = FishEngine(state_dir=tmp_path, name="t57")
    on_disk = {c.id: list(c.mi_vector) for c in reloaded.fish.crystals if c.text}

    assert set(on_disk) == set(in_memory)
    for cid, vec in in_memory.items():
        # approx: the store round-trips through float32-precision repr;
        # the requirement is persistence, not bit-identity (the unpatched
        # engine fails this with an EMPTY disk vector, not a 1e-7 delta).
        assert on_disk[cid] == pytest.approx(vec, rel=1e-5), (
            f"crystal {cid}: disk vector != recomputed vector — "
            "revectorize did not persist (#57)")


def test_rewrite_is_backed_up_and_line_counted(tmp_path):
    eng = _grown_engine(tmp_path)
    eng.revectorize_all(vocab_size=24)
    log = eng.fish.crystal_log_path
    bak = log + ".bak-pre-rewrite"
    import os
    assert os.path.exists(bak), "rewrite must leave a backup beside the log"
    rows = sum(1 for _ in open(log, encoding="utf-8"))
    assert rows == len(eng.fish.crystals)


def test_rewrite_survives_lone_surrogates(tmp_path):
    eng = FishEngine(state_dir=tmp_path, name="t57")
    for d in DOCS[:3]:
        eng.eat(d, source="test")
    # eat() itself refuses lone surrogates (md5 of the text crashes), which
    # is how legacy stores got them: OTHER ingestion paths. Inject the way
    # history did — directly onto a stored crystal.
    eng.fish.crystals[0].text += " mojibake " + chr(0xDC81) + " from an old archive"
    out = eng.revectorize_all(vocab_size=24)
    assert out["revectorized"]
    # the log must remain parseable line-by-line after the rewrite
    for line in open(eng.fish.crystal_log_path, encoding="utf-8"):
        json.loads(line)
