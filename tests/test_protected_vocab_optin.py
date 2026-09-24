"""Protected vocabulary is OPT-IN (2.3.1) — proven both ways.

2.3.1's cold review found that #88 made PROTECTED_VOCAB reserve top axes in every
user's fish, with no switch: one mention of "home" or "love" and the word took a
front slot. Right for the fish it was built for; wrong as a silent default for
someone else's writing. LINAFISH_PROTECTED_VOCAB=on restores it; a comma list names
your own terms; unset/off is 2.3.0's election exactly.

Also here: fusion's stability check compared the first 20 vocab terms, which under
protection are a fixed alphabetical block — so it declared "stable" after one cycle
whatever the corpus axes did. It now compares the head with protected terms removed.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from linafish.crystallizer_v3 import PROTECTED_VOCAB, UniversalFish, protected_vocab
from linafish.fusion import FusionEngine


def test_off_by_default(monkeypatch):
    monkeypatch.delenv("LINAFISH_PROTECTED_VOCAB", raising=False)
    assert protected_vocab() is None
    monkeypatch.setenv("LINAFISH_PROTECTED_VOCAB", "off")
    assert protected_vocab() is None


def test_on_is_the_shipped_set(monkeypatch):
    monkeypatch.setenv("LINAFISH_PROTECTED_VOCAB", "on")
    assert protected_vocab() is PROTECTED_VOCAB


def test_a_list_names_your_own_terms(monkeypatch):
    monkeypatch.setenv("LINAFISH_PROTECTED_VOCAB", " Maria, river ,,garden ")
    assert protected_vocab() == frozenset({"maria", "river", "garden"})


def _corpus():
    # "home" occurs in ONE document of 400: rare enough that an unprotected election
    # never picks it, so its presence in the vocab is protection and nothing else.
    # 120 ordinary words, each in ~33 documents, outnumber the 50-axis vocab.
    words = [f"word{chr(97 + i // 26)}{chr(97 + i % 26)}" for i in range(120)]
    texts = [" ".join(words[(i * 7 + k) % 120] for k in range(10)) for i in range(399)]
    texts.append("wordaa wordab home wordac")
    return texts


def _vocab(monkeypatch, value):
    if value is None:
        monkeypatch.delenv("LINAFISH_PROTECTED_VOCAB", raising=False)
    else:
        monkeypatch.setenv("LINAFISH_PROTECTED_VOCAB", value)
    f = UniversalFish()
    f.learn(_corpus())
    f.freeze(size=50, d=4.0)
    return f.vocab


def test_default_freeze_reserves_nothing(monkeypatch):
    assert "home" not in _vocab(monkeypatch, None)


def test_opted_in_freeze_reserves_a_present_term(monkeypatch):
    assert "home" in _vocab(monkeypatch, "on")


def test_custom_list_reserves_its_own_term_only(monkeypatch):
    v = _vocab(monkeypatch, "home")
    assert "home" in v
    assert "caroline" not in v


def _fusion():
    return FusionEngine.__new__(FusionEngine)   # _stability_head needs no corpus


def test_stability_head_ignores_the_protected_block(monkeypatch):
    monkeypatch.setenv("LINAFISH_PROTECTED_VOCAB", "on")
    fe = _fusion()
    block = sorted(PROTECTED_VOCAB)[:25]                # a front block longer than N
    a = block + [f"corpus{i}" for i in range(30)]
    b = block + [f"other{i}" for i in range(30)]        # corpus axes all changed
    assert fe._stability_head(a) != fe._stability_head(b)   # NOT stable: the check sees it
    assert fe._stability_head(a) == fe._stability_head(list(a))


def test_stability_head_unchanged_when_protection_off(monkeypatch):
    monkeypatch.delenv("LINAFISH_PROTECTED_VOCAB", raising=False)
    fe = _fusion()
    v = [f"t{i}" for i in range(40)]
    assert fe._stability_head(v) == v[:FusionEngine.VOCAB_STABILITY_N]
