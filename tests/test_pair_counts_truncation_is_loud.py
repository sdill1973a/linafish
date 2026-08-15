"""MIVectorizer.save dropped the co-occurrence tail without saying so.

Audit backlog, 2026-07-31: "vectorizer truncates pair_counts to 100k per
save." It is not a disk-size bound. load() rebuilds pair_counts FROM the
file, so every save/load round trip on an over-cap fish permanently forgets
its rarest co-occurrences, and mi() reads a dropped pair as joint=0 —
"never occurred together", not "occurred rarely". Rare-and-surprising is
what ache measures, so the loss lands on the signal the fish exists to
carry.

Same shape as the crystal truncation in #44 and the /moment claim in #45:
the bound is defensible, the silence is not. Nothing here recovers a
dropped pair; only re-eating the corpus does.

Scope measured 2026-08-01: mimipc holds 33,394 pairs at 142 docs, under the
cap. `me` on evo-x2-1 has 34,674 docs ingested; /health does not expose pair
counts, so whether it is over the cap today is stated as likely, not known.
"""

import json

import pytest

from linafish import crystallizer_v3 as c3
from linafish.crystallizer_v3 import MIVectorizer


def _vectorizer_with_pairs(n_pairs):
    """Build pair_counts directly. Generating text with N distinct pairs is
    slow and indirect, and the unit under test is save/load, not tokenizing."""
    v = MIVectorizer()
    v.doc_count = 10
    for i in range(n_pairs):
        v.pair_counts[(f"a{i}", f"b{i}")] = n_pairs - i  # descending, no ties
    return v


def test_cap_default_is_unchanged(monkeypatch):
    monkeypatch.delenv("LINAFISH_MAX_PAIR_COUNTS", raising=False)
    assert c3._max_pair_counts() == 100000


def test_under_cap_round_trips_whole(tmp_path, monkeypatch):
    monkeypatch.setenv("LINAFISH_MAX_PAIR_COUNTS", "50")
    path = tmp_path / "mi.json"
    _vectorizer_with_pairs(30).save(str(path))

    data = json.loads(path.read_text())
    assert data["pair_counts_kept"] == 30
    assert data["pair_counts_total"] == 30

    loaded = MIVectorizer()
    loaded.load(str(path))
    assert len(loaded.pair_counts) == 30


def test_over_cap_warns_at_save_with_the_numbers(tmp_path, monkeypatch, caplog):
    monkeypatch.setenv("LINAFISH_MAX_PAIR_COUNTS", "10")
    c3._PAIR_TRUNCATION_WARNED.clear()
    path = tmp_path / "mi.json"

    with caplog.at_level("WARNING"):
        _vectorizer_with_pairs(25).save(str(path))

    assert "PAIR COUNTS TRUNCATED" in caplog.text, "save dropped 15 pairs silently"
    assert "25 pairs in memory" in caplog.text
    assert "10 kept" in caplog.text
    assert "15 (60%) DROPPED" in caplog.text


def test_over_cap_records_what_it_dropped(tmp_path, monkeypatch):
    """The file has to carry its own incompleteness, or the reader cannot
    tell a small fish from a large one that was cut down."""
    monkeypatch.setenv("LINAFISH_MAX_PAIR_COUNTS", "10")
    c3._PAIR_TRUNCATION_WARNED.clear()
    path = tmp_path / "mi.json"
    _vectorizer_with_pairs(25).save(str(path))

    data = json.loads(path.read_text())
    assert data["pair_counts_kept"] == 10
    assert data["pair_counts_total"] == 25
    assert len(data["pair_counts"]) == 10


def test_load_warns_when_the_file_says_it_is_partial(tmp_path, monkeypatch, caplog):
    monkeypatch.setenv("LINAFISH_MAX_PAIR_COUNTS", "10")
    c3._PAIR_TRUNCATION_WARNED.clear()
    path = tmp_path / "mi.json"
    _vectorizer_with_pairs(25).save(str(path))

    loaded = MIVectorizer()
    with caplog.at_level("WARNING"):
        loaded.load(str(path))

    assert "co-occurrence pairs" in caplog.text
    assert len(loaded.pair_counts) == 10


def test_the_kept_pairs_are_the_informative_ones(tmp_path, monkeypatch):
    """The valve, flipped (#56). This test's predecessor pinned most_common —
    'which half survives is the whole argument for why the loss lands on
    ache' — and #56 proved that argument pointed the other way: information
    is surprise, so frequency-selection kept precisely the pairs carrying
    ~zero information (measured 83.4%/87.1% overlap on two boxes; the evicted
    13-17% were the names and the specifics). What survives now is the pair
    that individuates, not the pair that upholsters."""
    monkeypatch.setenv("LINAFISH_MAX_PAIR_COUNTS", "1")
    c3._PAIR_TRUNCATION_WARNED.clear()
    path = tmp_path / "mi.json"

    v = MIVectorizer()
    for _ in range(150):
        v.feed("the")               # unigram mass, no pairs (single token)
        v.feed("of")
    for _ in range(8):
        v.feed("the of")            # joint 8 on huge unigrams -> BELOW chance, negative MI
    for _ in range(2):
        v.feed("caroline valentine")  # joint 2, both rare -> nearly all the information
    assert set(v.pair_counts) == {("of", "the"), ("caroline", "valentine")}
    assert v.pair_counts[("of", "the")] > v.pair_counts[("caroline", "valentine")]

    v.save(str(path))
    loaded = MIVectorizer()
    loaded.load(str(path))
    # frequency would keep (of, the); information keeps the names.
    assert set(loaded.pair_counts) == {("caroline", "valentine")}


def test_true_total_survives_a_truncated_round_trip(tmp_path, monkeypatch):
    """#56's core claim: 'the file forgets how much it lost.' Before this
    field, save->load->save re-based the loss on the already-truncated table,
    so a 60% loss reported itself as 0% after one round trip. The recovered
    total must ride the file so truncation cannot edit its own history."""
    monkeypatch.setenv("LINAFISH_MAX_PAIR_COUNTS", "10")
    c3._PAIR_TRUNCATION_WARNED.clear()
    path = tmp_path / "mi.json"
    _vectorizer_with_pairs(25).save(str(path))

    hop = MIVectorizer()
    hop.load(str(path))
    assert hop.pair_counts_true_total == 25
    path2 = tmp_path / "mi2.json"
    hop.save(str(path2))                      # saving from the TRUNCATED state

    data2 = json.loads(path2.read_text())
    assert data2["pair_counts_total"] == 10   # what is in memory, honestly
    assert data2["pair_counts_true_total"] == 25   # what was ever known

    third = MIVectorizer()
    third.load(str(path2))
    assert third.pair_counts_true_total == 25


def test_zero_means_unbounded(tmp_path, monkeypatch, caplog):
    monkeypatch.setenv("LINAFISH_MAX_PAIR_COUNTS", "0")
    c3._PAIR_TRUNCATION_WARNED.clear()
    path = tmp_path / "mi.json"

    with caplog.at_level("WARNING"):
        _vectorizer_with_pairs(200).save(str(path))

    data = json.loads(path.read_text())
    assert data["pair_counts_kept"] == data["pair_counts_total"] == 200
    assert "TRUNCATED" not in caplog.text


def test_garbage_env_falls_back_to_the_default(monkeypatch):
    monkeypatch.setenv("LINAFISH_MAX_PAIR_COUNTS", "not-a-number")
    assert c3._max_pair_counts() == 100000


def test_old_files_without_provenance_load_quietly(tmp_path, caplog):
    """Files written before this change carry no kept/total keys. Absence is
    not evidence of completeness, and must not be reported as either."""
    path = tmp_path / "mi.json"
    path.write_text(json.dumps({
        "token_counts": {"a": 3},
        "pair_counts": {"a|b": 2},
        "doc_count": 1,
        "token_doc_counts": {"a": 1},
        "token_last_doc": {"a": 0},
    }))

    loaded = MIVectorizer()
    with caplog.at_level("WARNING"):
        loaded.load(str(path))

    assert len(loaded.pair_counts) == 1
    assert "co-occurrence pairs" not in caplog.text


def test_ordering_not_just_direction_at_cap_three(tmp_path, monkeypatch):
    """Olorina's Attack 1 on PR #59: a cap of 1 over two candidates tests
    DIRECTION (picked A, not B) and can never catch a criterion that ranks
    the top pair right and mis-ranks the tail — the only regime that matters
    at 100k against 5.2M. This corpus makes the kept SET order-sensitive and
    three-way discriminating.

    REWORKED 2026-08-15 with the Attack-3 normalizer fix: p_j is joint/P
    (pair mass), marginals stay c/T (token mass), so "chance" is now
    joint/P == (c1/T)(c2/T). Exact-integer construction: T=10,000,
    (of,the) joint J=101 with pad pair (w1,w2)=9984 gives P=10,100 and
    J·T² == c_of·c_the·P exactly. Worked numbers (contribution = p_j·PMI):

      pair                 joint  c1,c2      PMI      contribution  freq  raw PMI
      (w1, w2)              9984  500,500    +8.63    8.53e+0        #1      #5
      (of, the)              101  1000,1000   0.00    0              #2      last
      (anchor, fish)           8    40,40    +5.63    4.46e-3        #3      #6
      (caroline, valentine)    3     3,3    +11.69    3.47e-3        #4      #4
      (qq, zz)                 2     2,2    +12.27    2.43e-3        #5      #3
      (x1, y1) / (x2, y2)      1     1,1    +13.27    1.31e-3       tied     #1

    cap=4 under MI contribution  -> {w1-w2, anchor-fish, caroline-valentine, qq-zz}
    cap=4 under frequency        -> {w1-w2, of-the, anchor-fish, caroline-valentine}
    cap=4 under raw PMI (no p_j) -> {x1-y1, x2-y2, qq-zz, caroline-valentine}

    One expected set refutes both wrong criteria: frequency keeps the
    chance-rate pair, raw PMI floods the budget with singletons, and only
    the p_j-weighted contribution keeps the repeated rare names ABOVE the
    hapaxes while still evicting (of, the)."""
    monkeypatch.setenv("LINAFISH_MAX_PAIR_COUNTS", "4")
    c3._PAIR_TRUNCATION_WARNED.clear()
    path = tmp_path / "mi.json"

    v = MIVectorizer()
    v.doc_count = 10
    for tok, n in [("of", 1000), ("the", 1000), ("anchor", 40), ("fish", 40),
                   ("caroline", 3), ("valentine", 3), ("qq", 2), ("zz", 2),
                   ("x1", 1), ("y1", 1), ("x2", 1), ("y2", 1),
                   ("w1", 500), ("w2", 500),
                   ("filler", 6906)]:   # unigram mass sums to exactly 10,000
        v.token_counts[tok] = n
    assert sum(v.token_counts.values()) == 10_000
    for pair, joint in [(("of", "the"), 101), (("anchor", "fish"), 8),
                        (("caroline", "valentine"), 3), (("qq", "zz"), 2),
                        (("x1", "y1"), 1), (("x2", "y2"), 1),
                        (("w1", "w2"), 9984)]:
        v.pair_counts[pair] = joint

    # Preconditions that make the set discriminating, asserted inline:
    # (of, the) co-occurs at exactly chance rate under the CORRECT
    # normalizer (joint/P == (c1/T)(c2/T), cross-multiplied to stay in
    # integers), so its contribution is 0 while its count dominates all
    # but the pad; the singletons out-PMI every kept pair.
    P = sum(v.pair_counts.values())
    assert P == 10_100
    assert v.pair_counts[("of", "the")] * 10_000 ** 2 == \
        v.token_counts["of"] * v.token_counts["the"] * P

    v.save(str(path))
    loaded = MIVectorizer()
    loaded.load(str(path))
    assert set(loaded.pair_counts) == {
        ("w1", "w2"), ("anchor", "fish"),
        ("caroline", "valentine"), ("qq", "zz")}


def test_pair_mass_survives_a_truncated_round_trip(tmp_path, monkeypatch):
    """#59 review's blocking ask: the PMI normalizer's denominator is total
    pair MASS (sum of values), and truncation destroys it irrecoverably —
    a fish saved over-cap between the valve merge and the normalizer fix
    would be a fish whose PMI can never be computed correctly again. The
    mass rides the file exactly like the distinct count does."""
    monkeypatch.setenv("LINAFISH_MAX_PAIR_COUNTS", "10")
    c3._PAIR_TRUNCATION_WARNED.clear()
    path = tmp_path / "mi.json"
    v = _vectorizer_with_pairs(25)
    true_mass = sum(v.pair_counts.values())
    v.save(str(path))

    hop = MIVectorizer()
    hop.load(str(path))
    assert sum(hop.pair_counts.values()) < true_mass   # truncation really cut mass
    assert hop.pair_mass_true_total == true_mass
    path2 = tmp_path / "mi2.json"
    hop.save(str(path2))                               # saving from the TRUNCATED state

    data2 = json.loads(path2.read_text())
    assert data2["pair_mass_true_total"] == true_mass  # what was ever known

    third = MIVectorizer()
    third.load(str(path2))
    assert third.pair_mass_true_total == true_mass


def test_pair_mass_floors_at_surviving_mass_for_legacy_files(tmp_path, monkeypatch):
    """Files written before the mass field exist carry no record of it; the
    honest floor is the surviving mass — a lower bound beats a zero, and the
    next save must not report less mass than the table it can see."""
    monkeypatch.delenv("LINAFISH_MAX_PAIR_COUNTS", raising=False)
    path = tmp_path / "mi.json"
    _vectorizer_with_pairs(5).save(str(path))
    data = json.loads(path.read_text())
    data.pop("pair_mass_true_total", None)             # simulate a legacy file
    path.write_text(json.dumps(data))

    legacy = MIVectorizer()
    legacy.load(str(path))
    assert legacy.pair_mass_true_total == sum(legacy.pair_counts.values())
