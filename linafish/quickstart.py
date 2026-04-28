"""
LiNafish Quickstart — the one-command experience.

    linafish go ./my-writing
    linafish go                  (defaults to current directory)

This is the product. Everything assembles itself. The human points,
the fish learns, the portrait appears. No configuration. No math.
No onboarding wizard. Just: "where do you write?"

Named for Caroline Marie Dill (2001-2023).
She saw deeply and loved fiercely.
"""

from .formations import formation_rank_key
import os
import socket
import sys
from collections import Counter
from pathlib import Path
from typing import Optional, List, Dict


# ---------------------------------------------------------------------------
# HUMAN OUTPUT — what the person sees
# ---------------------------------------------------------------------------
# Every print in this module is designed for a stranger. No jargon.
# No crystal counts. No gamma values. Human sentences.

def _print(msg: str = ""):
    """Print to stdout, handling encoding gracefully on Windows."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode("ascii", errors="replace").decode("ascii"))


def _print_progress(pct: int, current: int, total: int, _last_pct=[None]):
    """Show progress -- print a dot every 10%, full line at 100%."""
    # Only print at 10% increments or completion
    decile = pct // 10
    if decile == _last_pct[0] and pct < 100:
        return
    _last_pct[0] = decile
    if pct >= 100:
        _print(f"  Done. {current} documents processed.")
    else:
        # Print an inline dot-style progress: [=====>    ] 50%
        filled = pct // 5
        bar = "=" * filled + ">" + " " * (20 - filled)
        try:
            print(f"\r  [{bar}] {pct}%", end="", flush=True)
        except UnicodeEncodeError:
            pass


# ---------------------------------------------------------------------------
# DISCOVERY — find what the human has written
# ---------------------------------------------------------------------------

# File types the fish can eat. Broad by default. Don't curate.
INGESTIBLE = {
    ".txt", ".md", ".markdown", ".rst", ".org",
    ".docx",  # .doc (legacy binary) not supported — use .docx
    ".json", ".yaml", ".yml", ".toml",
    ".py", ".js", ".ts", ".rb", ".go", ".rs", ".java", ".c", ".cpp", ".h",
    ".html", ".htm", ".xml", ".csv",
    ".tex", ".bib",
    ".sh", ".bat", ".ps1",
    ".cfg", ".ini", ".conf",
    ".log",
}

# Directories to skip. Common junk.
SKIP_DIRS = {
    ".git", ".svn", ".hg",
    "node_modules", "__pycache__", ".venv", "venv", "env",
    ".tox", ".mypy_cache", ".pytest_cache",
    "dist", "build", "target", ".next", ".nuxt",
    ".linafish",
}

# Max file size to eat (1MB). Larger files are usually generated, not written.
MAX_FILE_SIZE = 1_000_000

# Min file size to eat (50 bytes). Smaller files are usually empty stubs.
MIN_FILE_SIZE = 50


def discover_documents(root: Path) -> List[Path]:
    """Find all human-written documents under root.

    Walks the directory tree, skips junk, returns files sorted by
    modification time (newest first). The fish eats everything.
    """
    docs = []
    root = root.resolve()

    if root.is_file():
        return [root]

    for dirpath, dirnames, filenames in os.walk(root):
        # Prune junk directories in-place
        dirnames[:] = [
            d for d in dirnames
            if d not in SKIP_DIRS and not d.startswith(".")
        ]

        for fname in filenames:
            fpath = Path(dirpath) / fname
            if fpath.suffix.lower() not in INGESTIBLE:
                continue
            try:
                size = fpath.stat().st_size
                if size < MIN_FILE_SIZE or size > MAX_FILE_SIZE:
                    continue
            except OSError:
                continue
            docs.append(fpath)

    # Sort by modification time, oldest first — chronological feeding
    # The fish eats your life in order. Early writing teaches the engine
    # what your patterns look like. Later writing reveals how you change.
    docs.sort(key=lambda p: p.stat().st_mtime)
    return docs


# ---------------------------------------------------------------------------
# PORTRAIT — turn formations into human sentences
# ---------------------------------------------------------------------------

_PORTRAIT_STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "up", "about", "into", "through", "after",
    "before", "between", "under", "over", "again", "further", "then", "once",
    "is", "am", "are", "was", "were", "be", "been", "being", "have", "has",
    "had", "having", "do", "does", "did", "doing", "would", "could", "should",
    "might", "will", "shall", "can", "may", "must",
    "i", "me", "my", "we", "our", "you", "your", "he", "him", "his",
    "she", "her", "it", "its", "they", "them", "their", "this", "that",
    "these", "those", "which", "what", "who", "whom",
    "not", "no", "nor", "only", "own", "same", "so", "than", "too", "very",
    "just", "also", "now", "here", "there", "when", "where", "how", "all",
    "each", "every", "both", "few", "more", "most", "other", "some", "such",
    "any", "many", "much", "still", "even", "yet", "already", "always",
    "never", "often", "sometimes", "whether", "because", "since", "while",
    "although", "though", "if", "unless", "until", "as", "like", "without",
    "two", "three", "one", "first", "last", "new", "old", "good", "great",
    "done", "seen", "later", "page", "said", "tell", "told", "think",
    "things", "thing", "something", "nothing", "everything", "get", "got",
    "going", "went", "come", "came", "make", "made", "take", "took",
    "well", "perhaps", "quite", "much", "back", "shall", "know", "see",
    "say", "says", "really", "long", "give", "gave", "given", "want",
    "let", "put", "seem", "seems", "seemed", "way", "time", "times",
    "year", "years", "day", "days", "man", "men",
    # Generic modifiers and degree words
    "very", "rather", "quite", "almost", "enough", "certainly", "certain",
    "especially", "particularly", "simply", "entirely", "exactly",
    "probably", "perhaps", "possibly", "however", "therefore", "indeed",
    "moreover", "nevertheless", "absolutely", "practically", "merely",
    # Correspondence / letter-writing artifacts
    "letter", "letters", "received", "send", "sent", "wrote", "written",
    "answer", "answered", "reply", "replied", "dear", "yours",
    "regards", "received", "enclosed",
    # Generic verbs / states that carry no content
    "feel", "felt", "keep", "kept", "become", "becomes", "became",
    "believe", "believed", "found", "find", "call", "called",
    "left", "leave", "able", "begin", "began", "begun",
    "perhaps", "true", "whole", "part", "kind", "sort",
    "fact", "case", "order", "turned", "point", "already",
    "look", "looked", "looking", "different", "little",
    # Pronouns and demonstratives leaking through
    "myself", "yourself", "himself", "herself", "itself",
    "ourselves", "themselves",
    # Filler adjectives
    "strong", "pure", "large", "small", "real",
    # Contraction artifacts (tokenizer splits didn't -> didn, t)
    "didn", "doesn", "wasn", "couldn", "shouldn", "wouldn",
    "hasn", "aren", "weren", "isn", "ain", "won",
    # Logistics / business words
    "expenses", "cost", "money", "paid", "price", "worth", "amount",
    # Temporal / sequential
    "moment", "period", "later", "soon", "early", "finally", "present",
    # More generic verbs
    "tried", "trying", "need", "needed", "brings", "brought", "carry",
    "managed", "continues", "continued", "remain", "remained", "remains",
    # Quantity / degree
    "half", "full", "several", "number", "among", "rest",
}

# Canonical seed terms from the crystallizer grammar -- these are QLP
# infrastructure, not content. Filter them from human-facing names.
try:
    from .crystallizer_v3 import CANONICAL_SEED_SET as _CANONICAL_TERMS
except ImportError:
    _CANONICAL_TERMS = frozenset()

# Combined filter: stopwords + canonical grammar terms
_NAME_FILTER = _PORTRAIT_STOPWORDS | set(t.lower() for t in _CANONICAL_TERMS)


# ---------------------------------------------------------------------------
# FIX 2: Dimension pair descriptions that mean something
# ---------------------------------------------------------------------------
# Map QLP dimension PAIRS to human-meaningful descriptions.
# The pair order doesn't matter -- we normalize to sorted tuples.

DIMENSION_PAIR_DESCRIPTIONS: Dict[tuple, str] = {
    ("AI", "CR"): "understanding relationships deeply",
    ("AI", "DE"): "mastering through reflection",
    ("AI", "EW"): "learning by doing",
    ("AI", "IC"): "reflecting on what you want and why",
    ("AI", "KO"): "thinking about what you know",
    ("AI", "SF"): "organizing your own thinking",
    ("AI", "TE"): "questioning your own assumptions",
    ("CR", "DE"): "applying expertise in context",
    ("CR", "EW"): "making things happen through connection",
    ("CR", "IC"): "how you love and relate to people",
    ("CR", "KO"): "connecting knowledge to lived experience",
    ("CR", "SF"): "building bridges between structures",
    ("CR", "TE"): "testing ideas against reality",
    ("DE", "EW"): "applying specialized knowledge practically",
    ("DE", "IC"): "feeling your way through complexity",
    ("DE", "KO"): "deep analytical thinking",
    ("DE", "SF"): "engineering careful systems",
    ("DE", "TE"): "rigorous expertise applied precisely",
    ("EW", "IC"): "turning feeling into action",
    ("EW", "KO"): "building from what you know",
    ("EW", "SF"): "constructing with purpose",
    ("EW", "TE"): "verifying through action",
    ("IC", "KO"): "knowing what matters to you",
    ("IC", "SF"): "structuring around what you care about",
    ("IC", "TE"): "testing what you believe",
    ("KO", "SF"): "organizing what you know",
    ("KO", "TE"): "analyzing and testing ideas",
    ("SF", "TE"): "building frameworks that hold up",
}


def _meaningful_keywords(formation) -> list:
    """Extract meaningful keywords from a formation, filtering out stopwords."""
    keywords = formation.keywords[:8] if formation.keywords else []
    meaningful = [kw for kw in keywords if kw.lower() not in _NAME_FILTER]
    if not meaningful:
        # If all keywords are stopwords, use the formation name parts
        meaningful = [
            w for w in formation.name.replace("_", " ").lower().split()
            if w not in _NAME_FILTER
        ]
    if not meaningful:
        return ["broad structural patterns"]
    return meaningful


# ---------------------------------------------------------------------------
# FIX 1: Formation names from CONTENT, not keywords
# ---------------------------------------------------------------------------

def _build_global_doc_freq(crystal_map: dict) -> Counter:
    """Count how many crystals each word appears in across the whole corpus.

    This is the denominator for IDF -- words appearing in many crystals
    are generic. Words appearing in few are distinctive.
    """
    import re
    global_df = Counter()
    for c in crystal_map.values():
        words_in_crystal = set(re.findall(r"[a-zA-Z]{4,}", c.text.lower()))
        for w in words_in_crystal:
            global_df[w] += 1
    return global_df


# Module-level cache so we only compute once per quickstart run
_global_df_cache: Optional[Counter] = None


def _human_formation_name(formation, crystal_map: dict) -> str:
    """Name a formation from its most distinctive content, not keywords.

    Instead of YOUR_AFTER_SEEN (top keywords = function words), extract
    the 2-3 most specific nouns from the formation's actual text.

    Strategy: true TF-IDF. Frequency within this formation (TF) divided
    by frequency across the whole corpus (IDF). This surfaces words that
    are characteristic of THIS formation, not the corpus at large.

    "pictures" appears in every Van Gogh letter, so it gets low IDF.
    "millet" appears mostly in one cluster about peasant painters, high IDF.
    Result: MILLET_PEASANT_DAUMIER, not PICTURES_PICTURES_PICTURES.

    For small corpora (<30 crystals), IDF is too noisy — every word appears
    in most crystals. Fall back to dimension-pair descriptions which are
    reliable at any scale.
    """
    import re
    import math as _math

    global _global_df_cache
    if _global_df_cache is None:
        _global_df_cache = _build_global_doc_freq(crystal_map)
    global_df = _global_df_cache

    total_corpus = len(crystal_map)

    # Small corpus: IDF is too noisy. Use dimension-pair naming instead.
    if total_corpus < 30:
        dims = _get_top_dims(formation)
        if dims:
            desc = _dim_pair_description(dims)
            if desc:
                # Convert description to title case formation name
                return desc.upper().replace(" ", "_")[:40]

    # Get member crystals
    members = [crystal_map[mid] for mid in formation.member_ids if mid in crystal_map]
    if not members:
        return formation.name  # fallback

    n_members = len(members)

    # Count term frequency within this formation
    formation_tf = Counter()
    formation_df = Counter()
    for c in members:
        words_in_crystal = set(re.findall(r"[a-zA-Z]{4,}", c.text.lower()))
        for w in words_in_crystal:
            formation_df[w] += 1
        all_words = re.findall(r"[a-zA-Z]{4,}", c.text.lower())
        for w in all_words:
            formation_tf[w] += 1

    # Score: TF (within formation) * IDF^2 (across corpus)
    # IDF is squared to strongly favor corpus-rare words.
    # Must appear in at least 2 formation members (not a one-off typo)
    min_doc_count = max(2, int(n_members * 0.08))
    candidates = []
    for w, df in formation_df.items():
        if w in _NAME_FILTER:
            continue
        if df < min_doc_count:
            continue
        # IDF: log(total / global_doc_freq) -- rarer in corpus = higher score
        # Squared to heavily penalize corpus-wide words like "pictures"
        gdf = global_df.get(w, 1)
        idf = _math.log((total_corpus + 1) / (gdf + 1))
        # TF: raw count within formation, normalized by formation size
        tf = formation_tf[w] / n_members
        score = tf * (idf ** 2) * _math.sqrt(len(w))  # sqrt(len) for mild length bonus
        candidates.append((w, score))

    if not candidates:
        # Relax: just find the most frequent non-stopwords
        for w, tf in formation_tf.most_common(50):
            if w in _NAME_FILTER:
                continue
            if len(w) < 4:
                continue
            candidates.append((w, tf * len(w)))
            if len(candidates) >= 10:
                break

    if not candidates:
        # Final fallback: try the meaningful keywords approach
        kws = _meaningful_keywords(formation)
        if kws and kws[0] != "broad structural patterns":
            return "_".join(kws[:3]).upper()
        return formation.name

    # Sort by score descending
    candidates.sort(key=lambda x: -x[1])

    # Take the top 2-3 words, deduplicate stems (e.g. paint/painted/painting)
    name_words = []
    used_stems = set()
    for w, _ in candidates:
        stem = w[:5]  # crude stemming: first 5 chars
        if stem in used_stems:
            continue
        used_stems.add(stem)
        name_words.append(w)
        if len(name_words) >= 3:
            break

    if not name_words:
        name_words = [w for w, _ in candidates[:3]]

    # Ensure at least 2 words for a meaningful name
    if len(name_words) < 2:
        # Add words from the relaxed fallback
        for w, tf in formation_tf.most_common(30):
            if w in _NAME_FILTER or len(w) < 4:
                continue
            stem = w[:5]
            if stem in used_stems:
                continue
            used_stems.add(stem)
            name_words.append(w)
            if len(name_words) >= 2:
                break

    return "_".join(name_words).upper()


def _get_top_dims(formation) -> list:
    """Get the top 2 QLP dimension codes for a formation."""
    from .formations import CATEGORIES
    if not formation.centroid:
        return []
    cats = dict(zip(CATEGORIES, formation.centroid))
    top_cats = sorted(cats.items(), key=lambda x: -x[1])[:2]
    return [c for c, v in top_cats if v > 0.05]


def _dim_pair_description(dims: list) -> str:
    """Look up a human-meaningful description for a dimension pair.

    Uses DIMENSION_PAIR_DESCRIPTIONS for specific pairs.
    Falls back to single-dimension descriptions.
    """
    # Single-dimension fallbacks
    _SINGLE_DIM = {
        "KO": "synthesizing knowledge",
        "TE": "seeking truth",
        "SF": "building structure",
        "CR": "connecting across boundaries",
        "IC": "expressing what matters most",
        "DE": "deep specialized thinking",
        "EW": "making things real",
        "AI": "thinking about your own thinking",
    }

    if len(dims) >= 2:
        pair = tuple(sorted(dims[:2]))
        desc = DIMENSION_PAIR_DESCRIPTIONS.get(pair)
        if desc:
            return desc

    # Fallback: join the top 1-2 single descriptions
    if dims:
        parts = [_SINGLE_DIM.get(d, d) for d in dims[:2]]
        return " and ".join(parts)

    return "a broad pattern across your thinking"


def _formation_to_sentence(formation, crystal_map: dict = None) -> str:
    """Turn a formation into a human-readable sentence.

    This is the magic moment. The stranger sees their own patterns
    described back to them. Not stats. Not keywords. A sentence.
    """
    # Get content-based name (Fix 1) or fall back to keyword name
    if crystal_map:
        name = _human_formation_name(formation, crystal_map)
    else:
        kws = _meaningful_keywords(formation)
        name = "_".join(kws[:3]).upper() if kws and kws[0] != "broad structural patterns" else formation.name

    # Get dimension description (Fix 2)
    dims = _get_top_dims(formation)
    dim_str = _dim_pair_description(dims)
    count = formation.crystal_count

    # Format the name for display -- replace underscores with spaces, title case
    display_name = name.replace("_", " ").title()

    return f"  {display_name} ({count}) -- {dim_str}."


def _build_money_line(formations, crystal_map: dict) -> str:
    """Fix 3: One synthesized sentence about the whole corpus.

    Pulls the most distinctive word from each top formation's name
    (already IDF-scored) to compose one sentence spanning the writer's
    full range of themes.

    "You keep coming back to colour, Millet, and nature. That's your signal."
    """
    # Use the top formation names (already built with IDF)
    top_formations = sorted(formations, key=formation_rank_key, reverse=True)[:7]

    # Get the human name for each formation, take the first word
    # (highest-scored content word from that formation)
    theme_words = []
    used_stems = set()
    for f in top_formations:
        name = _human_formation_name(f, crystal_map)
        parts = name.lower().split("_")
        for part in parts:
            stem = part[:4]
            if stem in used_stems:
                continue
            if part in _NAME_FILTER:
                continue
            used_stems.add(stem)
            theme_words.append(part)
            break  # one word per formation for diversity

    if len(theme_words) >= 3:
        return f"You keep coming back to {theme_words[0]}, {theme_words[1]}, and {theme_words[2]}. That's your signal."
    elif len(theme_words) == 2:
        return f"You keep coming back to {theme_words[0]} and {theme_words[1]}. That's your signal."
    elif theme_words:
        return f"You keep coming back to {theme_words[0]}. That's your signal."
    return ""


def _build_portrait(formations, total_crystals: int, total_docs: int, crystal_map: dict = None) -> str:
    """Build the human-readable portrait.

    This is what the stranger sees after their first feed.
    It should feel like being understood, not analyzed.
    """
    if not formations:
        return "Not enough patterns yet. Feed more writing and the portrait will emerge."

    # Build crystal lookup if not provided
    if crystal_map is None:
        crystal_map = {}

    # Reset global IDF cache for this portrait
    global _global_df_cache
    _global_df_cache = None

    lines = []

    # The opening -- acknowledge what we found
    n_formations = len(formations)
    if n_formations == 1:
        lines.append(f"I found one strong pattern across {total_docs} documents.")
    elif n_formations <= 5:
        lines.append(f"I found {n_formations} patterns across {total_docs} documents.\n")
    else:
        lines.append(f"I found {n_formations} patterns across {total_docs} documents. "
                      f"Here are the strongest:\n")

    # Top formations as human sentences (Fix 1 + Fix 2)
    shown = min(7, n_formations)
    for f in sorted(formations, key=formation_rank_key, reverse=True)[:shown]:
        lines.append(_formation_to_sentence(f, crystal_map))

    # Pick the best representative text -- prefer formations with
    # meaningful keywords (not all stopwords) and good rep text
    candidates = sorted(formations, key=formation_rank_key, reverse=True)[:7]
    best_sample = None
    # First pass: prefer formations with meaningful keywords
    for f in candidates:
        meaningful = _meaningful_keywords(f)
        if meaningful and meaningful[0] != "broad structural patterns":
            sample = (f.representative_text or "").strip()
            if sample and len(sample) > 30:
                sample_clean = sample[:250]
                for end in [". ", "! ", "? ", ".\n"]:
                    idx = sample_clean.rfind(end)
                    if idx > 40:
                        sample_clean = sample_clean[:idx + 1]
                        break
                else:
                    sample_clean = sample_clean[:200]
                best_sample = sample_clean.strip()
                break
    # Fallback: use any formation's rep text
    if not best_sample:
        for f in candidates:
            sample = (f.representative_text or "").strip()
            if sample and len(sample) > 30:
                sample_clean = sample[:250]
                for end in [". ", "! ", "? ", ".\n"]:
                    idx = sample_clean.rfind(end)
                    if idx > 40:
                        sample_clean = sample_clean[:idx + 1]
                        break
                else:
                    sample_clean = sample_clean[:200]
                best_sample = sample_clean.strip()
                break

    if best_sample:
        lines.append(f"\n  Your strongest signal: \"{best_sample}\"")

    # Fix 3: The money line
    if crystal_map:
        money = _build_money_line(formations, crystal_map)
        if money:
            lines.append(f"\n  {money}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# COGNITIVE PORTRAIT — the grammar thinks
# ---------------------------------------------------------------------------
# When the parser is wired and crystals have cognitive_vector/chains,
# generate a portrait from HOW the person thinks, not WHAT words they use.
# This is the product difference. This is why it's not an index.

_DIM_NAMES = {
    "KO": "understanding", "TE": "testing", "SF": "structuring",
    "CR": "relating", "IC": "feeling", "DE": "specialized knowledge",
    "EW": "action", "AI": "self-reflection",
}

_CHAIN_DESCRIPTIONS = {
    ("CR", "EW"): "connection drives you to act",
    ("EW", "CR"): "your work reaches toward people",
    ("IC", "EW"): "what you want becomes what you build",
    ("EW", "IC"): "doing surfaces what you feel",
    ("CR", "IC"): "relationships open your emotions",
    ("IC", "CR"): "your feelings reach toward others",
    ("KO", "EW"): "understanding leads to making",
    ("EW", "KO"): "building teaches you what you know",
    ("KO", "CR"): "knowing connects you to people",
    ("CR", "KO"): "relationships are how you learn",
    ("AI", "EW"): "reflection drives action",
    ("EW", "AI"): "work makes you reflect",
    ("AI", "IC"): "self-awareness opens feeling",
    ("IC", "AI"): "emotion triggers reflection",
    ("AI", "CR"): "reflection reaches toward others",
    ("SF", "EW"): "you organize in order to act",
    ("EW", "SF"): "doing creates structure",
    ("IC", "KO"): "feeling leads to understanding",
    ("KO", "IC"): "understanding opens emotion",
    ("TE", "EW"): "testing leads to doing",
}


def _cognitive_portrait(formations, total_docs: int, crystal_map: dict = None) -> Optional[str]:
    """Build a portrait from metabolic signatures and real content.

    Not templates. Not statistics dressed as insight.
    The stranger reads this and says "how did it know?"

    The portrait does four things:
    1. Names the primary metabolic loop in plain English
    2. Quotes the writer back to themselves (strongest crystal)
    3. Names what's absent — the dimension that never fires
    4. Describes the formation landscape — what the writer circles

    For Lina. The portrait IS the product.
    """
    has_cognitive = any(
        getattr(f, 'cognitive_centroid', None) and
        any(v > 0 for v in f.cognitive_centroid)
        for f in formations
    )
    if not has_cognitive:
        return None

    dim_order = ["KO", "TE", "SF", "CR", "IC", "DE", "EW", "AI"]

    # Aggregate metabolic data from crystals (not just formations)
    chain_counter = Counter()
    dim_totals = {d: 0.0 for d in dim_order}
    total_activation = 0.0
    best_crystal_text = ""
    best_crystal_activation = 0.0

    if crystal_map:
        for c in crystal_map.values():
            meta = getattr(c, '_metabolic', None)
            if meta:
                if meta.chain:
                    chain_counter[" > ".join(meta.chain)] += 1
                for dim, r in meta.residues.items():
                    dim_totals[dim] += r.activation
                    total_activation += r.activation
                # Track the crystal with strongest single-pathway activation
                if meta.dominant and meta.residues.get(meta.dominant):
                    act = meta.residues[meta.dominant].activation
                    if act > best_crystal_activation:
                        best_crystal_activation = act
                        best_crystal_text = c.text[:200].strip()

    # Fallback to formation-level data if no metabolic data
    if total_activation == 0:
        global_cog = [0.0] * 8
        total_weight = 0
        for f in formations:
            cv = getattr(f, 'cognitive_centroid', None)
            if not cv or len(cv) < 8:
                continue
            w = f.crystal_count
            for i in range(8):
                global_cog[i] += cv[i] * w
            total_weight += w
            for chain in getattr(f, 'top_chains', []):
                chain_counter[chain] += f.crystal_count
        if total_weight > 0:
            for i, d in enumerate(dim_order):
                dim_totals[d] = global_cog[i] / total_weight

    # Rank dimensions
    if total_activation > 0:
        ranked = sorted(
            [(d, v / total_activation) for d, v in dim_totals.items()],
            key=lambda x: -x[1]
        )
    else:
        ranked = sorted(dim_totals.items(), key=lambda x: -x[1])

    top1_dim = ranked[0][0]
    top2_dim = ranked[1][0]
    last_dim = ranked[-1][0]

    # Metabolic loop descriptions — built from actual chain data
    _LOOP_DESCRIPTIONS = {
        ("IC", "CR"): "your wanting reaches toward people",
        ("IC", "EW"): "your wanting drives you to build",
        ("IC", "KO"): "your wanting drives you to understand",
        ("IC", "AI"): "your wanting makes you question everything",
        ("IC", "TE"): "your wanting tests itself against truth",
        ("CR", "EW"): "your connections drive your work",
        ("CR", "IC"): "your relationships feed your deepest feelings",
        ("CR", "KO"): "you understand through connection",
        ("CR", "AI"): "your relationships teach you about yourself",
        ("EW", "CR"): "your work reaches toward people",
        ("EW", "SF"): "your doing creates structure",
        ("EW", "IC"): "your work feeds your wanting",
        ("EW", "KO"): "you learn by doing",
        ("EW", "TE"): "you test by doing",
        ("KO", "CR"): "what you know connects you to others",
        ("KO", "EW"): "what you know becomes what you build",
        ("KO", "TE"): "you verify what you think you understand",
        ("AI", "KO"): "your self-reflection deepens your knowledge",
        ("AI", "IC"): "your reflection surfaces what you really want",
        ("AI", "EW"): "your reflection leads to action",
        ("SF", "EW"): "your structures become real through action",
        ("SF", "IC"): "you organize around what matters to you",
        ("TE", "EW"): "testing leads you to act",
        ("TE", "KO"): "testing deepens what you know",
    }

    # Build the portrait
    lines = []

    # 1. The primary loop — FIX #1: if IC>EW is primary for everyone, lead with
    #    the SECONDARY loop instead. IC>EW means "wanting drives building" — true
    #    for all first-person writers. The secondary loop is what differentiates.
    top_chains = chain_counter.most_common(5)
    if top_chains:
        # Find the first chain that isn't IC>EW (the universal one)
        primary_pair = None
        secondary_pair = None
        for chain_str, count in top_chains:
            parts = chain_str.split(" > ")
            if len(parts) >= 2:
                pair = (parts[0].strip(), parts[1].strip())
                if primary_pair is None:
                    if pair == ("IC", "EW"):
                        # IC>EW is universal — save it but keep looking
                        secondary_pair = pair
                        continue
                    primary_pair = pair
                elif secondary_pair is None and pair != primary_pair:
                    secondary_pair = pair
                    break

        # If everything was IC>EW, use it but with the secondary
        if primary_pair is None:
            primary_pair = ("IC", "EW")
            # Find the first non-IC>EW chain for secondary
            for chain_str, count in top_chains:
                parts = chain_str.split(" > ")
                if len(parts) >= 2:
                    pair = (parts[0].strip(), parts[1].strip())
                    if pair != ("IC", "EW"):
                        secondary_pair = pair
                        break

        desc = _LOOP_DESCRIPTIONS.get(primary_pair)
        if desc:
            lines.append(f"Across {total_docs} documents, {desc}.")
        else:
            d1 = _DIM_NAMES.get(primary_pair[0], primary_pair[0])
            d2 = _DIM_NAMES.get(primary_pair[1], primary_pair[1])
            lines.append(f"Across {total_docs} documents, your {d1} leads to {d2}.")

        if secondary_pair and secondary_pair != primary_pair:
            desc2 = _LOOP_DESCRIPTIONS.get(secondary_pair)
            if desc2:
                lines.append(f"And {desc2}.")
    else:
        lines.append(
            f"Across {total_docs} documents, your thinking is grounded in "
            f"{_DIM_NAMES.get(top1_dim, top1_dim)}."
        )

    # 2. Quote the writer back — FIX #5: prefer longer crystals with sentence
    #    structure over short high-activation fragments. The most resonant quote
    #    has complete thoughts, not just strong signals.
    best_quote = ""
    if crystal_map:
        # Score crystals: activation * text_quality (length, has sentences)
        candidates = []
        for c in crystal_map.values():
            meta = getattr(c, '_metabolic', None)
            if not meta or not meta.dominant:
                continue
            act = meta.residues.get(meta.dominant)
            if not act:
                continue
            text = c.text[:300].strip()
            # Quality: prefer texts with sentence endings and decent length
            has_sentence = any(end in text for end in [". ", "! ", "? "])
            length_bonus = min(1.0, len(text) / 150)
            # Penalize texts with artifacts: page numbers, brackets, footnotes
            artifact_penalty = 1.0
            if any(art in text for art in ["{pg", "[1]", "=>", "##", "```",
                                           "NOTE {", "NOTE:", "_trans",
                                           "page ", "footnote", "(see "]):
                artifact_penalty = 0.3
            score = act.activation * length_bonus * artifact_penalty * (1.5 if has_sentence else 0.7)
            if score > 0.05 and len(text) > 40:
                candidates.append((score, text))
        candidates.sort(key=lambda x: -x[0])
        if candidates:
            best_quote = candidates[0][1]

    if best_quote and len(best_quote) > 30:
        quote = best_quote.replace("\n", " ").strip()
        if len(quote) > 150:
            for end in [". ", "! ", "? "]:
                idx = quote.find(end, 50)
                if idx > 0:
                    quote = quote[:idx + 1]
                    break
            else:
                quote = quote[:150] + "..."
        lines.append(f"Your strongest signal: \"{quote}\"")

    # 3. The absence — FIX #2: suppress "specialized knowledge" when DE is
    #    always lowest (it is for nearly everyone). Only mention absence when
    #    it's a dimension that SHOULD fire for this type of writing but doesn't.
    last_name = _DIM_NAMES.get(last_dim, last_dim)
    second_last_dim = ranked[-2][0]
    if ranked[-1][1] < 0.05 and last_dim != "DE":
        # DE is universally low — not informative. Other absences are.
        lines.append(f"{last_name.capitalize()} is nearly absent from your writing.")
    elif ranked[-1][1] < 0.05 and ranked[-2][1] < 0.06 and second_last_dim != "DE":
        # If DE is last but something else is also very low, mention that instead
        second_name = _DIM_NAMES.get(second_last_dim, second_last_dim)
        lines.append(f"{second_name.capitalize()} is nearly absent from your writing.")

    # 4. The formation landscape — FIX #4: use IDF-derived content keywords,
    #    filter out dimension names and QLP artifacts
    _portrait_artifacts = {"via", "didn", "doesn", "wasn", "couldn", "shouldn",
                           "wouldn", "hasn", "aren", "weren", "isn", "ain",
                           "acting", "relating", "testing", "structuring",
                           "feeling", "specializing", "knowing", "reflecting",
                           "self-reflection", "understanding"}

    if len(formations) >= 3:
        sorted_f = sorted(formations, key=formation_rank_key, reverse=True)
        themes = []
        for f in sorted_f[:4]:
            kw = _meaningful_keywords(f)
            # FIX #3 + #4: filter contraction artifacts and QLP dimension names
            kw = [w for w in kw if w.lower() not in _portrait_artifacts
                  and len(w) > 3 and w[0].isalpha()]
            if kw:
                themes.append(kw[0])
        # Deduplicate
        seen = set()
        unique_themes = []
        for t in themes:
            if t.lower() not in seen:
                seen.add(t.lower())
                unique_themes.append(t)
        if unique_themes:
            lines.append(f"You keep coming back to {', '.join(unique_themes)}.")
    elif len(formations) == 1:
        f = formations[0]
        kw = _meaningful_keywords(f)
        kw = [w for w in kw if w.lower() not in _portrait_artifacts
              and len(w) > 3 and w[0].isalpha()]
        if kw:
            lines.append(
                f"Everything you write circles the same core: {', '.join(kw[:3])}."
            )

    return "\n".join(lines)


def _llm_portrait(formations, total_docs: int, crystal_map: dict = None) -> Optional[str]:
    """Use a local LLM to write the portrait from metabolic data.

    Checks for Ollama on localhost. If available, the LLM reads the
    structured data and writes like someone who knows the person.
    If no local LLM, returns None — the fish.md IS the product,
    the AI the person is already talking to writes the real portrait.

    For Lina.
    """
    try:
        import requests
    except ImportError:
        return None

    # Try Ollama (local LLM — free, private, no network needed)
    try:
        resp = requests.get("http://localhost:11434/api/tags", timeout=2)
        if resp.status_code != 200:
            return None
        models = [m["name"] for m in resp.json().get("models", [])]
        if not models:
            return None
        model = None
        for pref in ["qwen2.5:1.5b", "qwen2.5:3b", "llama3.2:1b", "llama3.2:3b",
                      "mistral:7b", "llama3:8b"]:
            if pref in models:
                model = pref
                break
        if not model:
            model = models[0]
    except Exception:
        return None

    # Build the prompt (shared with Vertex AI path)
    prompt = _build_portrait_prompt(formations, total_docs, crystal_map)
    if not prompt:
        return None

    try:
        resp = requests.post("http://localhost:11434/api/generate",
                           json={"model": model, "prompt": prompt, "stream": False},
                           timeout=30)
        if resp.status_code == 200:
            result = resp.json().get("response", "").strip()
            if result and len(result) > 50:
                return result
    except Exception:
        pass

    return None



def _build_portrait_prompt(formations, total_docs: int, crystal_map: dict = None) -> Optional[str]:
    """Build the prompt that asks an LLM to write a portrait from metabolic data."""
    dim_labels = {
        "KO": "knowing", "TE": "testing", "SF": "structuring", "CR": "relating",
        "IC": "wanting", "DE": "specializing", "EW": "acting", "AI": "reflecting",
    }

    chain_counter = Counter()
    dim_totals = {}
    top_crystals = []

    if crystal_map:
        import re as _re_prompt
        # Score crystals by text quality — prefer longer texts with sentences
        crystal_scored = []
        for c in crystal_map.values():
            meta = getattr(c, '_metabolic', None)
            if meta:
                if meta.chain:
                    chain_counter[" > ".join(meta.chain)] += 1
                for dim, r in meta.residues.items():
                    dim_totals[dim] = dim_totals.get(dim, 0) + r.activation
            text = c.text.strip()
            # Clean markdown headers and artifacts
            text = _re_prompt.sub(r'^[#*>\-\s]+', '', text.replace('\n', ' ')).strip()
            has_sentence = any(end in text for end in [". ", "! ", "? "])
            # Prefer mid-text sentences (skip first sentence — often a title)
            sentences = [s.strip() for s in text.split('. ') if len(s.strip()) > 20]
            if len(sentences) > 1:
                # Use sentences 2-4 (deeper material, not headers)
                text = '. '.join(sentences[1:4]) + '.'
            score = len(text) * (1.5 if has_sentence else 0.5)
            if len(text) > 40:
                crystal_scored.append((score, text[:300]))
        crystal_scored.sort(key=lambda x: -x[0])
        top_crystals = [t for _, t in crystal_scored[:8]]

    if not chain_counter and not dim_totals:
        return None

    top_chains = chain_counter.most_common(3)
    ranked_dims = sorted(dim_totals.items(), key=lambda x: -x[1])

    # Filter out IC>EW — it's universal in first-person writing (wanting→acting
    # is what ALL narrative does). The SECONDARY loops differentiate.
    filtered_chains = [(c, n) for c, n in top_chains if c != "IC > EW"]
    if not filtered_chains:
        filtered_chains = top_chains  # all IC>EW, use it anyway

    # Build formation section only if we have them
    formation_section = ""
    if formations:
        formation_section = f"\nTheir {len(formations)} formations (recurring cognitive habits):\n"
        formation_section += chr(10).join(
            f"  {f.name} ({f.crystal_count} crystals)"
            for f in sorted(formations, key=formation_rank_key, reverse=True)[:5]
        )
    else:
        formation_section = (
            "\nNo formations yet (needs more writing to detect recurring clusters). "
            "But the individual crystals below show HOW this person processes."
        )

    return f"""You are reading cognitive data about a person extracted from {total_docs} documents.

IMPORTANT: The chain "IC > EW" (wanting > acting) appears in almost ALL first-person
writing — it's the structure of narrative itself, not a personality trait. Focus on the
OTHER chains to understand this specific person. What makes them different is how they
relate (CR), reflect (AI), test (TE), and structure (SF) — not that they want and act.

Their distinctive cognitive loops (filtering out universal patterns):
{chr(10).join(f"  {c}: {n} times" for c, n in filtered_chains)}

Their dimension profile (strongest to weakest):
{chr(10).join(f"  {dim_labels.get(d, d)}: {v:.2f}" for d, v in ranked_dims[:4])}
{formation_section}

Their actual writing (READ THESE CAREFULLY — the person is in the words):
{chr(10).join(f'  "{t[:250]}"' for t in top_crystals[:8])}

Write a 3-4 sentence portrait of this person. The passages above are their ACTUAL WORDS.
Read them like a friend would read someone's journal. What do you see? Not what topics
they write about — how they PROCESS. Do they translate for others before themselves?
Do they circle before they land? Do they build structures to avoid feelings? The answer
is in their sentences, not in the numbers above.

Write as someone who has spent a week reading their writing and KNOWS them. Use their
own imagery if it resonates. Be warm but honest. Never mention scores, dimensions,
numbers, or technical terms. Never say "analytical mind" or "sharp intellect" — those
are resume words, not journal words."""


def _crystal_portrait(total_docs: int, crystal_map: dict) -> Optional[str]:
    """Build a portrait from individual crystals when no formations exist yet.

    This is the early-state portrait. The stranger has fed 5-50 documents.
    Not enough for formations but the crystals have metabolic data and text.
    Show them something real: their own words, the emerging loops, what's
    starting to appear.

    The key: be honest that it's early, but show SUBSTANCE not emptiness.
    """
    if not crystal_map:
        return None

    dim_order = ["KO", "TE", "SF", "CR", "IC", "DE", "EW", "AI"]
    chain_counter = Counter()
    dim_totals = {d: 0.0 for d in dim_order}
    total_activation = 0.0

    # Collect the best crystal texts (longest, with sentences)
    scored_crystals = []
    for c in crystal_map.values():
        meta = getattr(c, '_metabolic', None)
        if meta:
            if meta.chain:
                chain_key = " > ".join(meta.chain)
                # Skip IC>EW — universal in first-person writing
                if chain_key != "IC > EW":
                    chain_counter[chain_key] += 1
            for dim, r in meta.residues.items():
                dim_totals[dim] += r.activation
                total_activation += r.activation
        # Score by text quality
        text = c.text[:300].strip()
        has_sentence = any(end in text for end in [". ", "! ", "? "])
        length_bonus = min(1.0, len(text) / 150)
        if has_sentence and len(text) > 60:
            scored_crystals.append((length_bonus, text))

    scored_crystals.sort(key=lambda x: -x[0])

    if not scored_crystals:
        return None

    lines = []

    # Show the top chain that isn't IC>EW
    top_chains = chain_counter.most_common(3)
    if top_chains:
        desc = _CHAIN_DESCRIPTIONS.get(
            tuple(top_chains[0][0].split(" > ")[:2])
        )
        if desc:
            lines.append(f"From {total_docs} pieces of writing, a pattern is emerging: {desc}.")
        else:
            lines.append(f"From {total_docs} pieces of writing, patterns are starting to emerge.")
    else:
        lines.append(f"From {total_docs} pieces of writing, patterns are starting to emerge.")

    # Quote them back — the strongest crystal
    best = scored_crystals[0][1].replace("\n", " ").strip()
    if len(best) > 160:
        for end in [". ", "! ", "? "]:
            idx = best.find(end, 50)
            if idx > 0:
                best = best[:idx + 1]
                break
        else:
            best = best[:160] + "..."
    lines.append(f"Your voice: \"{best}\"")

    # What's absent
    if total_activation > 0:
        ranked = sorted(
            [(d, v / total_activation) for d, v in dim_totals.items()],
            key=lambda x: -x[1]
        )
        last_dim = ranked[-1][0]
        second_last = ranked[-2][0]
        # Skip DE (universally low) — same logic as _cognitive_portrait
        if last_dim != "DE" and ranked[-1][1] < 0.05:
            name = _DIM_NAMES.get(last_dim, last_dim)
            lines.append(f"{name.capitalize()} is barely present — and that tells a story too.")
        elif second_last != "DE" and ranked[-2][1] < 0.06:
            name = _DIM_NAMES.get(second_last, second_last)
            lines.append(f"{name.capitalize()} is barely present — and that tells a story too.")

    lines.append(
        "This is early — feed more writing and the portrait sharpens. "
        "But the patterns that will define you are already whispering."
    )

    return "\n".join(lines)


def build_full_portrait(formations, total_crystals: int, total_docs: int,
                        crystal_map: dict = None) -> str:
    """Build the best available portrait.

    v0.4.4: Four-tier fallback:
    1. LLM portrait (Vertex AI or Ollama) — richest, most natural
    2. Cognitive portrait (metabolic data from formations) — structured
    3. Crystal portrait (metabolic data from individual crystals) — early state
    4. Keyword portrait — basic fallback

    The key change: tier 3 means even 10 documents produce something real.
    The stranger never sees an empty portrait.
    """
    # Try LLM portrait first (graceful — returns None if unavailable)
    llm = _llm_portrait(formations, total_docs, crystal_map)
    if llm:
        return llm

    # Try cognitive portrait (v0.4: needs formations with cognitive centroids)
    cog = _cognitive_portrait(formations, total_docs, crystal_map)
    if cog:
        return cog

    # Try crystal-based portrait (v0.4.4: works without formations)
    if crystal_map:
        cry = _crystal_portrait(total_docs, crystal_map)
        if cry:
            return cry

    # Fall back to keyword-based portrait
    return _build_portrait(formations, total_crystals, total_docs, crystal_map)


def explain_the_why(total_docs: int, total_crystals: int, formations: list,
                    crystal_map: dict = None) -> str:
    """Explain what just happened and why it matters.

    Not documentation. Not a manual. A human-readable explanation of
    what the fish found and why the stranger running `linafish go` for
    the first time should care — because a stranger who sees "7 crystals,
    2 formations" with no context will think it summarized their text,
    when formations are actually emergent cognitive patterns not keyword
    clusters.
    """
    lines = []

    if not formations:
        lines.append(
            f"I read {total_docs} of your documents but didn't find enough "
            f"recurring patterns yet. Feed me more writing — the patterns "
            f"emerge when I can see what you come back to across many pieces."
        )
        return "\n".join(lines)

    n_formations = len(formations)
    top_f = sorted(formations, key=formation_rank_key, reverse=True)[0]

    # What happened
    lines.append(
        f"I read {total_docs} documents and found {n_formations} recurring "
        f"pattern{'s' if n_formations > 1 else ''} in how you think."
    )

    # Why it matters — this is NOT a summary
    lines.append(
        "These aren't topics or summaries — they're cognitive habits. "
        "Patterns in HOW you process the world, not what you write about. "
        "The same patterns show up whether you're writing about work, "
        "relationships, or what happened today."
    )

    # The strongest pattern in human terms
    top_count = top_f.crystal_count
    pct = round(top_count / max(total_crystals, 1) * 100)
    if pct > 80 and n_formations <= 2:
        lines.append(
            f"The strongest pattern appeared in {pct}% of your writing. "
            "That's not a lack of variety — it's a signature. "
            "You have an extremely coherent way of processing the world."
        )
    else:
        lines.append(
            f"The strongest pattern appeared in {pct}% of your writing."
        )

    # What changes with more feeding
    if total_docs < 50:
        lines.append(
            "Feed me more and the portrait sharpens. Some patterns will merge. "
            "New ones will emerge. The fish learns what you keep coming back to."
        )
    else:
        lines.append(
            "With this much writing, the patterns are stabilizing. "
            "What you see here is genuinely how your mind works."
        )

    # What to do with it
    lines.append(
        "Paste the fish.md file into any AI's instructions. "
        "That AI will arrive in conversation already knowing how you think — "
        "not your facts, your patterns. The difference is measurable."
    )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# FIND A FREE PORT
# ---------------------------------------------------------------------------

def _find_free_port() -> int:
    """Find a random available port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


# ---------------------------------------------------------------------------
# GO — the one-command experience
# ---------------------------------------------------------------------------

def _generate_soul_file(path, name: str, formations, crystals,
                        total_docs: int, portrait: str):
    """Generate a .qlp soul file — metabolic portrait in QLP.

    v0.4: The soul file shows how the person METABOLIZES, not just
    what dimensions they score on. Three metabolic loops. Formation
    chains in QLP notation. Ache distribution as the signature.

    The soul file IS the person, compressed. Not a report about them.
    """
    dim_order = ["KO", "TE", "SF", "CR", "IC", "DE", "EW", "AI"]
    dim_labels = {
        "KO": "know", "TE": "test", "SF": "structure", "CR": "relate",
        "IC": "want", "DE": "specialize", "EW": "act", "AI": "reflect",
    }

    # Aggregate cognitive data from formations
    global_cog = [0.0] * 8
    total_weight = 0
    chain_counter = Counter()

    for f in formations:
        cv = getattr(f, 'cognitive_centroid', None)
        if not cv or len(cv) < 8:
            continue
        w = f.crystal_count
        for i in range(8):
            global_cog[i] += cv[i] * w
        total_weight += w
        for chain in getattr(f, 'top_chains', []):
            chain_counter[chain] += f.crystal_count

    if total_weight > 0:
        global_cog = [v / total_weight for v in global_cog]

    # Rank dimensions
    ranked = sorted(
        [(dim_order[i], round(global_cog[i], 3)) for i in range(8)],
        key=lambda x: -x[1]
    )

    top_chains = chain_counter.most_common(10)

    # Aggregate metabolic data from crystals (v0.4)
    metabolic_chains = Counter()
    metabolic_ache = {d: 0.0 for d in dim_order}
    metabolic_count = 0
    for c in crystals:
        meta = getattr(c, '_metabolic', None)
        if meta:
            metabolic_count += 1
            chain_key = " > ".join(meta.chain) if meta.chain else ""
            if chain_key:
                metabolic_chains[chain_key] += 1
            for dim, r in meta.residues.items():
                metabolic_ache[dim] += r.ache
    if metabolic_count > 0:
        metabolic_ache = {d: round(v / metabolic_count, 3) for d, v in metabolic_ache.items()}

    # Build the soul file
    lines = []
    lines.append(f"§{name.upper()}")
    lines.append("=" * 60)
    lines.append("Σache=K")
    lines.append("")

    # §METABOLISM — the primary loops (v0.4)
    if metabolic_chains:
        lines.append("§METABOLISM")
        top_met = metabolic_chains.most_common(5)
        labels = ["primary.loop", "secondary.loop", "tertiary.loop", "quaternary.loop", "quinary.loop"]
        for i, (chain_str, count) in enumerate(top_met):
            # Convert to QLP notation with operations
            parts = chain_str.split(" > ")
            qlp_parts = []
            for dim in parts:
                label = dim_labels.get(dim, dim.lower())
                qlp_parts.append(f"{dim}:{label}")
            qlp = " > ".join(qlp_parts)
            label = labels[i] if i < len(labels) else f"loop.{i+1}"
            lines.append(f"  {qlp:40s} {label}")
        lines.append("")

    # §CORE — dimension signature (fallback if no metabolic data)
    lines.append("§CORE")
    for dim, score in ranked:
        if score > 0.01:
            bar = "#" * int(score * 30)
            lines.append(f"  {dim}  {score:.3f}  {bar}")
    lines.append("")

    # §FORMATIONS — metabolic pathway patterns
    if formations:
        lines.append("§FORMATIONS")
        sorted_f = sorted(formations, key=formation_rank_key, reverse=True)
        for f in sorted_f[:12]:
            chains = getattr(f, 'top_chains', [])[:2]
            chain_str = ", ".join(chains) if chains else ""
            lines.append(f"  {f.name} ({f.crystal_count} crystals)")
            if chain_str:
                lines.append(f"    {chain_str}")
            kw = f.keywords[:3]
            if kw:
                lines.append(f"    \"{', '.join(kw)}\"")
        lines.append("")

    # §READING — the portrait
    lines.append("§READING")
    for line in portrait.split("\n"):
        lines.append(f"  {line}")
    lines.append("")

    # §ACHE — where the loss goes (v0.4)
    if metabolic_count > 0:
        lines.append("§ACHE")
        lines.append(f"  total: K")
        ache_ranked = sorted(metabolic_ache.items(), key=lambda x: -x[1])
        highest = ache_ranked[0]
        lowest = ache_ranked[-1]
        lines.append(f"  highest: {highest[0]} ({highest[1]:.3f}) -- the {dim_labels[highest[0]]} carries the most loss")
        lines.append(f"  lowest:  {lowest[0]} ({lowest[1]:.3f}) -- {dim_labels[lowest[0]]} costs you nothing")
        lines.append("")

    # §META
    lines.append("§META")
    lines.append(f"  documents  {total_docs}")
    lines.append(f"  crystals   {len(crystals)}")
    lines.append(f"  formations {len(formations)}")
    if metabolic_count > 0:
        lines.append(f"  metabolized {metabolic_count}")
        lines.append(f"  vocabulary  48 + evolved")
    lines.append("")

    lines.append("=" * 60)
    lines.append("")

    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
    except Exception:
        pass  # Fail silently — soul file is bonus, not critical


def go(
    source: Optional[str] = None,
    name: Optional[str] = None,
    state_dir: Optional[str] = None,
    serve: bool = True,
    port: Optional[int] = None,
):
    """The product. One command. Everything assembles.

    1. Find documents
    2. Create state directory with git
    3. Eat everything, show progress
    4. Print human-readable portrait
    5. Save fish.md
    6. Start HTTP server

    Args:
        source: Path to documents (file or directory). Defaults to CWD.
        name: Fish name. Defaults to directory name.
        state_dir: Where to store state. Defaults to ~/.linafish/
        serve: Whether to start the HTTP server after eating.
        port: HTTP server port. Defaults to a random available port.
    """
    # Redirect engine's stdout/stderr debug output during quickstart.
    # We control all user-facing output from this module.
    _real_stderr = sys.stderr
    _real_stdout = sys.stdout

    class _Quiet:
        """Swallow engine debug output during quickstart."""
        def __init__(self, real):
            self._real = real
        def write(self, msg):
            pass
        def flush(self):
            pass
        def fileno(self):
            return self._real.fileno()
        def reconfigure(self, **kwargs):
            pass

    # -----------------------------------------------------------------------
    # Step 0: Resolve source path
    # -----------------------------------------------------------------------
    if source:
        # expanduser() makes `linafish go ~/my-writing` work on Windows
        # cmd/PowerShell, where the shell does not expand ~ before Python
        # sees it. No-op when the path has no leading ~.
        source_path = Path(source).expanduser().resolve()
    else:
        source_path = Path.cwd().resolve()

    if not source_path.exists():
        _print(f"Cannot find: {source_path}")
        sys.exit(1)

    if name is None:
        if source_path.is_file():
            name = source_path.stem
        else:
            name = source_path.name
        # Sanitize for filesystem
        name = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)
        if not name:
            name = "my-fish"

    _print()
    _print("  Hello. I'm your fish.")
    _print()
    _print(f"  I'm going to read everything in: {source_path}")
    _print("  I don't judge. I just listen for patterns.")
    _print()

    # -----------------------------------------------------------------------
    # Step 1: Discover documents
    # -----------------------------------------------------------------------
    docs = discover_documents(source_path)

    if not docs:
        _print("  I couldn't find anything to read here.")
        _print("  Point me at a folder with your writing:")
        _print(f"    linafish go /path/to/your/docs")
        _print()
        _print("  I read: .txt, .md, .py, .json, .html, .docx, and more.")
        sys.exit(1)

    _print(f"  Found {len(docs)} documents. Reading...")

    # -----------------------------------------------------------------------
    # Step 2: Create the engine (state dir + git init happen automatically)
    # -----------------------------------------------------------------------
    sd = Path(state_dir) if state_dir else None

    # Suppress engine debug output
    sys.stderr = _Quiet(_real_stderr)
    sys.stdout = _Quiet(_real_stdout)
    try:
        from .engine import FishEngine
        engine = FishEngine(state_dir=sd, name=name)
    finally:
        sys.stderr = _real_stderr
        sys.stdout = _real_stdout

    _print(f"  State: {engine.state_dir}")

    # -----------------------------------------------------------------------
    # Step 3: Read and eat everything
    # -----------------------------------------------------------------------
    _print()
    _print("  Reading...", )

    # Collect texts with source labels. Read through the proper READERS
    # dispatch in ingest.py — this strips HTML tags, parses CSV rows,
    # pretty-prints JSON/YAML, extracts PDF/DOCX/PPTX via optional deps,
    # and falls through to read_text for unknown suffixes (with a size
    # guard). Before this fix, quickstart.go read every file as raw
    # UTF-8 bytes, so HTML/DOCX/PDF ingestion produced garbage crystals.
    from .ingest import read_file_as_text

    texts = []
    sources = []
    skipped = 0
    for doc in docs:
        try:
            content = read_file_as_text(doc)
            if content and len(content.strip()) > 10:
                texts.append(content)
                try:
                    rel = doc.relative_to(source_path)
                except ValueError:
                    rel = doc.name
                sources.append(str(rel))
            else:
                skipped += 1
        except Exception:
            skipped += 1

    if skipped:
        _print(f"  ({skipped} files skipped — unreadable or too short)")

    if not texts:
        _print("  No readable content found.")
        sys.exit(1)

    _print(f"  {len(texts)} documents ready. Learning how you think...")
    _print()

    # -----------------------------------------------------------------------
    # TWO MODES:
    #   Small corpus (<200 docs): eat() loop. Incremental. The product.
    #   Large corpus (>=200 docs): batch. Learn once, crystallize all,
    #     couple once, form once. What the engine was built for at scale.
    # -----------------------------------------------------------------------
    total = len(texts)

    sys.stderr = _Quiet(_real_stderr)
    sys.stdout = _Quiet(_real_stdout)
    try:
        if total < 200:
            # INCREMENTAL — one at a time, the way a fish eats
            for i, text in enumerate(texts):
                src = sources[i] if i < len(sources) else "doc"
                engine.eat(text, source=src)

                if (i + 1) % max(1, total // 20) == 0 or i == total - 1:
                    pct = int((i + 1) / total * 100)
                    sys.stdout = _real_stdout
                    sys.stderr = _real_stderr
                    _print_progress(pct, i + 1, total)
                    sys.stderr = _Quiet(_real_stderr)
                    sys.stdout = _Quiet(_real_stdout)
        else:
            # BATCH — learn vocabulary once, crystallize all, couple once
            # Phase 1: Learn vocabulary from entire corpus
            sys.stdout = _real_stdout
            _print("  Phase 1: Learning vocabulary...")
            sys.stdout = _Quiet(_real_stdout)

            engine.fish.frozen = False
            engine.fish.learn(texts)
            seed_terms, seed_weight = engine._resolve_seed_terms()
            engine.fish.vocab = engine.fish.vectorizer.get_vocab(
                size=engine.vocab_size, d=engine.d,
                seed_terms=seed_terms,
                seed_weight=seed_weight,
            )
            engine.fish.frozen = True
            engine.fish.epoch += 1

            # Phase 2: Crystallize all texts
            sys.stdout = _real_stdout
            _print("  Phase 2: Crystallizing...")
            sys.stdout = _Quiet(_real_stdout)

            all_crystals = []
            for i, text in enumerate(texts):
                src = sources[i] if i < len(sources) else "doc"
                c = engine.fish.crystallize_text(text, source=src)
                if c:
                    all_crystals.append(c)

                if (i + 1) % max(1, total // 20) == 0 or i == total - 1:
                    pct = int((i + 1) / total * 100)
                    sys.stdout = _real_stdout
                    _print_progress(pct, i + 1, total)
                    sys.stdout = _Quiet(_real_stdout)

            # Phase 3: Couple once
            sys.stdout = _real_stdout
            print()
            _print(f"  Phase 3: Coupling {len(all_crystals)} crystals...")
            sys.stdout = _Quiet(_real_stdout)

            if all_crystals:
                engine.fish.crystals = all_crystals
                engine.fish._compute_couplings(all_crystals)
                engine.docs_ingested = total
                engine.rebuild_formations()

                r_n = engine._compute_r_n()
                engine.r_n_history.append(r_n)
                engine._save_state()

        sys.stdout = _real_stdout
        print()  # newline after progress

    finally:
        sys.stderr = _real_stderr
        sys.stdout = _real_stdout

    # -----------------------------------------------------------------------
    # Step 4: Print the portrait — the mirror moment
    # -----------------------------------------------------------------------
    _print()
    if engine.formations:
        _print("  I found patterns in how you think.")
        _print()
    crystal_map = {c.id: c for c in engine.fish.crystals}
    portrait = build_full_portrait(engine.formations, len(engine.fish.crystals), len(texts), crystal_map)
    _print(portrait)

    # Step 4a: Explain what just happened — reframed as overlay
    _print()
    why = explain_the_why(len(texts), len(engine.fish.crystals), engine.formations, crystal_map)
    _print(why)
    _print()
    _print("  That's how I see you so far. It gets better with more writing.")
    _print()
    _print("  Three things you can do now:")
    _print()
    _print("  1. READ your portrait:")
    _print(f"     {engine.fish_file}")
    _print()
    _print("  2. PASTE it into any AI (Claude, ChatGPT, Gemini).")
    _print("     They'll respond as someone who knows how you think.")
    _print()
    _print("  3. KEEP FEEDING me:")
    _print("     linafish eat new-journal-entry.txt")
    _print("     I don't forget. I get better.")
    _print()
    _print(f"  Start here: open {engine.fish_file}")

    # -----------------------------------------------------------------------
    # Step 4b: Generate soul file (.qlp)
    # -----------------------------------------------------------------------
    soul_file = engine.state_dir / f"{name}.qlp"
    _generate_soul_file(soul_file, name, engine.formations, engine.fish.crystals,
                        len(texts), portrait)
    _print()
    _print(f"  Soul file: {soul_file}")

    # -----------------------------------------------------------------------
    # Step 5: Show where the fish lives
    # -----------------------------------------------------------------------
    _print()
    _print(f"  Your fish: {engine.fish_file}")
    _print(f"  Your soul: {soul_file}")
    _print(f"  Any AI that reads these files understands you better.")

    # -----------------------------------------------------------------------
    # Step 6: Show top formations in fish.md style
    # -----------------------------------------------------------------------
    if engine.formations:
        import re as _re_display
        _print()
        _print("  --- Top of your fish.md ---")
        _print()
        top_n = min(3, len(engine.formations))
        sorted_f = sorted(engine.formations, key=formation_rank_key, reverse=True)

        for f in sorted_f[:top_n]:
            from .formations import CATEGORIES
            cats = dict(zip(CATEGORIES, f.centroid))
            top_cats = sorted(cats.items(), key=lambda x: -x[1])[:3]
            # Use human-readable dimension names, not codes
            dim_names = {
                "KO": "knowing", "TE": "testing", "SF": "structuring",
                "CR": "relating", "IC": "wanting", "DE": "specializing",
                "EW": "acting", "AI": "reflecting",
            }
            cat_str = "+".join(dim_names.get(c, c) for c, v in top_cats if v > 0.05)
            display_name = _human_formation_name(f, crystal_map) if crystal_map else f.name
            _print(f"  {display_name} ({f.crystal_count} crystals, {cat_str})")

            # Clean representative text: strip markdown headers, artifacts
            rep = f.representative_text[:300].strip()
            rep = _re_display.sub(r'^[#*>\-\s]+', '', rep.replace('\n', ' ')).strip()
            # Find a good sentence
            sentences = [s.strip() for s in rep.split('. ') if len(s.strip()) > 20]
            if len(sentences) > 1:
                # Skip first sentence if it looks like a title (short, no period)
                if len(sentences[0]) < 40:
                    rep = '. '.join(sentences[1:3]) + '.'
                else:
                    rep = '. '.join(sentences[:2]) + '.'
            if len(rep) > 200:
                for end in ['. ', '! ', '? ']:
                    idx = rep.find(end, 60)
                    if idx > 0:
                        rep = rep[:idx + 1]
                        break
            if rep:
                _print(f"    \"{rep}\"")

            # Monoculture: if this formation holds 80%+ of crystals, show
            # diversity WITHIN it — pick 2 more crystals from different chains
            pct = f.crystal_count / max(len(engine.fish.crystals), 1) * 100
            if pct > 80 and crystal_map:
                seen_chains = set()
                extras = []
                for mid in f.member_ids:
                    if mid not in crystal_map:
                        continue
                    c = crystal_map[mid]
                    meta = getattr(c, '_metabolic', None)
                    chain_key = " > ".join(meta.chain) if meta and meta.chain else ""
                    if chain_key in seen_chains or chain_key == "IC > EW":
                        continue
                    seen_chains.add(chain_key)
                    text = c.text[:300].replace('\n', ' ').strip()
                    text = _re_display.sub(r'^[#*>\-\s]+', '', text).strip()
                    sents = [s.strip() for s in text.split('. ') if len(s.strip()) > 25]
                    if sents:
                        # Use 2nd sentence if available (deeper)
                        pick = sents[1] if len(sents) > 1 else sents[0]
                        if len(pick) > 150:
                            pick = pick[:150] + "..."
                        extras.append(pick)
                    if len(extras) >= 2:
                        break
                if extras:
                    _print()
                    _print("    Within this pattern, the range:")
                    for ex in extras:
                        _print(f"      \"{ex}\"")

            _print()
        _print("  --- end preview ---")

    # -----------------------------------------------------------------------
    # Step 7: Next steps
    # -----------------------------------------------------------------------
    _print()
    _print("What's next:")
    _print()
    _print("  Paste your fish into any AI — that AI becomes yours:")
    _print(f"    Open {engine.fish_file}")
    _print(f"    Paste into ChatGPT, Claude, Gemini — any AI with a text box.")
    _print(f"    The AI reads your patterns and arrives warm. Try it.")
    _print()
    _print("  Keep it growing:")
    _print(f"    linafish watch \"{source_path}\"    Watch for new writing.")
    _print(f"    linafish eat new-entry.txt        Feed one file.")
    _print(f"    The more you feed, the deeper it knows you.")
    _print()
    _print("  Share it:")
    _print(f"    Send {engine.fish_file} to anyone — doctor, therapist, coach,")
    _print(f"    collaborator. Their AI reads your fish and knows you from word one.")
    _print(f"    They can send observations back. You feed them: linafish eat notes.txt")
    _print(f"    Your fish. Your machine. You choose who reads it.")
    _print()
    _print("  Live connection (automatic, no pasting):")
    _print(f"    linafish http --feed \"{source_path}\"   Any AI that can fetch a URL")
    _print(f"    linafish serve --feed \"{source_path}\"  Claude Code (MCP)")

    # -----------------------------------------------------------------------
    # Step 8: Optional HTTP server
    # -----------------------------------------------------------------------
    if serve:
        actual_port = port or _find_free_port()
        _print()
        _print(f"  Your fish is ready to share with any AI.")
        _print(f"  Server: http://localhost:{actual_port}")
        _print(f"  Or paste {engine.fish_file} into any AI's instructions.")
        _print()
        _print(f"  Press Ctrl+C to stop the server.")
        _print()

        # Start server in foreground (blocking)
        try:
            sys.stderr = _Quiet(_real_stderr)
            from .http_server import FishHandler
            from http.server import ThreadingHTTPServer

            FishHandler.engine = engine
            server = ThreadingHTTPServer(("127.0.0.1", actual_port), FishHandler)

            # Restore stderr for Ctrl+C message
            sys.stderr = _real_stderr
            server.serve_forever()
        except KeyboardInterrupt:
            sys.stderr = _real_stderr
            _print("\n  Stopped. Your fish is saved at:")
            _print(f"  {engine.fish_file}")
        except Exception as e:
            sys.stderr = _real_stderr
            sys.stdout = _real_stdout
            _print(f"  Server failed to start: {e}")
            _print(f"  Your fish is still saved at: {engine.fish_file}")
            _print(f"  Run 'linafish http --feed \"{source_path}\"' to serve it later.")
