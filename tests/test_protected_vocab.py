"""Protected vocabulary + the region floor — proven BOTH ways.

Born 2026-08-19 from an audit of a self fish's axis set: 26 of 100 axes were pure
hex-hash fragments, and not one identity term survived. Captain: "if a coordinate
system can't say my daughter's name it isn't mine."

Root cause (not a post-filter problem): stranger-mode scores idf^2 * log(freq+1), so
rarity IS the score — a hash fragment seen in three documents of 155,377 outranks a
word the author writes every day, while max_doc_pct filters the author's signature out
as a stopword. Two root fixes, both tested here:

  protect      — identity terms PRESENT in the corpus are reserved slots before scoring.
  min_doc_frac — an axis must name a REGION (a floor on document frequency), so a
                 string that appears in one document can never buy a coordinate.

The failure direction matters as much as the pass: protection must NOT be able to
invent an axis for a word the corpus has never said, and must not be able to eat the
whole vocabulary.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from linafish.crystallizer_v3 import PROTECTED_VOCAB, MIVectorizer


def _fish():
    """A corpus shaped like the real one: identity words are a MINORITY of documents
    (caroline is in 1.2% of the me-fish), and each debris string appears in exactly
    one document. Both properties matter — an earlier fixture made identity words
    ubiquitous, which the stopword filter removed for a different reason and hid what
    was being tested."""
    v = MIVectorizer()
    letters = "abcdef"
    for i in range(300):                      # ordinary corpus, varied
        v.feed(f"session notes about the build and the plan for step {i} today")
    for i in range(40):                       # identity words: ~11% of documents
        v.feed(f"anchor holds memory for caroline in the quiet room tonight {i}")
    for i in range(60):                       # each debris token: exactly ONE document
        tok = "cf" + "".join(letters[(i // 6 ** k) % 6] for k in range(4))  # unique per i
        v.feed(f"commit {tok}{'x' * 0} landed and the checks came back clean")
    return v


def test_identity_term_wins_a_slot_when_it_would_otherwise_lose():
    v = _fish()
    plain = v.get_vocab(size=12)
    guarded = v.get_vocab(size=12, protect=frozenset({"caroline"}))
    assert "caroline" in guarded, "a present identity term must be reserved an axis"
    assert len(guarded) == len(plain) == 12, "protection must not change the axis count"


def test_protection_cannot_invent_an_absent_term():
    """The failure direction: an axis for a word the corpus never said would be a
    coordinate system lying about what it holds."""
    v = _fish()
    guarded = v.get_vocab(size=12, protect=frozenset({"zzzznotinthecorpus"}))
    assert "zzzznotinthecorpus" not in guarded


def test_protection_is_capped_so_it_cannot_eat_the_vocabulary():
    v = _fish()
    big = frozenset({"anchor", "memory", "caroline", "room", "holds", "the", "number"})
    guarded = v.get_vocab(size=8, protect=big, protect_max_frac=0.25)
    reserved = [t for t in guarded if t in big]
    assert len(reserved) <= 2, "protection must never exceed its cap"


def test_region_floor_evicts_single_document_debris():
    v = _fish()
    unfloored = v.get_vocab(size=40)
    floored = v.get_vocab(size=40, min_doc_frac=0.02)   # >= ~8 documents

    letters = "abcdef"
    made = {"cf" + "".join(letters[(i // 6 ** k) % 6] for k in range(4)) for i in range(60)}

    def debris(vocab):
        return [t for t in vocab if t in made]

    assert debris(unfloored), "precondition: without a floor, one-doc debris wins axes"
    assert not debris(floored), "the floor must evict strings that name no region"


def test_floor_keeps_terms_that_name_a_region():
    v = _fish()
    floored = v.get_vocab(size=40, min_doc_frac=0.02)
    assert "anchor" in floored and "memory" in floored


def test_protected_set_is_identity_bearing_and_lowercase():
    assert {"caroline", "lina", "ache", "love", "presence", "captain", "fish"} <= PROTECTED_VOCAB
    assert all(t == t.lower() and t.strip() == t for t in PROTECTED_VOCAB)
