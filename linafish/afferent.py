#!/usr/bin/env python3
"""linafish.afferent — the afferent SCHOOL organ.

Given a prompt, name which subfish (school member) is relevant — so an agent can
surface that specialist's knowledge into its context each turn. A nervous system
for a school of fish: one cheap lookup routes attention to the right member.

THE HARD CONSTRAINT — not CPU-gated. The per-turn path must do NO heavy compute:
no recall, no model encode, no GPU, no per-turn re-vectorize. So a topic
fingerprint per member is PRECOMPUTED ONCE into an index; per-turn routing is a
sub-millisecond in-memory dict lookup. The organ is meant to run on a solar Pi.
Heavy work (the index build) is a rare, deliberate, offline step.

ROUTING — always CURATED (route on a topic->member keyword map).
  Per-turn routing counts keyword hits against each member's interest map (with
  a member-name match as a higher tier), NOT frequency magnitude. Two ways the
  map is obtained:
  - SUPPLIED (best): an `afferent_topics.json` in the school dir (or passed to
    `surface_for`/`build_index`) naming each member's topic keywords. Routes
    correctly even when members' crystals overlap heavily (e.g. a school whose
    members all skim one broadcast stream).
  - AUTO-DERIVED (zero-config fallback): if no map is supplied, `build_index`
    derives a starter map from each member's TF-IDF-*distinctive* mined vocab
    and flags `topics_auto`. Good enough to route, but noisier than a curated
    map — the CLI says so and points you at `afferent_topics.json`.

  Why not route on the mined frequency directly? Because summing TF-IDF
  magnitude is not comparable across members of different corpus sizes: a small
  member's incidental word outweighs a large member's on-topic word (measured —
  `qlp_grammar`/113cr beat the `sister` fish/10073cr on "sister"), and for
  members that all ate one stream the topic signal is not statistically
  recoverable by ANY frequency method (measured). `_mined_scores` is retained
  only as the vocab-mining step behind the auto-derived map, not a live route.

SNIPPETS. When a member wakes under CURATED routing, the organ can surface one
on-topic crystal: the window centered on the matched keyword, harvested at build
time. Centering on the keyword makes the snippet about the topic by
construction — immune to off-topic but high-ache crystals.

USAGE
    from linafish.afferent import build_index, surface_for
    build_index("/path/to/school", "/path/to/school/afferent_index.json")
    woke = surface_for("reset the billing webhook", "/path/to/school/afferent_index.json")
    # -> [("billing", ["billing", "webhook"], "...snippet about the webhook..."), ...]

CLI
    python -m linafish.afferent build  <school_dir> [index_path]
    python -m linafish.afferent route  <index_path> "<prompt>"
"""
import os
import re
import sys
import json
import glob
import math
from collections import Counter

TOP_VOCAB = 30
DIMS = {"KO", "TE", "SF", "CR", "IC", "DE", "EW", "AI"}
WAKE_MIN = 1            # >=1 curated keyword hit = the member is relevant
_TOK = re.compile(r"[a-z]{3,}")
_STOP = {
    "the", "and", "for", "you", "your", "are", "but", "with", "this", "that",
    "have", "was", "her", "she", "his", "him", "they", "what", "how", "why",
    "into", "out", "off", "over", "very", "not", "all", "can", "got", "get",
    "now", "one", "two", "let", "use", "its", "has", "had", "our", "from",
    "image", "prompt", "seed", "text", "full", "open", "long", "past", "same",
    "read", "built", "build", "close", "morning", "night", "live", "first",
    "day", "name", "today", "tonight", "thing", "here", "made", "work", "still",
    "way", "then", "back", "more", "just", "like", "about", "would", "could",
    "been", "were", "who", "them", "did", "does", "ask", "said", "say", "next",
    "last", "good", "real", "true", "wrote", "write", "session", "memory",
}

# crystals that are not human prose — drop from snippet harvest (a code/json
# dump reads as noise in a snippet).
_JUNK_PREFIX = ("# oid sha256", "version https://git-lfs", "oid sha256:",
                "{", "[", "<", "def ", "import ", "```", "---", "http")


def _tok(s):
    return [t for t in _TOK.findall((s or "").lower()) if t not in _STOP]


def _is_prose(txt):
    t = (txt or "").lstrip()
    if not t or t.startswith(_JUNK_PREFIX):
        return False
    head = t[:200]
    if "oid sha256:" in head[:60] or "git-lfs" in head[:60]:
        return False
    if sum(head.count(ch) for ch in '{}[]":`=') > 8:
        return False
    words = head.split()
    if not words:
        return False
    alpha = sum(1 for w in words if w and sum(ch.isalpha() for ch in w) >= len(w) * 0.6)
    return alpha >= len(words) * 0.6


def _crystals_file(d, name):
    for cand in (f"{name}_crystals.jsonl", "crystals.jsonl"):
        p = os.path.join(d, cand)
        if os.path.exists(p):
            return p
    hits = glob.glob(os.path.join(d, "*_crystals.jsonl"))
    return hits[0] if hits else None


def _norm_kws(v):
    """Coerce a member's keyword list to clean, matchable form: lowercase, str
    only, non-empty. Drops non-strings (e.g. a hand-edited port number) that
    would otherwise crash `kw in pl` on every route call, and lowercases so a
    keyword like "RCP" isn't silently unmatchable against a lowercased prompt."""
    out = []
    for kw in v:
        if isinstance(kw, str):
            k = kw.strip().lower()
            if k:
                out.append(k)
    return out


def load_topics(school_dir):
    """Load a topic->member keyword map from <school_dir>/afferent_topics.json,
    or return {} (→ build auto-derives one). Format: {"member": ["kw", ...]}."""
    p = os.path.join(school_dir, "afferent_topics.json")
    if os.path.exists(p):
        try:
            with open(p, encoding="utf-8") as fh:
                d = json.load(fh)
            return {k: _norm_kws(v) for k, v in d.items()
                    if isinstance(v, (list, tuple))}
        except Exception:
            return {}
    return {}


def _scan_member(cf, topic_kws=()):
    """Full vocab Counter + dims + per-keyword on-topic snippet for one member."""
    vocab, dims, kw_best, n = Counter(), Counter(), {}, 0
    single_kws = [k for k in topic_kws if " " not in k]
    try:
        with open(cf, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    c = json.loads(line)
                except json.JSONDecodeError:
                    continue
                n += 1
                kws = c.get("keywords") or []
                if kws:
                    for kw in kws:
                        for t in _tok(str(kw)):
                            vocab[t] += 1
                else:
                    for t in _tok(c.get("text") or c.get("content") or "")[:120]:
                        vocab[t] += 1
                mods = c.get("modifiers") or {}
                for k, v in mods.items():
                    if k in DIMS:
                        try:
                            dims[k] += float(v)
                        except (TypeError, ValueError):
                            pass
                txt = " ".join((c.get("text") or c.get("content") or "").split())
                if txt and single_kws and _is_prose(txt):
                    try:
                        ache = float(c.get("ache") or 0)
                    except (TypeError, ValueError):
                        ache = 0.0
                    low = txt.lower()
                    toks = set(_TOK.findall(low))
                    for kw in single_kws:
                        if kw in toks and ache >= kw_best.get(kw, (-1.0,))[0]:
                            pos = low.find(kw)
                            start = max(0, pos - 45)
                            window = ("..." if start else "") + txt[start:pos + 95]
                            kw_best[kw] = (ache, window)
    except OSError:
        return None
    if not n:
        return None
    return vocab, dims, {k: v[1] for k, v in kw_best.items()}, n


def build_index(school_dir, index_path, topics=None, exclude=()):
    """Scan every member subfish under school_dir and write a precomputed index.

    topics: {member: [keywords]} for snippet harvest + the curated route map. If
    None, loaded from <school_dir>/afferent_topics.json. exclude: member names to
    skip. The index stores, per member: TF-IDF-distinctive vocab (the raw
    material an auto-derived interest map is built from when no map is supplied,
    minus the member's own name tokens), per-keyword on-topic snippets, crystal
    count. Routing is always CURATED; see the module docstring.
    """
    if topics is None:
        topics = load_topics(school_dir)
    exclude = set(exclude)
    raw = {}
    for d in sorted(glob.glob(os.path.join(school_dir, "*"))):
        if not os.path.isdir(d):
            continue
        name = os.path.basename(d)
        if name in exclude or ".bak" in name:
            continue
        cf = _crystals_file(d, name)
        if not cf:
            continue
        scanned = _scan_member(cf, topics.get(name, ()))
        if scanned:
            raw[name] = scanned
    if not raw:
        return {"_meta": {"n_members": 0, "df": {}}, "members": {}}

    # member-frequency: how many members contain each word at all (for TF-IDF).
    N = len(raw)
    member_df = Counter()
    for vocab, *_ in raw.values():
        for w in vocab:
            member_df[w] += 1

    members = {}
    for name, (vocab, dims, kw_snips, n) in raw.items():
        total = sum(vocab.values()) or 1
        scored = []
        for w, c in vocab.items():
            if c < 2:
                continue
            idf = math.log((N + 1) / member_df[w])
            if idf <= 0:
                continue
            scored.append(((c / total) * idf, w, c))
        scored.sort(reverse=True)
        top = scored[:TOP_VOCAB]
        if not top:
            continue
        members[name] = {
            "n_crystals": n,
            "vocab": [w for _, w, _ in top],
            "vocab_freq": {w: round((c / total) * math.log((N + 1) / member_df[w]) * 1000, 2)
                           for _, w, c in top},
            "dims": {k: round(v, 2) for k, v in dims.most_common()},
            "kw_snippets": kw_snips,
        }
    df = Counter()
    for fp in members.values():
        for w in fp["vocab"]:
            df[w] += 1

    # Zero-config routing: if no curated interest map was supplied, derive a
    # starter one from each member's mined distinctive vocab so `surface_for`
    # routes CURATED (hit-count, name-weighted) — NOT MINED. MINED sums
    # frequency-magnitude, which small-corpus members provably hijack and which
    # cannot separate filtered-view schools at all (members that skim one
    # primary stream share its vocab; measured — see module docstring). The
    # derived map is a floor; a hand-curated afferent_topics.json still wins.
    topics_auto = False
    if not topics:
        # Derive from mined vocab, but EXCLUDE each member's own name tokens: a
        # concept-named facet's own name is exactly what TF-IDF selects (high tf
        # in-member, rare across — measured), so without this it re-enters as a
        # "keyword" and defeats surface_for's wake-guard, reproducing the very
        # bare-name over-fire the guard exists to stop. The name still routes via
        # the name-tier whenever a genuine OTHER keyword also hits.
        _nsplit = re.compile(r"[_\-.]")
        topics = {}
        for name, fp in members.items():
            own = {p for p in _nsplit.split(name) if len(p) > 3}
            topics[name] = [w for w in fp["vocab"] if w not in own]
        topics_auto = True

    out = {"_meta": {"n_members": len(members), "df": dict(df),
                     "topics": topics, "topics_auto": topics_auto},
           "members": members}
    if index_path:
        os.makedirs(os.path.dirname(os.path.abspath(index_path)), exist_ok=True)
        with open(index_path, "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=1)
        _CACHE.pop(index_path, None)  # a rebuilt index must not serve stale from cache
    return out


def _curated_scores(prompt, topics):
    """Route by curated topic keywords. Returns {member: (score, matched_kws)}
    where score is a ``(name_match, n_keyword_hits)`` tuple, compared high-first.

    A member wakes ONLY on a real topic-keyword hit — a bare mention of its NAME
    is not sufficient. Otherwise members whose names are ordinary words
    (`desk`, `paper`, `boot`, `comms`) fire on incidental prose ("the paper on
    my desk"). But WHEN a member already has a keyword hit, a match on its name
    lifts it into a strictly higher tier: a fish named for the subject wins its
    subject over any rival carrying only incidental keyword hits, no matter how
    many. Measured: without the tier, `sister` lost "sister" to `automation` on
    keyword volume; with a flat bonus, three stray hits still beat it. The tier
    is order- and volume-independent."""
    pl = (prompt or "").lower()
    ptoks = set(_TOK.findall(pl))
    name_split = re.compile(r"[_\-.]")
    matched = {}
    for member, kws in topics.items():
        # word-boundary match: "art class" must not fire on "start classes", and
        # digit/hyphen/short keywords ("n8n", "raw-archive", "ai") that can't
        # survive the [a-z]{3,} tokenizer still match. keywords are lowercased by
        # _norm_kws (supplied) / _tok (auto-derived).
        hit = [kw for kw in kws if re.search(r"\b" + re.escape(kw) + r"\b", pl)]
        if not hit:
            continue  # no topic keyword → not relevant; a name mention is noise
        name_match = any(len(p) > 3 and p in ptoks for p in name_split.split(member))
        matched[member] = ((1 if name_match else 0, len(hit)), hit)
    return matched


def _mined_scores(prompt, members, df):
    """Route by TF-IDF distinctive vocab. Returns {member: score}. Use only when
    members are topic-pure (see module docstring)."""
    ptoks = _tok(prompt)
    scores = {}
    for name, fp in members.items():
        vf = fp["vocab_freq"]
        s = sum(vf[t] * (1.0 / df.get(t, 1)) for t in ptoks if t in vf)
        if s > 0:
            scores[name] = s
    return scores


_CACHE = {}


def surface_for(prompt, index_path, k=2, mined_threshold=4.0):
    """The afferent call: cheap lookup naming the relevant member(s). Returns
    [(name, matched_or_score, snippet), ...] or []. Routes CURATED on the index's
    topic map (supplied or auto-derived at build); the legacy MINED frequency
    path runs only for the degenerate index with no map at all. Loads + caches
    the index once."""
    if not prompt:
        return []
    idx = _CACHE.get(index_path)
    if idx is None:
        try:
            with open(index_path, encoding="utf-8") as fh:
                idx = json.load(fh)
        except OSError:
            return []
        _CACHE[index_path] = idx
    members = idx.get("members", {})
    topics = idx.get("_meta", {}).get("topics") or {}

    if topics:                       # CURATED
        matched = _curated_scores(prompt, topics)
        ranked = sorted(matched.items(), key=lambda x: x[1][0], reverse=True)
        out = []
        for name, (score, kws) in ranked:
            if len(out) >= k:          # honor k, incl. the degenerate k<=0
                break
            if len(kws) < WAKE_MIN:
                continue
            snips = members.get(name, {}).get("kw_snippets") or {}
            snip = next((snips[kw][:120] for kw in kws if kw in snips), "")
            out.append((name, kws, snip))
        return out

    # MINED
    df = idx.get("_meta", {}).get("df", {})
    scores = _mined_scores(prompt, members, df)
    return [(name, round(s, 1), "")
            for name, s in sorted(scores.items(), key=lambda x: -x[1])[:k]
            if s >= mined_threshold]


def _cli():
    args = sys.argv[1:]
    if len(args) >= 2 and args[0] == "build":
        school_dir = args[1]
        index_path = args[2] if len(args) >= 3 else os.path.join(school_dir, "afferent_index.json")
        idx = build_index(school_dir, index_path)
        n = idx["_meta"]["n_members"]
        mode = "auto-curated" if idx["_meta"].get("topics_auto") else "curated"
        print(f"indexed {n} members ({mode} mode) -> {index_path}")
        if idx["_meta"].get("topics_auto"):
            print(f"  note: interest map auto-derived from mined vocab. For sharper "
                  f"routing, curate {os.path.join(school_dir, 'afferent_topics.json')}")
        for name, fp in sorted(idx["members"].items(), key=lambda x: -x[1]["n_crystals"])[:10]:
            print(f"  {name:18s} {fp['n_crystals']:>6d}cr  ~{','.join(fp['vocab'][:7])}")
    elif len(args) >= 3 and args[0] == "route":
        for name, info, snip in surface_for(" ".join(args[2:]), args[1], k=3):
            tag = ",".join(info) if isinstance(info, list) else f"score {info}"
            print(f"  {name:16s} {tag:24s}  ~{snip[:70]}")
    else:
        print(__doc__)


if __name__ == "__main__":
    _cli()
