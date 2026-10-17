"""sparse — the retrieval key is the crystal's own terms, not its dense vector.

Measured 2026-10-17 on two live fish (35K and 14K crystals): the dense MI vector ranks by
vector LENGTH, not content (ragged widths; flat gamma; p@10 ≈ 0 on real queries; a full name
plus a date returned zero candidates against 2,032 crystals holding the name). An inverted
index over each crystal's own tokens answered the same queries at 6–10/10 in milliseconds.
Seed: docs/sparse-key-seed.md.

Design, in one line: carry MORE (the whole vocabulary — every term any crystal ever held),
with LESS (a crystal's address is its ~140 weighted terms, not thousands of floats). The dense
vector is untouched; it stays fuel for eating (couplings, formations). This is only the KEY.

Pure Python by design: postings are ``array('I')`` doc ids + ``array('H')`` term frequencies,
~6 bytes a posting (5M postings ≈ 30 MB). No numpy, no third index to install.
"""
from __future__ import annotations

import math
import re
from array import array
from collections import Counter
from typing import Callable, Dict, Iterable, List, Optional, Tuple

_WORD = re.compile(r"[a-z]+")


def default_tokenize(text: str) -> List[str]:
    """The crystallizer's tokenizer (``MIVectorizer.tokenize``): lowercase alpha runs. Kept here
    so the index and the crystals agree even when no vectorizer is in hand."""
    return _WORD.findall(text.lower())


class SparseIndex:
    """BM25 inverted index over crystal text. ``k1=1.2, b=0.75`` (vanilla; the reviewer who
    weighed this design asked for plain lexical weights in stage 1 and no MI here)."""

    def __init__(self, tokenize: Optional[Callable[[str], List[str]]] = None,
                 k1: float = 1.2, b: float = 0.75):
        self.tokenize = tokenize or default_tokenize
        self.k1 = k1
        self.b = b
        self._ids: Dict[str, array] = {}     # term -> doc indexes (terms seen in 2+ docs)
        self._tfs: Dict[str, array] = {}     # term -> term frequency, parallel to _ids
        self._single: Dict[str, Tuple[int, int]] = {}   # term seen in ONE doc -> (doc, tf); most of the vocabulary
        self._dl: array = array("I")         # doc index -> length in tokens
        self._total_len = 0
        self.n_docs = 0

    # -- building -------------------------------------------------------------------------
    def add(self, text: str) -> int:
        """Index one document; returns its doc index (its position in the crystal list)."""
        tokens = self.tokenize(text or "")
        i = self.n_docs
        self.n_docs += 1
        self._dl.append(len(tokens))
        self._total_len += len(tokens)
        for term, tf in Counter(tokens).items():
            tf = min(tf, 65535)
            ids = self._ids.get(term)
            if ids is not None:
                ids.append(i)
                self._tfs[term].append(tf)
                continue
            first = self._single.pop(term, None)
            if first is None:
                self._single[term] = (i, tf)      # the long tail of once-seen terms costs one tuple, not two arrays
                continue
            self._ids[term] = array("I", (first[0], i))
            self._tfs[term] = array("H", (first[1], tf))
        return i

    def _postings(self, term: str):
        """(doc ids, tfs) for a term, whichever store holds it; (), () when unknown."""
        ids = self._ids.get(term)
        if ids is not None:
            return ids, self._tfs[term]
        one = self._single.get(term)
        return ((one[0],), (one[1],)) if one else ((), ())

    def build(self, texts: Iterable[str]) -> "SparseIndex":
        for t in texts:
            self.add(t)
        return self

    # -- querying -------------------------------------------------------------------------
    @property
    def n_postings(self) -> int:
        return sum(len(a) for a in self._ids.values()) + len(self._single)

    @property
    def vocab_size(self) -> int:
        return len(self._ids) + len(self._single)

    def __contains__(self, term: str) -> bool:
        return term in self._ids or term in self._single

    def idf(self, term: str) -> float:
        df = len(self._postings(term)[0])
        if not df:
            return 0.0
        return math.log(1.0 + (self.n_docs - df + 0.5) / (df + 0.5))

    def query_terms(self, text: str) -> List[str]:
        """The query's distinct terms the index knows, most informative first."""
        seen = set(self.tokenize(text or ""))
        return sorted((t for t in seen if t in self), key=self.idf, reverse=True)

    def score(self, text: str, top: int = 10, floor: float = 0.0) -> List[Tuple[int, float]]:
        """[(doc index, bm25)] for the best ``top`` documents, best first. Empty when no query
        term is in the index — a loud nothing, not a confident wrong list."""
        if self.n_docs == 0:
            return []
        avgdl = self._total_len / self.n_docs if self.n_docs else 1.0
        k1, b = self.k1, self.b
        acc: Dict[int, float] = {}
        for term in self.query_terms(text):
            idf = self.idf(term)
            ids, tfs = self._postings(term)
            dl = self._dl
            for j in range(len(ids)):
                i = ids[j]
                tf = tfs[j]
                s = idf * tf * (k1 + 1.0) / (tf + k1 * (1.0 - b + b * dl[i] / avgdl))
                acc[i] = acc.get(i, 0.0) + s
        if not acc:
            return []
        ranked = sorted(acc.items(), key=lambda kv: kv[1], reverse=True)
        if floor > 0:
            ranked = [kv for kv in ranked if kv[1] > floor]
        return ranked[:top] if top else ranked

    def candidates(self, text: str) -> int:
        """How many documents share at least one known term with the query."""
        s = set()
        for term in self.query_terms(text):
            s.update(self._postings(term)[0])
        return len(s)
