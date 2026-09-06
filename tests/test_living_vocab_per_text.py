"""Issue #71 — living_vocab on the per-text path.

The issue as filed said a loaded (frozen) fish never rebuilt its vocab on ``eat()``. Measured
2026-09-06 (this file, run against HEAD 929fad8 BEFORE any fix): that is FALSE. ``learn()``
unfreezes on every call, so ``eat()`` rebuilds on every eat, and a reloaded living fish DOES
admit a new term per-text on a small corpus — the growth tests below passed untouched.

The real gate is RANK, not frozen: ``extend_vocab`` appends only terms in the current global
top-``size``. On a mature fish (7,353 crystals) a novel term fed 40 times never enters
because incumbents have frequencies in the hundreds. On 08-09 it entered via ``eat_path``
because a whole file's volume pushed it over the bar — volume, not verb.

These tests therefore pin what IS true on the per-text path (growth on a small corpus,
rebuild-before-crystallize, seal halts, batch shares the path) and document the legacy
hazard (non-living re-selection may reorder axes) as an expected failure, not a claim.
"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from linafish.engine import FishEngine

# Enough shared plain words that the first freeze has a vocabulary to build; each later
# text introduces a distinct novel token seen in several docs so it clears the df floor.
_SEED = [
    "the river carries the boat past the willow and the otter watches the water",
    "the otter slides into the river and the willow leans over the water again",
    "a boat on the river under the willow while the otter sleeps by the water",
    "the water is cold and the river is high and the willow holds the bank",
]


def _living_engine(tmp, name="pertext"):
    return FishEngine(state_dir=Path(tmp), name=name, living_vocab=True,
                      git_autocommit=False)


def _novel_texts(word, n=4):
    return [f"the {word} appears again beside the river near the willow and the water {i}"
            for i in range(n)]


def _seed_and_reload(tmp, living=True):
    """Build a fish, freeze it by eating, save, and reload — the served-fish shape."""
    kw = {"living_vocab": True} if living else {}
    e = FishEngine(state_dir=Path(tmp), name="pertext", git_autocommit=False, **kw)
    for t in _SEED:
        e.eat(t)
    assert e.fish.frozen
    e._save_state()
    # reload: a loaded fish is frozen from the first line of its life
    e2 = FishEngine(state_dir=Path(tmp), name="pertext", git_autocommit=False)
    assert e2.fish.frozen
    assert e2.fish.living_vocab is living
    return e2


def test_loaded_living_fish_grows_on_per_text_eat():
    """A reloaded living fish fed via eat() extends its vocab (small corpus). PASSES at HEAD."""
    with tempfile.TemporaryDirectory() as tmp:
        e = _seed_and_reload(tmp, living=True)
        before = list(e.fish.vocab)
        assert before, "seed freeze produced no vocab — test corpus too thin"
        for t in _novel_texts("zorbification"):
            e.eat(t)
        after = e.fish.vocab
        assert "zorbification" in after, (
            f"living fish did not learn a term fed {len(_novel_texts('zorbification'))}x "
            f"via eat(); vocab stayed {len(before)} -> {len(after)}")
        # append-only: the prefix is untouched, so old crystal vectors stay valid
        assert after[:len(before)] == before


def test_new_term_is_in_vocab_before_its_own_text_crystallizes():
    """Q's timing test (2026-09-06): the rebuild must sit BETWEEN learn and crystallize.

    If the vocab only grows after the text is crystallized, the text that carried the new
    term is stored against a vocab that lacks it — silent semantic loss on exactly the
    crystal that introduced the word. Checked by vector length: the crystal minted on the
    admitting eat must be as long as the vocab after that eat."""
    with tempfile.TemporaryDirectory() as tmp:
        e = _seed_and_reload(tmp, living=True)
        texts = _novel_texts("quillhaven")
        admitted_at = None
        for i, t in enumerate(texts):
            e.eat(t)
            if "quillhaven" in e.fish.vocab:
                admitted_at = i
                break
        assert admitted_at is not None, "term never admitted — growth test should have failed first"
        last = e.fish.crystals[-1]
        vec = last.get("mi_vector") if isinstance(last, dict) else getattr(last, "mi_vector", None)
        assert vec is not None
        assert len(vec) == len(e.fish.vocab), (
            f"crystal that admitted the term has a {len(vec)}-dim vector against a "
            f"{len(e.fish.vocab)}-term vocab — rebuilt AFTER crystallize, not before")


import pytest


@pytest.mark.xfail(strict=False, reason=(
    "LEGACY HAZARD, documented not fixed (2026-09-06): non-living mode re-selects the vocab "
    "from scratch on EVERY eat (learn() unfreezes), so on a small corpus one eat can reorder "
    "the axes under stored crystal vectors. On a 9,365-doc fish one eat left the order intact; "
    "on this 4-doc corpus it did not. Stable-ish, never guaranteed."))
def test_non_living_loaded_fish_does_not_grow_on_per_text_eat():
    """FAILURE DIRECTION: a non-living fish must not reorder or grow on per-text eat."""
    with tempfile.TemporaryDirectory() as tmp:
        e = _seed_and_reload(tmp, living=False)
        before = list(e.fish.vocab)
        for t in _novel_texts("zorbification"):
            e.eat(t)
        assert e.fish.vocab == before
        assert "zorbification" not in e.fish.vocab


def test_sealed_living_fish_does_not_grow_on_per_text_eat():
    """FAILURE DIRECTION: seal still halts everything, living or not."""
    with tempfile.TemporaryDirectory() as tmp:
        e = _seed_and_reload(tmp, living=True)
        e.seal()
        before = list(e.fish.vocab)
        for t in _novel_texts("zorbification"):
            r = e.eat(t)
            assert r.get("sealed") is True
        assert e.fish.vocab == before


def test_batch_path_grows_too():
    """The batch verb shares the gate; it must share the fix."""
    with tempfile.TemporaryDirectory() as tmp:
        e = _seed_and_reload(tmp, living=True)
        before = list(e.fish.vocab)
        batch = getattr(e, "eat_batch", None) or getattr(e, "eat_many", None)
        if batch is None:
            import pytest
            pytest.skip("no batch eat verb on this engine")
        batch(_novel_texts("marrowlight"))
        assert "marrowlight" in e.fish.vocab
        assert e.fish.vocab[:len(before)] == before
