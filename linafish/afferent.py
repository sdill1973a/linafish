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

TWO ROUTING MODES
  - CURATED (robust; use when members are NOT topic-pure): route on a
    topic->member keyword map you supply (an `afferent_topics.json` in the
    school dir, or passed to `surface_for`/`build_index`). The map names each
    member's topic explicitly, so it routes correctly even when the members'
    crystals overlap heavily (e.g. a school whose members were all fed the same
    broadcast stream).
  - MINED (zero-config; use when members ARE topic-pure): route on the TF-IDF
    *distinctive* vocabulary mined from each member's crystals — words frequent
    in this member and rare across the others. This needs no map, but it only
    disambiguates when each member's corpus is genuinely about its own distinct
    topic. If every member ate the same stream, the topic signal is not
    statistically recoverable by any frequency method (measured) — route CURATED
    there, or re-feed the members topic-pure first, then MINED returns.

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


def load_topics(school_dir):
    """Load a topic->member keyword map from <school_dir>/afferent_topics.json,
    or return {} (→ mined-only routing). Format: {"member": ["kw", "kw", ...]}."""
    p = os.path.join(school_dir, "afferent_topics.json")
    if os.path.exists(p):
        try:
            with open(p, encoding="utf-8") as fh:
                d = json.load(fh)
            return {k: list(v) for k, v in d.items() if isinstance(v, (list, tuple))}
        except Exception:
            return {}
    return {}


def _scan_member(cf, topic_kws=()):
    """Full vocab Counter + dims + per-keyword on-topic snippet for one member."""
    vocab, dims, kw_best, n = Counter(), Counter(), {}, 0
    single_kws = [k for k in topic_kws if " " not in k]
    try:
        with open(cf, encoding="utf-8") as fh:
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
    skip. The index stores, per member: TF-IDF-distinctive vocab (for MINED
    routing), per-keyword on-topic snippets (for CURATED snippets), crystal count.
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
    out = {"_meta": {"n_members": len(members), "df": dict(df), "topics": topics},
           "members": members}
    if index_path:
        os.makedirs(os.path.dirname(os.path.abspath(index_path)), exist_ok=True)
        with open(index_path, "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=1)
    return out


def _curated_scores(prompt, topics):
    """Route by curated topic keywords. Returns {member: [matched_kws]}. The
    member's own name is an implicit keyword (split on '_'/'-')."""
    pl = (prompt or "").lower()
    ptoks = set(_TOK.findall(pl))
    matched = {}
    for member, kws in topics.items():
        hit = [kw for kw in kws if (kw in ptoks if " " not in kw else kw in pl)]
        for part in re.split(r"[_\-]", member):
            if len(part) > 3 and part in ptoks and part not in hit:
                hit.append(part)
        if hit:
            matched[member] = hit
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
    [(name, matched_or_score, snippet), ...] or []. CURATED if the index carries
    a topic map (preferred); else MINED. Loads + caches the index once."""
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
        out = []
        for name, kws in sorted(matched.items(), key=lambda x: -len(x[1]))[:k]:
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
        mode = "curated" if idx["_meta"].get("topics") else "mined"
        print(f"indexed {n} members ({mode} mode) -> {index_path}")
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
