"""Turn-level deposit classifier.

Scores a (user_turn, assistant_turn) conversational pair for
fish-eat-worthiness. Use it as a gate in front of `linafish listen
stdin -n <fish>` so the corpus doesn't bloat with trivial chitchat.

The classifier scores three signals:

  1. Doctrine markers — regex patterns that flag "this turn is naming
     a rule, locking canon, or §-tagging a moment." Defaults include
     "new rule", "from now on", "don't/always/never", "doctrine",
     "canon", and "§TAG.LIKE.THIS".
  2. High-value tokens — substrings that mark domain-specific
     importance. No defaults (caller supplies their own; e.g. names
     of load-bearing people, places, or projects in their writing).
  3. Length — assistant turns over 1000 chars get a small bonus
     (long responses tend to carry more compression).

Each signal contributes to a score. Above DEPOSIT_THRESHOLD (default
1.5) the decision is to deposit; below, skip.

Routing tags are independent of the deposit decision: every turn gets
a tag (default "ambient") so downstream wiring can route to per-facet
fish in a future phase. Tag patterns are caller-supplied.

Origin: ported from anchor-chat-ui Phase 6 Task 53 into linafish 1.4.
The decoupling from anchor-specific defaults is the 1.4 generalization.

CLI: `linafish classify --user "..." --assistant "..."` prints
DepositDecision as JSON. Use `--jsonl` mode for batch over stdin.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class DepositDecision:
    """Output of classify(). JSON-serializable via dataclasses.asdict."""
    deposit: bool
    target_fish: str  # e.g. "anchor-writing" or "skip"
    routing_tag: str
    score: float
    reasons: list[str]


# Default doctrine-marker patterns. Generic English phrases that flag
# rule-locking, canon-declaring, or section-tagging turns.
#
# **Caveat for users:** the `\b(don'?t|always|never)\b` pattern is broad
# — ordinary English sentences like "I always enjoy coffee" or "I don't
# eat dairy" will trip it. The default set is tuned for journal/work
# corpora where these words usually signal a real rule-lock; for casual
# chat-heavy corpora you'll want to override with a narrower pattern
# (e.g. `\b(never again|always remember|don'?t do)\b`) via
# `--doctrine-marker` or by passing `doctrine_markers=` to classify().
DEFAULT_DOCTRINE_MARKERS = [
    r"\bnew rule\b",
    r"\bfrom now on\b",
    r"\b(don'?t|always|never)\b",
    r"§[A-Z][A-Z\.]+",
    r"\bdoctrine\b",
    r"\bcanon\b",
]

# Default high-value tokens. Empty by design — caller supplies the
# author-specific words that mark importance in their corpus.
DEFAULT_HIGH_VALUE_TOKENS: list[str] = []

# Default routing-tag patterns: {tag_name: [regex, ...]}. Empty by
# design — caller wires in per-target patterns if they want per-facet
# routing. Matches are checked in dict-iteration order; the LAST match
# wins. Use Python 3.7+ insertion-ordered dicts to control priority.
DEFAULT_ROUTING_TAGS: dict[str, list[str]] = {}

DEPOSIT_THRESHOLD = 1.5
DOCTRINE_MARKER_SCORE = 2.0
HVT_PER_HIT_SCORE = 1.0
LENGTH_BONUS_SCORE = 0.5
LENGTH_BONUS_THRESHOLD = 1000


def classify(
    user_turn: str,
    assistant_turn: str,
    *,
    doctrine_markers: Optional[list[str]] = None,
    high_value_tokens: Optional[list[str]] = None,
    routing_tags: Optional[dict[str, list[str]]] = None,
    target_fish_name: str = "linafish",
    deposit_threshold: float = DEPOSIT_THRESHOLD,
) -> DepositDecision:
    """Score a turn pair and return a DepositDecision.

    Args:
        user_turn: the user's text in this turn.
        assistant_turn: the assistant's text in this turn.
        doctrine_markers: regex patterns to score as doctrine-locks.
            Defaults to DEFAULT_DOCTRINE_MARKERS. First match per turn
            scores DOCTRINE_MARKER_SCORE; multiple matches do not stack.
        high_value_tokens: substrings (case-insensitive) to score as
            high-value mentions. Each unique hit scores HVT_PER_HIT_SCORE.
            Defaults to DEFAULT_HIGH_VALUE_TOKENS (empty).
        routing_tags: {tag_name: [regex, ...]}. Each tag whose patterns
            match assigns its name to routing_tag; later matches override
            earlier (dict-iteration order). Defaults to
            DEFAULT_ROUTING_TAGS (empty → tag stays "ambient").
        target_fish_name: name to put in target_fish when depositing.
            Defaults to "linafish".
        deposit_threshold: score gate. Defaults to DEPOSIT_THRESHOLD.

    Returns:
        DepositDecision with deposit (bool), target_fish (str), routing_tag
        (str), score (float), reasons (list[str]).
    """
    markers = doctrine_markers if doctrine_markers is not None else DEFAULT_DOCTRINE_MARKERS
    hvts = high_value_tokens if high_value_tokens is not None else DEFAULT_HIGH_VALUE_TOKENS
    tags = routing_tags if routing_tags is not None else DEFAULT_ROUTING_TAGS

    full = f"{user_turn}\n\n{assistant_turn}"
    full_lower = full.lower()
    reasons: list[str] = []
    score = 0.0

    # 1. Doctrine marker — first match scores; no stacking.
    for marker in markers:
        if re.search(marker, full, re.IGNORECASE):
            score += DOCTRINE_MARKER_SCORE
            reasons.append(f"doctrine-marker:{marker}")
            break

    # 2. High-value tokens — each unique hit scores.
    hvt_hits = [t for t in hvts if t.lower() in full_lower]
    if hvt_hits:
        score += HVT_PER_HIT_SCORE * len(hvt_hits)
        reasons.append(f"high-value-tokens:{','.join(hvt_hits)}")

    # 3. Length bonus.
    if len(assistant_turn) > LENGTH_BONUS_THRESHOLD:
        score += LENGTH_BONUS_SCORE
        reasons.append(f"length>{LENGTH_BONUS_THRESHOLD}")

    # 4. Routing tag — last match wins (dict-iteration order).
    routing_tag = "ambient"
    for tag_name, patterns in tags.items():
        if any(re.search(p, full, re.IGNORECASE) for p in patterns):
            routing_tag = tag_name

    deposit = score >= deposit_threshold
    return DepositDecision(
        deposit=deposit,
        target_fish=target_fish_name if deposit else "skip",
        routing_tag=routing_tag,
        score=score,
        reasons=reasons + [f"routing_tag:{routing_tag}"],
    )


def decision_as_dict(d: DepositDecision) -> dict:
    """Convert a DepositDecision to a plain dict suitable for JSON."""
    return asdict(d)
