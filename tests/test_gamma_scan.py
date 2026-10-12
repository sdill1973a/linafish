"""gamma_scan must give exactly what a gamma() loop gives — ragged vectors included."""
import random

import pytest

from linafish.crystallizer_v3 import gamma, gamma_scan


def _loop(probe, vecs, floor):
    return {i: gamma(probe, v) for i, v in enumerate(vecs) if v and gamma(probe, v) > floor}


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_matches_loop_on_ragged_vectors(seed):
    rnd = random.Random(seed)
    probe = [rnd.uniform(-1, 1) for _ in range(300)]
    vecs = [[rnd.uniform(-1, 1) for _ in range(rnd.choice([0, 1, 50, 299, 300, 301, 450]))] for _ in range(400)]
    vecs.append([0.0] * 120)
    old, new = _loop(probe, vecs, 0.1), dict(gamma_scan(probe, vecs, 0.1))
    assert set(old) == set(new)
    assert max(abs(old[k] - new[k]) for k in old) < 1e-12


def test_small_input_is_the_loop():
    probe, vecs = [1.0, -2.0, 0.5], [[1.0, 1.0, 1.0], [], [0.0, 0.0]]
    assert dict(gamma_scan(probe, vecs, 0.0)) == _loop(probe, vecs, 0.0)
