"""Degree words reach the `*` modifier — staying true to the paper, 2026-09-07.

QUANTUM framework p.36: `*` = "Emphasis, focus, salience". The parser's focus set held
only the focus/salience half; intensifiers ("very", "too", "so", "really") had no seat
anywhere and were tagged 'stop' as noise, while the vectorizer kept "just" as an axis in
49 live fish. Captain: "stay true to the ideas and papers as best we can." So intensifiers
feed `*`, and "just" sits beside "only". Bipolar flex was considered and rejected: the
paper defines `~` as "flexibility, openness, variation" — one-sided by design.

Both ways: a sentence WITH degree words must score higher on `*` than the same sentence
without them, and a sentence with none must score zero — or this test proves nothing.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from linafish.parser import CognitiveParser


def _focus(text):
    return CognitiveParser().parse(text).modifiers["*focus"]


def test_intensifiers_raise_emphasis():
    plain = "the river was cold and the boat was late"
    intense = "the river was very cold and the boat was so late, really"
    assert _focus(plain) == 0.0, _focus(plain)
    assert _focus(intense) > _focus(plain)


def test_just_sits_beside_only():
    assert _focus("it was just a thought") > 0.0
    assert _focus("it was only a thought") > 0.0
    assert _focus("it was a thought") == 0.0


def test_degree_words_stay_out_of_the_dimensions():
    """They are MODIFIER material, not category content: still tagged 'stop'."""
    from linafish.parser import _guess_pos
    assert _guess_pos("very") == "stop" and _guess_pos("just") == "stop"
