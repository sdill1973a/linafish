"""Light vectors (LINAFISH_LIGHT_VECTORS=on): crystals' vectors memory-mapped from a float32 sidecar.

Captain, 2026-10-04: "remembering and accessing - not holding it all, ever". The JSONL stays the source of truth; the
sidecar is a derived, verifiable cache. Every test here compares against the plain (off) load of the SAME files, so a
light load that returned different numbers — or nothing — fails. A fish with no vectors would make these vacuous, so
the fixture asserts vectors exist first.
"""
import os

import pytest

np = pytest.importorskip("numpy")

from linafish.engine import FishEngine
from linafish import crystallizer_v3 as cv

WORDS = ("river memory compression truth ache recursion daughter build fish school crystal glyph chain record "
         "archive light vector voice table door ground road truck camp creek persimmon map chapter novel").split()


def _texts(n, seed=0):
    out = []
    for i in range(n):
        w = [WORDS[(i * 7 + j * 3 + seed) % len(WORDS)] for j in range(14)]
        out.append(f"Passage {i}: the " + " ".join(w) + f" and then the {WORDS[(i + seed) % len(WORDS)]} held.")
    return out


def _load(path, light, monkeypatch):
    monkeypatch.setenv("LINAFISH_LIGHT_VECTORS", "on" if light else "off")
    return FishEngine(state_dir=path, name="t", git_autocommit=False)


def _vecs(e):
    return [(c.id, np.asarray(c.mi_vector, dtype=np.float32) if c.mi_vector else None) for c in e.fish.crystals]


def _same(a, b):
    assert [i for i, _ in a] == [i for i, _ in b]
    for (_, x), (_, y) in zip(a, b):
        assert (x is None) == (y is None)
        if x is not None:
            assert x.shape == y.shape and np.array_equal(x, y)


@pytest.fixture
def fish(tmp_path, monkeypatch):
    monkeypatch.setenv("LINAFISH_LIGHT_VECTORS", "off")
    e = FishEngine(state_dir=tmp_path, name="t", git_autocommit=False)
    for t in _texts(80):
        e.eat(t, admit=False)
    e.flush()
    plain = _vecs(_load(tmp_path, False, monkeypatch))
    assert sum(1 for _, v in plain if v is not None) > 0, "no crystal carries a vector — these tests would prove nothing"
    return tmp_path


def test_light_load_matches_plain_and_writes_sidecar(fish, monkeypatch):
    plain = _vecs(_load(fish, False, monkeypatch))
    e = _load(fish, True, monkeypatch)
    _same(plain, _vecs(e))
    log = e.fish.crystal_log_path
    assert os.path.exists(log + ".vec.f32") and os.path.exists(log + ".vec.json")
    mapped = [c.mi_vector for c in e.fish.crystals if c.mi_vector]
    assert mapped and all(isinstance(v, cv.VecView) for v in mapped)


def test_second_light_load_uses_sidecar_without_decoding(fish, monkeypatch):
    _load(fish, True, monkeypatch)                                       # builds the sidecar
    calls = []
    real = cv._unpack_vec
    monkeypatch.setattr(cv, "_unpack_vec", lambda b: calls.append(1) or real(b))
    plain_ids = [c.id for c in _load(fish, False, monkeypatch).fish.crystals]
    calls.clear()
    e = _load(fish, True, monkeypatch)                                   # every crystal covered: nothing decoded
    assert calls == []
    assert [c.id for c in e.fish.crystals] == plain_ids


def test_appended_crystals_extend_the_sidecar(fish, monkeypatch):
    _load(fish, True, monkeypatch)
    log = _load(fish, False, monkeypatch).fish.crystal_log_path
    before = os.path.getsize(log + ".vec.f32")
    e = _load(fish, False, monkeypatch)
    for t in _texts(20, seed=5):
        e.eat(t, admit=False)
    e.flush()
    light = _load(fish, True, monkeypatch)
    _same(_vecs(_load(fish, False, monkeypatch)), _vecs(light))
    assert os.path.getsize(log + ".vec.f32") >= before


def test_rewritten_log_rebuilds_instead_of_mapping_a_guess(fish, monkeypatch):
    e = _load(fish, True, monkeypatch)
    log = e.fish.crystal_log_path
    lines = open(log, encoding="utf-8").read().splitlines(keepends=True)
    with open(log, "w", encoding="utf-8") as f:                         # rewrite: same crystals, reversed order
        f.writelines(reversed(lines))
    _same(_vecs(_load(fish, False, monkeypatch)), _vecs(_load(fish, True, monkeypatch)))


def test_shrunk_log_never_maps_a_guess(fish, monkeypatch):
    e = _load(fish, True, monkeypatch)
    log = e.fish.crystal_log_path
    lines = open(log, encoding="utf-8").read().splitlines(keepends=True)
    with open(log, "w", encoding="utf-8") as f:
        f.writelines(lines[: len(lines) // 2])
    _same(_vecs(_load(fish, False, monkeypatch)), _vecs(_load(fish, True, monkeypatch)))


def test_vecview_truthiness():
    mm = np.zeros(4, dtype="<f4")
    assert bool(mm[0:4].view(cv.VecView)) is True
    assert bool(mm[0:0].view(cv.VecView)) is False


def test_formations_are_the_same_light_or_plain(fish, monkeypatch):
    def forms(e):
        fs = getattr(e, "formations", None) or getattr(e.fish, "formations", []) or []
        return sorted((f.crystal_count, round(f.content_diversity, 9)) for f in fs)
    assert forms(_load(fish, False, monkeypatch)) == forms(_load(fish, True, monkeypatch))
