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
"""

import math
import re

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


def verdict(text, vectorizer, recent_texts=None, gamma=None, gamma_floor=0.885):
    """Grade a query by how much co-occurrence evidence backs it.

    Bands (on max_evidence): <0.25 ungrounded, 0.25-1.30 thin,
    >1.30 grounded. An ungrounded query gets one lift: if a single
    recent text (within the caller's recency window) covers at least
    half the query's informative tokens, the band softens to
    'thin-recent' — the fish just learned this, it hasn't earned
    'grounded' yet.

    Composition fusion (M1 Phase 1c): pair evidence alone can be
    register-borrowed — a query can wear known vocabulary in known
    pairings without the query, taken as a whole, actually resonating
    with anything the fish holds. gamma (the top match's whole-query
    similarity) catches what pair statistics cannot: if the band would
    be 'grounded' but gamma is given and falls below gamma_floor, the
    verdict is demoted to 'thin' and the demotion is named. Omitting
    gamma leaves the verdict exactly as it was before this fusion.
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

    if band == "grounded" and gamma is not None and gamma < gamma_floor:
        result["band"] = "thin"
        result["demoted_by"] = "composition"
        result["gamma"] = gamma

    return result
