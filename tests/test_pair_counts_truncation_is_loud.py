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
