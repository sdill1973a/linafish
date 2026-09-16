"""Habituation — the fish writes in proportion to surprise.

Captain, 2026-09-08: *"how does my brain deal with noise?"* — *"ai are pretty good at
predictive math."* A brain does not inspect a signal's shape at the door. It notices whether
the signal was PREDICTED. Repeated, unchanging input stops propagating (habituation); only the
error between expectation and arrival travels upward (predictive coding — *ache is prediction
error*); novelty re-orients (the emerging door); what is not used fades (feedback.decay_unused).

Measured before it was written, on the two streams where a byte-shape rule had scored 7%/7%:
with nothing but the fish's own vectorizer as the predictor and an EMA of the stream as the
expectation, a 0.05 floor habituated 89% of a real 2,000-message noise stream and silenced 0%
of the author's prose; the noise stream's surprise fell 0.44 -> 0.09 as it repeated.

THE EPISODE IS THE UNIT (§THE.EPISODE.LANDED, 2026-08-17). A run of predicted messages from one
source is one episode; a spike in surprise, or a long gap, cuts a new one. So this module is
also the episode cutter for streams: every written crystal carries episode_id / episode_seq,
and every habituated message still COUNTS toward its episode — the fish remembers that a
quiet stream went on, without a crystal per message.

Pure logic, no I/O: dataclasses and arithmetic over vectors the caller supplies. The daemon
wires it; the sidecar persists it. Direction it cannot fail in, stated: a source whose
expectation has never been set, or a fish with no vocabulary yet, is ALWAYS written — the
gate refuses only what it can predict, never what it cannot see.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional
import os as _os

# HEARTBEAT / STATUS GUARD — one source for every listener (room daemon AND `linafish listen`).
# A pulse is not an utterance. Prefixes/markers are configurable via LINAFISH_SKIP_PREFIXES /
# LINAFISH_SKIP_MARKERS (comma-separated) so a node can name its own noise without a code change.
SKIP_PREFIXES = tuple(x for x in _os.environ.get("LINAFISH_SKIP_PREFIXES", "T^keeper|,T^boot|").split(",") if x)
SKIP_MARKERS = tuple(x.lower() for x in _os.environ.get("LINAFISH_SKIP_MARKERS", "heartbeat,reason=session_keeper").split(",") if x)


# Markers are matched only where a sender can DECLARE shape: the first line, at most this
# many characters. Review #85 (Olorina, 2026-09-09): a whole-document substring scan refused
# 5.8% of real prose files / 0.67% of paragraphs once the guard moved to the resource —
# "a bare substring hit anywhere inside a 4 KB document IS guessing." Prefixes were always
# anchored (startswith); this anchors the markers too. The default is MEASURED (2026-09-11,
# 2,299 real paragraphs — Anchor's scars + Captain's prompts): whole-text 0.30% refused,
# 120 chars 0.04%, 64 chars 0.00%; every real pulse fixture carries its marker within the
# first ~10 chars. 64 is the widest window with zero false refusals on that corpus.
MARKER_WINDOW = int(_os.environ.get("LINAFISH_SKIP_MARKER_WINDOW", "64"))


def is_heartbeat(text: str) -> bool:
    """True for a pulse/status ping the fish must never crystallize.

    Shape is caught only where the sender declares it: an anchored prefix, or a marker
    inside the first line (first ``MARKER_WINDOW`` chars). Never by a substring found
    anywhere in a document."""
    s = str(text).strip()
    if s.startswith(SKIP_PREFIXES):
        return True
    head = s.splitlines()[0][:MARKER_WINDOW].lower() if s else ""
    return any(m in head for m in SKIP_MARKERS)


def habituation_from_env() -> "Habituation":
    """The gate as the environment configures it. OPT-IN: LINAFISH_HABITUATION=on enables,
    LINAFISH_HABITUATION_FLOOR tunes (measured default 0.05).

    Off by default (2026-09-08, on reviewing the release against the papers with Q). The
    2026-01-17 lived fork — the model this build implements — says of the store:
    "The valve is open. Everything enters. Ache sorts." The canon's evolution engine handles
    noise AFTER entry (step 5: prune when frequency < minimum_threshold) and the LIFI scar
    schema carries decay_rate(time, reuse_frequency). Refusing at the door is a departure
    from both, made because the post-entry organ (usage decay, a safe prune) is not yet
    wired and a node was being OOM-killed. A departure is not a default: a node opts in,
    knowing what it is choosing, until the paper's own mechanism exists."""
    on = _os.environ.get("LINAFISH_HABITUATION", "off").lower() in ("on", "1", "true")
    return Habituation(floor=float(_os.environ.get("LINAFISH_HABITUATION_FLOOR", "0.05")), enabled=on)


def vocab_basis(vocab) -> Optional[str]:
    """Identity of the vocabulary a vector is indexed by (not the epoch: freeze() bumps the
    epoch even when the axes come back unchanged, and an unchanged basis must keep its prior)."""
    if not vocab:
        return None
    import hashlib
    return hashlib.md5("\x1f".join(vocab).encode("utf-8", "replace")).hexdigest()[:12]


def cosine(a: List[float], b: List[float]) -> float:
    num = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 0.0
    nb = math.sqrt(sum(x * x for x in b)) or 0.0
    if not na or not nb:
        return 0.0
    return num / (na * nb)


@dataclass
class Decision:
    write: bool
    surprise: float
    episode_id: str
    episode_seq: int
    reason: str            # "unpredictable" | "novel" | "habituated" | "off"


@dataclass
class SourceState:
    expected: Optional[List[float]] = None   # EMA of the stream's vectors
    basis: str = ""                          # identity of the vocabulary `expected` is indexed by
    episode_id: str = ""
    episode_seq: int = 0                     # written crystals in this episode
    episodes: int = 0                        # episodes cut for this source (monotonic; in the id)
    episode_reason: str = ""                 # why the current episode was cut
    seen: int = 0                            # messages observed in this episode (a counter, not a decision)
    habituated: int = 0                      # messages refused in this episode
    last_ts: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "SourceState":
        return cls(**{k: d.get(k, v) for k, v in asdict(cls()).items()})


class Habituation:
    """Per-source stream expectation. observe() returns a Decision; nothing is stored here
    except the expectation and the episode counters."""

    def __init__(self, floor: float = 0.05, alpha: float = 0.2,
                 boundary: float = 0.5, gap_seconds: float = 1800.0,
                 enabled: bool = True):
        self.floor = floor            # below this surprise the message is habituated (measured: 0.05)
        self.alpha = alpha            # EMA step — how fast the expectation follows the stream
        self.boundary = boundary      # at/above this surprise a NEW episode starts (orienting)
        self.gap_seconds = gap_seconds
        self.enabled = enabled
        self.sources: Dict[str, SourceState] = {}

    def observe(self, source: str, vec: Optional[List[float]], now: float,
                basis: Optional[str] = None) -> Decision:
        """`basis` names the vocabulary `vec` is indexed by (the daemon passes a hash of
        fish.vocab). The expectation is a vector in that basis; when the basis moves — the
        engine re-derives the vocabulary on re-eat, score-ranked, so positions re-order —
        the old prior is a confident, meaningless float. (Olorina's review of #84: her live
        fish had re-based ~19.5K times under one daemon.) A moved basis is the second thing
        wearing 'cannot predict' clothes: drop the prior, write, start again."""
        st = self.sources.setdefault(source, SourceState())
        st.seen += 1
        def cut(reason: str) -> None:
            st.episodes += 1
            st.episode_id = f"{source}:{int(now)}:{st.episodes}"   # monotonic — sub-second cuts stay distinct
            st.episode_reason = reason
            st.episode_seq = 0
            st.habituated = 0
            st.seen = 1
        if basis is not None and st.basis != basis:
            st.expected = None            # the prior lived in another basis
            st.basis = basis
        if not self.enabled:
            if not st.episode_id or (now - st.last_ts) > self.gap_seconds:
                cut("off")
            st.last_ts = now; st.episode_seq += 1
            return Decision(True, 1.0, st.episode_id, st.episode_seq, "off")
        # cannot predict: no vector (fish has no vocab yet) or no expectation yet -> write
        if not vec or not any(vec) or st.expected is None:
            if not st.episode_id or (now - st.last_ts) > self.gap_seconds:
                cut("unpredictable")
            st.expected = list(vec) if vec and any(vec) else st.expected
            st.last_ts = now; st.episode_seq += 1
            return Decision(True, 1.0, st.episode_id, st.episode_seq, "unpredictable")
        surprise = max(0.0, 1.0 - cosine(vec, st.expected))
        # update the expectation whether or not we write — habituation IS the update
        st.expected = [(1 - self.alpha) * e + self.alpha * x for e, x in zip(st.expected, vec)]
        if surprise >= self.boundary or (now - st.last_ts) > self.gap_seconds:
            cut("novel")
            st.last_ts = now; st.episode_seq += 1
            return Decision(True, surprise, st.episode_id, st.episode_seq, "novel")
        st.last_ts = now
        if surprise < self.floor:
            st.habituated += 1
            return Decision(False, surprise, st.episode_id, st.episode_seq, "habituated")
        st.episode_seq += 1
        return Decision(True, surprise, st.episode_id, st.episode_seq, "novel")

    def to_dict(self) -> dict:
        # The knobs are INFORMATIONAL here: on restart the environment wins, and load()
        # deliberately does not read them. Named so nobody answers "what floor is this
        # daemon at" from the sidecar.
        return {"config_informational": {"floor": self.floor, "alpha": self.alpha,
                                         "boundary": self.boundary, "gap_seconds": self.gap_seconds},
                "sources": {k: v.to_dict() for k, v in self.sources.items()}}

    def load(self, d: Optional[dict]) -> None:
        if not d:
            return
        self.sources = {k: SourceState.from_dict(v) for k, v in (d.get("sources") or {}).items()}
