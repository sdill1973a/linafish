"""#56 Attack 3: the PMI normalizer mixed unigram and pair mass.

`p_joint = joint / total_tokens` divides a PAIR count by TOKEN mass, so
every PMI read log2(P/T) bits hot (+2.18 measured on a real me-fish where
pair mass P ~ 4.5x token mass T). In mi() the offset is constant (ranking-
safe, value-wrong); in the save() valve it expands to

    (joint/T)*PMI_true + (joint/T)*log2(P/T)

— a joint-proportional frequency bonus smuggled back into the criterion
whose one job was to replace frequency with information (Olorina's #59
review: ~10% of the kept budget was `(the,v)`-class pairs kept over
+12-bit names).

Fix: p_joint normalizes by pair mass — the live `pair_mass_true_total`
counter (fed per observation, survives truncation via the #59 max()-carry),
floored at the surviving table's mass for hand-built tables. Marginals stay
over token mass; they are unigram probabilities.

These tests FAIL on the pre-fix engine (fail-first discipline).
"""

import json
import math

import pytest

from linafish.crystallizer_v3 import MIVectorizer


def _hand_built(table, tokens):
    """A vectorizer with counts set directly — the never-fed path."""
    v = MIVectorizer()
    for t, c in tokens.items():
        v.token_counts[t] = c
    for pair, c in table.items():
        v.pair_counts[tuple(sorted(pair))] = c
    return v


def test_mi_is_definitional_pmi():
    """mi() must equal log2( (joint/P) / ((c1/T)(c2/T)) ) — standard PMI."""
    v = MIVectorizer()
    docs = [
        "the river runs past the old mill",
        "the keeper walks the wall and counts the lanterns",
        "gamma couples iff the window holds",
        "gamma rises iff the corpus grows",
    ]
    for d in docs:
        v.feed(d)
    T = sum(v.token_counts.values())
    P = sum(v.pair_counts.values())
    for t1, t2 in [("gamma", "iff"), ("the", "river"), ("keeper", "wall")]:
        joint = v.pair_counts.get(tuple(sorted([t1, t2])), 0)
        if joint == 0:
            continue
        expected = math.log2((joint / P) /
                             ((v.token_counts[t1] / T) * (v.token_counts[t2] / T)))
        assert v.mi(t1, t2) == pytest.approx(expected, rel=1e-9), (
            f"mi({t1},{t2}) is not definitional PMI — "
            f"the unigram-mass denominator is back (#56 Attack 3)")


def test_live_mass_counter_tracks_feed_exactly():
    """feed() maintains pair_mass_true_total per observation, so the
    denominator is current between saves, not a save-time snapshot."""
    v = MIVectorizer()
    v.feed("one two three four")
    v.feed("two three five")
    assert v.pair_mass_true_total == sum(v.pair_counts.values())
    before = v.pair_mass_true_total
    v.feed("six seven")
    assert v.pair_mass_true_total == before + 1
    assert v.pair_mass_true_total == sum(v.pair_counts.values())


def test_hand_built_table_still_computes():
    """A table built without feed() (counter = 0) must fall back to the
    surviving mass floor, never divide by zero, never return garbage."""
    v = _hand_built({("a", "b"): 6, ("c", "d"): 2},
                    {"a": 10, "b": 10, "c": 5, "d": 5})
    assert v.pair_mass_true_total == 0  # counter genuinely bypassed
    P, T = 8, 30
    expected = math.log2((6 / P) / ((10 / T) * (10 / T)))
    assert v.mi("a", "b") == pytest.approx(expected, rel=1e-9)


def test_truncation_cannot_rebase_the_denominator(tmp_path):
    """After a truncated save, the reloaded vectorizer's mass keeps the
    full pre-truncation observation mass (#59 max()-carry, consumed here)."""
    v = MIVectorizer()
    # letter suffixes: the tokenizer is [a-z]+ so digit suffixes collapse
    # into one token and no truncation ever happens (found the fail-first way)
    for i in range(20):
        s = chr(ord("a") + i)
        v.feed(f"alpha beta gamma{s} delta{s} epsilon{s}")
    full_mass = v.pair_mass_true_total
    assert full_mass == sum(v.pair_counts.values())

    path = str(tmp_path / "mi_vectorizer.json")
    import os
    os.environ["LINAFISH_MAX_PAIR_COUNTS"] = "10"
    try:
        v.save(path)
    finally:
        del os.environ["LINAFISH_MAX_PAIR_COUNTS"]

    v2 = MIVectorizer()
    v2.load(path)
    assert sum(v2.pair_counts.values()) < full_mass  # truncation really bit
    assert v2.pair_mass_true_total == full_mass, (
        "reloaded mass re-based on the surviving table — "
        "the file forgot how much it lost")


def test_valve_keeps_information_not_frequency(tmp_path, monkeypatch):
    """THE flip case (searched numerically, both criteria computed below):
    under the buggy unigram-mass criterion the frequent near-chance pair
    (of,the) outranks the rare +informative pair (gamma,iff); under the
    correct pair-mass criterion the ranking inverts. cap=2: slot 1 goes to
    the huge pad pair either way; slot 2 is the discriminator."""
    tokens = {"the": 1000, "of": 1000, "gamma": 10, "iff": 10,
              "x": 3000, "y": 3000}
    table = {("of", "the"): 200, ("gamma", "iff"): 5, ("x", "y"): 20000}
    T = sum(tokens.values())          # 8020
    P = sum(table.values())           # 20205

    def crit(joint, c1, c2, denom):
        p_j = joint / denom
        p1, p2 = c1 / T, c2 / T
        return p_j * math.log2(p_j / (p1 * p2))

    # precondition, asserted so the test can never rot into a tautology:
    assert crit(200, 1000, 1000, T) > crit(5, 10, 10, T), "buggy prefers (of,the)"
    assert crit(5, 10, 10, P) > crit(200, 1000, 1000, P), "correct prefers (gamma,iff)"

    v = _hand_built(table, tokens)
    monkeypatch.setenv("LINAFISH_MAX_PAIR_COUNTS", "2")
    path = str(tmp_path / "mi_vectorizer.json")
    v.save(path)

    kept = set(json.load(open(path))["pair_counts"])
    assert "x|y" in kept
    assert "gamma|iff" in kept, (
        f"valve kept {kept} — the frequency term is back in the criterion "
        "(#56 Attack 3): (of,the) at PMI~chance beat (gamma,iff) at +9 bits")
    assert "of|the" not in kept


def test_load_clears_the_pair_mass_cache(tmp_path):
    """Olorina's #56 review probe, taken as offered (her demonstration:
    mi() then load() of a SMALLER state left a 78x-inflated denominator —
    6.3 bits, sign flipped, on 5/5 pairs). max(true_total, stale_cache)
    picks the stale cache exactly when the previous corpus was larger:
    the rebind case. The floor was the gate."""
    big = MIVectorizer()
    for i in range(20):
        s = chr(ord("a") + i)
        big.feed(f"keeper wall lantern{s} coast{s} fleet{s}")
    big.mi("keeper", "wall")            # populates _pair_mass_cache

    small = MIVectorizer()
    small.feed("the keeper counts")
    path = str(tmp_path / "mi_vectorizer.json")
    small.save(path)

    clean = MIVectorizer()
    clean.load(path)

    big.load(path)                       # rebind: big object, small state
    for t1, t2 in [("keeper", "the"), ("counts", "the"), ("counts", "keeper")]:
        assert big.mi(t1, t2) == pytest.approx(clean.mi(t1, t2), rel=1e-9), (
            f"mi({t1},{t2}) differs after rebind — the stale pair-mass "
            "cache survived load() (Olorina's #56 probe)")
