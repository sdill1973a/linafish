"""M1 grounding verdict — is a taste query backed by known co-occurrence,
or floating free of anything the fish has actually seen?

CONTRACT (measured, 2026-08-11 v5 + design round 2): ``grounded`` means
WELL-ATTESTED — the query's vocabulary and composition are strongly
backed by the corpus. It does NOT mean TRUE. Within pair statistics and
vector resonance, a well-composed fabrication built from real vocabulary
(register-borrowing) is indistinguishable from a real memory; three veto
candidates died to that measurement (see data/METRIC_GRAVEYARD.md in the
runtime repo). Callers holding load-bearing claims must cross-check
against the disk or a claim-level judge — this module cannot do it.

Additive to ``taste_dict`` (never changes an existing field, never breaks
an early-return path — see ``FishEngine.taste_dict``). Three questions:

1. Which tokens in the query carry information at all
   (``informative_tokens``)?
2. For each pair of those tokens, how much co-occurrence evidence does the
   vectorizer actually hold (``pair_evidence``)?
3. Given that evidence, how should the query be graded — grounded, thin,
   or ungrounded — with a recency lift for things the fish only just
   learned (``verdict``)?

No redesign here — this module implements a frozen spec. Band edges and
the recency-lift threshold are not tunable knobs; they're the spec.

CALIBRATED 2026-11-14 (120 probes: 20 invented / 20 true / 20 identity
lines on two served fish, 21K and 41K crystals). Two findings changed the
``grounded`` gate:

1. The composition floor of 0.885 was unreachable BY CONSTRUCTION. A
   stored crystal's own text, re-tasted verbatim, scores gamma 0.34-0.43
   against its own stored vector (measured on both served fish and on the
   400-crystal test fixture) because the vectorizer keeps moving after the
   crystal is stored. Every line that cleared max_evidence 1.30 (51 of 120)
   was demoted; 0 of 120 came back ``grounded``, true and invented alike.
   gamma separates true from invented at AUC 0.46 (no better than chance) — and it ranks an invented
   line ABOVE "Caroline Marie Dill, August 29 2023" on both fish. So gamma
   now guards only the zero-resonance case (nothing matched → never
   grounded); the ``gamma_floor`` parameter stays for callers that want a
   stricter floor.
2. max_evidence does not separate (AUC 0.70): an invented sentence that
   borrows ONE real pair ("pole star", "warm decoder") clears 1.30 as
   easily as a true one. mean_evidence does (AUC 0.95): in a true line most
   pairs are attested, in an invented line one is. ``grounded`` therefore
   also requires mean_evidence >= 0.25 (SPREAD_FLOOR; threshold chosen on
   one half of the rows, 0.247, and checked on the other, 0.209 — 0.25 is
   the conservative side). Below it the band is ``thin`` with
   ``demoted_by: "spread"``.

Not fixed, and not claimed: a SHORT invented line (1-3 informative tokens)
has mean ≈ max, so one borrowed real pair still grounds it. That is the
register-borrowing hole the contract above already names. And ``thin``
still does NOT mean "the fish lacks it" — about half the true lines on the
calibration set stay ``thin``; read the matches, check the disk.
"""

import math
import re

# One of three stopword-like sets in the package, each with its own job — see the
# cross-reference at crystallizer_v3.STOPWORDS. This one is a superset of the vectorizer's
# set by construction (pinned by tests/test_stopword_sets_are_deliberate.py).
# Small, deliberately short — this is a stopword FLOOR, not an NLP
# pipeline. Anything longer than this belongs in a real tokenizer, not
# a grounding check that has to stay legible.
STOPWORDS = frozenset({
    "the", "a", "an", "and", "or", "but", "to", "of", "in", "on", "at",
    "is", "are", "was", "were", "be", "been", "being",
    "this", "that", "these", "those", "it", "its",
    "as", "for", "with", "by", "from", "not", "no",
    "do", "does", "did", "done",
    "have", "has", "had", "having",
    "will", "would", "can", "could", "shall", "should", "may", "might", "must",
    "i", "you", "he", "she", "we", "they", "me", "him", "her", "us", "them",
    "my", "your", "his", "our", "their",
    "what", "which", "who", "whom", "whose",
    "so", "if", "than", "then", "there", "here",
    "when", "where", "how", "why",
    "all", "any", "some", "into", "about", "up", "out", "over", "under",
    "again", "more", "most", "other", "such", "only", "own", "same", "too",
    "very", "just", "also", "one", "two",
})


def informative_tokens(text, vectorizer):
    """Lowercase alpha tokens worth grounding a query against.

    Kept iff not a stopword, AND (len >= 4 OR the vectorizer already
    knows the token) — so a short but KNOWN name ('q') survives while
    short filler doesn't.

    Returns a sorted set (list, deduped, alphabetical) — pair_evidence
    walks it in order so (a, b) pairs come out a < b for free.
    """
    tokens = re.findall(r"[a-z]+", (text or "").lower())
    known = getattr(vectorizer, "token_doc_counts", None) or {}

    kept = set()
    for t in tokens:
        if t in STOPWORDS:
            continue
        if len(t) >= 4 or known.get(t, 0) > 0:
            kept.add(t)
    return sorted(kept)


def _idf(token, vectorizer):
    doc_count = getattr(vectorizer, "doc_count", 0) or 0
    known = getattr(vectorizer, "token_doc_counts", None) or {}
    df = known.get(token, 0)
    if df > 0 and doc_count > 0:
        return math.log2(doc_count / df)
    return math.log2(doc_count + 1) if doc_count > 0 else 0.0


def _spec(a, b, vectorizer):
    """min(idf) normalized into a 0..~1 specificity score."""
    doc_count = getattr(vectorizer, "doc_count", 0) or 0
    denom = math.log2(doc_count + 1) if doc_count > 0 else 0.0
    if denom <= 0:
        denom = 1.0
    return min(_idf(a, vectorizer), _idf(b, vectorizer)) / denom


def _pair_count(a, b, vectorizer):
    """Look up co-occurrence count, tolerant of key shape.

    The live MIVectorizer keys pair_counts by a sorted tuple; a
    string-keyed ('a|b') stub is also honored, in either token order.
    """
    counts = getattr(vectorizer, "pair_counts", None) or {}
    for key in (f"{a}|{b}", f"{b}|{a}", (a, b), (b, a)):
        try:
            value = counts.get(key)
        except AttributeError:
            value = None
        if value:
            return value
    return 0


def pair_evidence(tokens, vectorizer):
    """(a, b, count, evidence) for every unordered pair of tokens.

    evidence = log1p(count) * spec, where spec rewards pairs of rare
    (high-idf) tokens over pairs of merely-common ones — a co-occurrence
    between two ubiquitous words is weak evidence even at a high count.
    """
    toks = list(tokens)
    out = []
    for i in range(len(toks)):
        for j in range(i + 1, len(toks)):
            a, b = toks[i], toks[j]
            count = _pair_count(a, b, vectorizer)
            spec = _spec(a, b, vectorizer)
            evidence = math.log1p(count) * spec
            out.append((a, b, count, evidence))
    return out


# A 'grounded' band needs most of the query's pairs attested, not one. Calibrated 2026-11-14
# (see the module docstring): mean_evidence separates true from invented at AUC 0.95 where
# max_evidence (0.70) and gamma (0.46) do not.
SPREAD_FLOOR = 0.25


def verdict(text, vectorizer, recent_texts=None, gamma=None, gamma_floor=0.0,
            spread_floor=SPREAD_FLOOR):
    """Grade a query by how much co-occurrence evidence backs it.

    Bands (on max_evidence): <0.25 ungrounded, 0.25-1.30 thin,
    >1.30 grounded. An ungrounded query gets one lift: if a single
    recent text (within the caller's recency window) covers at least
    half the query's informative tokens, the band softens to
    'thin-recent' — the fish just learned this, it hasn't earned
    'grounded' yet.

    Composition guard (M1 Phase 1c, recalibrated 2026-11-14): if the band
    would be 'grounded' but gamma is given and is at or below gamma_floor,
    the verdict is demoted to 'thin' with ``demoted_by: "composition"``.
    The default floor is 0.0 — gamma 0.0 means the query resonated with
    nothing, and that can never be grounded. The old default of 0.885 was
    unreachable on any fish that has kept learning since its crystals were
    stored (verbatim text scores 0.34-0.43 against its own vector), so it
    demoted every grounded line, true or invented. Callers may still pass a
    stricter floor. Omitting gamma skips the guard.

    Spread guard (2026-11-14): a 'grounded' band also requires
    mean_evidence >= spread_floor. One borrowed real pair lifts
    max_evidence over 1.30 for an invented sentence as easily as a true
    one; only a true sentence has MOST of its pairs attested. Below the
    floor the band is 'thin' with ``demoted_by: "spread"``.
    """
    tokens = informative_tokens(text, vectorizer)
    pairs = pair_evidence(tokens, vectorizer)

    evidences = [p[3] for p in pairs]
    max_evidence = max(evidences) if evidences else 0.0
    mean_evidence = (sum(evidences) / len(evidences)) if evidences else 0.0

    if max_evidence < 0.25:
        band = "ungrounded"
    elif max_evidence <= 1.30:
        band = "thin"
    else:
        band = "grounded"

    known_pairs = sorted(
        (p for p in pairs if p[2] > 0), key=lambda p: p[3], reverse=True
    )
    evidence_top = [(a, b, c) for a, b, c, _e in known_pairs[:3]]

    zero_pairs = [p for p in pairs if p[2] == 0]
    zero_ranked = sorted(
        zero_pairs, key=lambda p: _spec(p[0], p[1], vectorizer), reverse=True
    )
    unknown_pairs = [(a, b) for a, b, _c, _e in zero_ranked[:3]]

    recent_support = 0.0
    if recent_texts and tokens:
        qset = set(tokens)
        best = 0.0
        for rtext in recent_texts:
            rtoks = set(informative_tokens(rtext, vectorizer))
            if not rtoks:
                continue
            overlap = len(qset & rtoks) / len(qset)
            if overlap > best:
                best = overlap
        recent_support = best

    if band == "ungrounded" and recent_support >= 0.5:
        band = "thin-recent"

    result = {
        "band": band,
        "max_evidence": round(max_evidence, 4),
        "mean_evidence": round(mean_evidence, 4),
        "evidence": evidence_top,
        "unknown_pairs": unknown_pairs,
        "recent_support": round(recent_support, 4),
    }

    if band == "grounded" and gamma is not None and gamma <= gamma_floor:
        result["band"] = "thin"
        result["demoted_by"] = "composition"
        result["gamma"] = gamma
    elif band == "grounded" and mean_evidence < spread_floor:
        result["band"] = "thin"
        result["demoted_by"] = "spread"

    return result
