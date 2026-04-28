"""
Formations — the throat of the fish.

Crystals go in, named glyphs come out. The name earns itself.

Formation detection algorithm for LiNafish:
1. Fission — prevent mega-formations (>15% of lattice)
2. BFS flood fill — connected components on coupling graph
3. Minimum size gate (>=3 crystals)
4. Naming — Counter.most_common(5) keywords across members
5. Reinforcement — formation membership = structural use

Not clustering. Not k-means. Graph traversal.
The graph is the truth. Formations are just what the BFS finds.
"""

import math
from collections import Counter, deque
from dataclasses import dataclass, field
from typing import List, Optional

from .crystallizer_v3 import Crystal
from ._dedup_helpers import normalize_for_dedup

CATEGORIES = ["KO", "TE", "SF", "CR", "IC", "DE", "EW", "AI"]


# Constants from Mind
GAMMA_THRESHOLD = 0.45
MIN_FORMATION_SIZE = 2
FISSION_THRESHOLD = 0.15
FISSION_CUT_PERCENTILE = 30


DIM_ORDER = ["KO", "TE", "SF", "CR", "IC", "DE", "EW", "AI"]
DIM_LABELS = {
    "KO": "Understanding", "TE": "Testing", "SF": "Structuring",
    "CR": "Relating", "IC": "Feeling", "DE": "Specializing",
    "EW": "Acting", "AI": "Self-Reflection",
}


def _cognitive_name(cognitive_centroid: List[float],
                    top_chains: List[str]) -> str:
    """Generate a formation name from cognitive signature.

    Instead of HIS_WHICH_WITH (keyword frequency), produce
    ACTING+RELATING_via_FEELING (cognitive operations).

    Format: TOP1+TOP2_via_TOP3
    Where TOP1/2/3 are the dominant cognitive dimensions.
    """
    if not cognitive_centroid or len(cognitive_centroid) < 8:
        return "UNKNOWN"

    # Rank dimensions by score
    ranked = sorted(
        [(DIM_ORDER[i], cognitive_centroid[i]) for i in range(8)],
        key=lambda x: -x[1]
    )

    # Top 3 dimensions (must have nonzero score)
    top = [(dim, score) for dim, score in ranked if score > 0.01][:3]

    if not top:
        return "UNKNOWN"

    if len(top) == 1:
        return DIM_LABELS[top[0][0]].upper()

    if len(top) == 2:
        return f"{DIM_LABELS[top[0][0]].upper()}+{DIM_LABELS[top[1][0]].upper()}"

    return (f"{DIM_LABELS[top[0][0]].upper()}"
            f"+{DIM_LABELS[top[1][0]].upper()}"
            f"_via_{DIM_LABELS[top[2][0]].upper()}")


@dataclass
class Formation:
    """A named cluster of coupled crystals. Becomes a glyph."""
    id: int
    name: str                        # cognitive name (ACTING+RELATING_via_FEELING)
    keywords: List[str]              # top 5 by frequency (kept for backward compat)
    member_ids: List[str]            # crystal ids
    centroid: List[float]            # average QLP vector
    representative_text: str         # most-connected crystal's text
    crystal_count: int = 0
    birth_signal: str = "mixed"      # "gamma" (structural), "cosine" (emotional), "both", "mixed"
    source_minds: List[str] = field(default_factory=list)
    trust_weight: float = 1.0
    self_referential_pct: float = 0.0
    # Cognitive signature — what makes this not an index
    cognitive_centroid: List[float] = field(default_factory=list)  # 8-dim average
    top_chains: List[str] = field(default_factory=list)  # most common chains in members
    top_operations: List[str] = field(default_factory=list)  # most common QUANTUM ops

    # ---------- v7 surface-ranking signals ----------
    # All derived at detect_formations() time from existing Crystal fields.
    # No new persistence: these get recomputed on every formation pass.
    # Crystal data is never mutated; conservation preserved by construction.
    mean_ache: float = 0.0           # mean Crystal.ache across positive-ache members
    cog_amplitude: float = 0.0       # L2 norm of cognitive_centroid (QLP signal strength)
    content_diversity: float = 0.0   # unique_normalized_hashes / crystal_count, in (0, 1]
    compression_score: float = 0.0   # mean_ache * cog_amplitude * trust_weight * content_diversity
                                     # validated 4133x ratio between top substantive and ALL MINDS
                                     # dominator on me-fish 2026-04-28. Replaces crystal_count as
                                     # the surface ranking key — broadcast-regime saturation
                                     # (low ache, low cog_amplitude, low diversity from
                                     # normalized-hash collapse) compresses to ~0; substantive
                                     # multi-mind content dominates the surface.


def formation_rank_key(formation):
    """Shared sort key for v7 surface ranking.

    Returns a tuple ``(compression_score, crystal_count, id)`` for use
    with ``sorted(..., key=formation_rank_key, reverse=True)``. The
    primary key is ``compression_score`` (a float). Tie-breaks fall
    through to ``crystal_count`` then ``id``.

    Defensive against:
      - missing ``compression_score`` attribute (legacy Formation
        objects loaded from cached state) — defaults to 0.0
      - explicit ``None`` value (someone manually constructed a
        Formation with ``compression_score=None``) — coerced to 0.0
        via ``or 0.0`` so ``sorted`` doesn't crash on
        ``None < float`` comparison

    Used at all 11 surface ranking call sites. Do NOT inline a tuple
    key — keeping a single helper means a future formula change
    happens in one place. (The 11 sites still inline for performance
    in the lambda hot path; this helper is the canonical reference
    and is used by ``formations_to_codebook_text``.)
    """
    score = getattr(formation, 'compression_score', 0.0) or 0.0
    return (score, formation.crystal_count, formation.id)


# ---------------------------------------------------------------------------
# INTERPRETATION — warm translation of cognitive dimensions
# ---------------------------------------------------------------------------
# The fish finds the pattern. This layer translates it into prose.

DIM_INSIGHT = {
    "KO": {
        "primary": "lead with understanding — your first move is to figure out how things work",
        "bridge": "making sense of it first",
        "solo": "You're a pattern-finder. When something new arrives, you reach for the structure underneath before you react.",
        "via": "You engage most when you can learn something real, not just feel something.",
    },
    "TE": {
        "primary": "lead with testing — you check before you trust",
        "bridge": "questioning whether it's actually true",
        "solo": "You hold things up to the light. Not cynicism — care. You test because you've seen what happens when people don't.",
        "via": "You open up when something proves itself honest, not just confident.",
    },
    "SF": {
        "primary": "lead with structure — you organize to make sense of the world",
        "bridge": "building a framework around it",
        "solo": "You think in systems. When things get chaotic, your instinct is to find the shape underneath and name it.",
        "via": "You feel safest when things have a place. Not rigid — oriented.",
    },
    "CR": {
        "primary": "lead with connection — your first instinct is to relate it to someone",
        "bridge": "connecting it to the people involved",
        "solo": "You think in relationships. Every idea, every problem, every feeling — your first question is 'who does this touch?'",
        "via": "You come alive in conversation, in shared experience, in the space between people.",
    },
    "IC": {
        "primary": "lead with feeling — you process through what you want and what you fear",
        "bridge": "feeling your way through it first",
        "solo": "You know things before you can explain them. Your gut speaks and you've learned to listen, even when it's inconvenient.",
        "via": "You engage most when something matters emotionally, not just intellectually.",
    },
    "DE": {
        "primary": "lead with expertise — you go deep, not wide",
        "bridge": "applying specialized knowledge to it",
        "solo": "You're a craftsperson. You'd rather know one thing completely than ten things casually.",
        "via": "You respect precision and get frustrated with hand-waving.",
    },
    "EW": {
        "primary": "lead with action — your first response to understanding is to do something",
        "bridge": "doing something about it",
        "solo": "You process by building, moving, making. Sitting with an idea without acting on it feels like holding your breath.",
        "via": "You feel most yourself when you're making something real, not just thinking about it.",
    },
    "AI": {
        "primary": "lead with reflection — you think about your own thinking",
        "bridge": "pausing to check the conversation inside before responding outside",
        "solo": "You keep a thoughtful dialogue with yourself. That honesty steadies everyone around you.",
        "via": "You engage most when there's room to think out loud, journal, or process aloud with someone safe.",
    },
}

LABEL_TO_DIM = {label.upper(): dim for dim, label in DIM_LABELS.items()}


def interpret_formation(formation: Formation) -> str:
    """Turn a formation into a warm, human paragraph.

    The fish finds the pattern. This function tells you what it means
    about you. Not clinical. Not vague. Warm and specific.
    """
    # Get dimensions from centroid or name
    dims = []
    if formation.cognitive_centroid and len(formation.cognitive_centroid) >= 8:
        ranked = sorted(
            ((DIM_ORDER[i], formation.cognitive_centroid[i]) for i in range(8)),
            key=lambda x: -x[1],
        )
        dims = [dim for dim, score in ranked if score > 0.01]

    if not dims:
        # Parse from cognitive name: FEELING+RELATING_via_ACTING
        tokens = formation.name.upper().replace("_VIA_", "+").split("+")
        for token in tokens:
            token = token.strip("_ ")
            code = LABEL_TO_DIM.get(token)
            if code and code not in dims:
                dims.append(code)

    if not dims:
        # Fall back to the QLP centroid (resonance vector) — exists on ALL formations
        # This is the 8-dim average of member crystal resonance vectors
        centroid = getattr(formation, 'centroid', [])
        if centroid and len(centroid) >= 8 and any(v > 0.01 for v in centroid[:8]):
            ranked = sorted(
                ((DIM_ORDER[i], centroid[i]) for i in range(min(8, len(centroid)))),
                key=lambda x: -x[1],
            )
            dims = [dim for dim, score in ranked if score > 0.01][:3]

    if not dims:
        # Last resort: infer from keywords using the canonical seed mapping
        from .crystallizer_v3 import CANONICAL_SEED
        kw_set = set(k.lower() for k in (formation.keywords or []))
        dim_scores = {}
        for dim, seeds in CANONICAL_SEED.items():
            overlap = len(kw_set & set(seeds))
            if overlap:
                dim_scores[dim] = overlap
        if dim_scores:
            dims = [d for d, _ in sorted(dim_scores.items(), key=lambda x: -x[1])][:3]

    if not dims:
        return ("This formation blends several instincts. Notice the stories "
                "and people it keeps highlighting — that's where your energy lives.")

    primary = dims[0]
    secondary = dims[1] if len(dims) > 1 else None
    tertiary = dims[2] if len(dims) > 2 else None

    sentences = []

    p_lang = DIM_INSIGHT.get(primary, {})
    s_lang = DIM_INSIGHT.get(secondary, {}) if secondary else {}

    # Main sentence: "You [primary] by [secondary bridge]"
    if secondary and s_lang:
        sentences.append(f"You {p_lang.get('primary', 'process')} by {s_lang.get('bridge', 'connecting')}.")
    elif p_lang:
        sentences.append(p_lang.get("solo", ""))

    # Via sentence: how the tertiary dimension shows up
    if tertiary and tertiary in DIM_INSIGHT:
        sentences.append(DIM_INSIGHT[tertiary].get("via", ""))
    elif s_lang:
        sentences.append(s_lang.get("via", ""))
    elif p_lang:
        sentences.append(p_lang.get("via", ""))

    return " ".join(s for s in sentences if s)


def detect_formations(crystals: List[Crystal]) -> List[Formation]:
    """Run formation detection on a batch of crystals.

    BFS flood fill on coupling graph. Each connected component
    with >= 3 members becomes a formation.
    """
    if not crystals:
        return []

    # Build adjacency map
    crystal_map = {c.id: c for c in crystals}
    adjacency = {c.id: set() for c in crystals}
    for c in crystals:
        for coupled_id, gamma in c.couplings:
            if coupled_id in crystal_map:
                adjacency[c.id].add(coupled_id)
                adjacency[coupled_id].add(c.id)

    # BFS flood fill
    visited = set()
    components = []

    for cid in adjacency:
        if cid in visited:
            continue
        if not adjacency[cid]:
            continue

        # BFS from this crystal
        component = []
        queue = deque([cid])
        while queue:
            node = queue.popleft()
            if node in visited:
                continue
            visited.add(node)
            component.append(node)
            for neighbor in adjacency[node]:
                if neighbor not in visited:
                    queue.append(neighbor)

        components.append(component)

    # Filter by minimum size
    components = [c for c in components if len(c) >= MIN_FORMATION_SIZE]

    # Fission — progressively aggressive cuts for mega-formations
    total_crystals = len(crystals)
    for _fission_round in range(10):
        fissioned = False
        # Increase cut percentile each round: 30, 35, 40, 45, 50...
        cut_pct = FISSION_CUT_PERCENTILE + (_fission_round * 5)
        new_components = []
        for comp in components:
            if len(comp) / total_crystals > FISSION_THRESHOLD:
                sub_crystals = [crystal_map[cid] for cid in comp if cid in crystal_map]
                cut_comp = _fission(sub_crystals, crystal_map, min(cut_pct, 70))
                if len(cut_comp) > 1:
                    new_components.extend(cut_comp)
                    fissioned = True
                else:
                    new_components.append(comp)
            else:
                new_components.append(comp)
        components = [c for c in new_components if len(c) >= MIN_FORMATION_SIZE]
        if not fissioned:
            break

    # Build formations
    formations = []
    for i, comp in enumerate(components):
        member_crystals = [crystal_map[cid] for cid in comp if cid in crystal_map]
        if not member_crystals:
            continue

        # Keywords — top 5 by frequency across all members
        all_keywords = []
        for mc in member_crystals:
            all_keywords.extend(mc.keywords)
        # Sort by count descending, then alphabetically on ties (shuffle-invariant naming)
        kw_counts = Counter(all_keywords).most_common()
        kw_sorted = sorted(kw_counts, key=lambda x: (-x[1], x[0]))
        top_keywords = [kw for kw, _ in kw_sorted[:5]]

        # Centroid — average QLP vector
        n = len(member_crystals)
        centroid = [0.0] * 8
        for mc in member_crystals:
            for dim in range(min(8, len(mc.resonance))):
                centroid[dim] += mc.resonance[dim]
        centroid = [round(v / n, 4) for v in centroid]

        # Representative — prefer diamond (structural) crystals, then highest coupling
        # Diamonds carry consumed expertise. Connected crystals carry structure.
        # Teaching > wiring.
        structural = [c for c in member_crystals if c.structural]
        if structural:
            best_crystal = max(structural,
                              key=lambda c: sum(g for _, g in c.couplings))
        else:
            best_crystal = max(member_crystals,
                              key=lambda c: sum(g for _, g in c.couplings))
        rep_text = best_crystal.text

        # Cognitive centroid — average cognitive_vector across members
        cog_centroid = [0.0] * 8
        cog_count = 0
        chain_counter = Counter()
        op_counter = Counter()
        for mc in member_crystals:
            cv = getattr(mc, 'cognitive_vector', None)
            if cv and len(cv) >= 8 and any(v > 0 for v in cv):
                for dim in range(8):
                    cog_centroid[dim] += cv[dim]
                cog_count += 1
            # Collect chains
            mc_chains = getattr(mc, 'chains', None)
            if mc_chains:
                for chain in mc_chains:
                    if isinstance(chain, (list, tuple)):
                        chain_counter[">".join(chain)] += 1
                    else:
                        chain_counter[str(chain)] += 1
        if cog_count > 0:
            cog_centroid = [round(v / cog_count, 4) for v in cog_centroid]

        top_chains_list = [c for c, _ in chain_counter.most_common(5)]
        top_ops_list = [o for o, _ in op_counter.most_common(5)]

        # Name — cognitive if we have the data, keyword fallback
        if cog_count > 0 and any(v > 0 for v in cog_centroid):
            name = _cognitive_name(cog_centroid, top_chains_list)
        else:
            name = "_".join(top_keywords[:3]).upper() if top_keywords else f"FORMATION_{i}"

        # Source minds — which minds contributed crystals to this formation
        minds = set()
        for mc in member_crystals:
            mind = getattr(mc, 'source_mind', None)
            if mind:
                minds.add(mind)

        # Trust weight — cross-mind coupling is harder to fake (Section 3.8 defense)
        # 1 mind = 0.5, 2 minds = 1.0, 3+ minds = 1.5
        n_minds = len(minds) if minds else 1
        trust = min(0.5 * n_minds, 1.5)

        # Self-referential percentage (Section 6.8 — recursion boundary)
        n_self_ref = sum(1 for mc in member_crystals if getattr(mc, 'self_referential', False))
        self_ref_pct = round(n_self_ref / len(member_crystals), 2) if member_crystals else 0.0

        # v7 surface-ranking signals — derived from member_crystals,
        # never modify the underlying Crystal objects.
        positive_aches = [
            mc.ache for mc in member_crystals if (mc.ache or 0) > 0
        ]
        mean_ache_val = (
            sum(positive_aches) / len(positive_aches)
            if positive_aches else 0.0
        )
        cog_amp_val = math.sqrt(sum(v * v for v in cog_centroid)) if cog_centroid else 0.0
        if member_crystals:
            unique_hashes = {
                normalize_for_dedup(mc.text or "") for mc in member_crystals
            }
            content_div_val = len(unique_hashes) / len(member_crystals)
        else:
            content_div_val = 0.0
        compression_val = (
            mean_ache_val * cog_amp_val * trust * content_div_val
        )

        formations.append(Formation(
            id=i,
            name=name,
            keywords=top_keywords,
            member_ids=comp,
            centroid=centroid,
            representative_text=rep_text,
            crystal_count=len(comp),
            source_minds=sorted(minds) if minds else [],
            trust_weight=trust,
            self_referential_pct=self_ref_pct,
            cognitive_centroid=cog_centroid,
            top_chains=top_chains_list,
            top_operations=top_ops_list,
            mean_ache=mean_ache_val,
            cog_amplitude=cog_amp_val,
            content_diversity=content_div_val,
            compression_score=compression_val,
        ))

    return formations


def _fission(
    crystals: List[Crystal],
    crystal_map: dict,
    cut_percentile: int,
) -> List[List[str]]:
    """Cut weakest edges in an oversized formation, return sub-components."""
    # Collect all internal edges with gamma
    edges = []
    seen = set()
    for c in crystals:
        for coupled_id, gamma in c.couplings:
            edge_key = tuple(sorted([c.id, coupled_id]))
            if edge_key not in seen and coupled_id in crystal_map:
                # Skip structural-to-structural edges
                c2 = crystal_map.get(coupled_id)
                if c2 and c.structural and c2.structural:
                    continue
                edges.append((c.id, coupled_id, gamma))
                seen.add(edge_key)

    if not edges:
        return [[c.id for c in crystals]]

    # Find cut threshold
    gammas = sorted(g for _, _, g in edges)
    cut_idx = max(1, len(gammas) * cut_percentile // 100)
    cut_threshold = gammas[cut_idx - 1]

    # Remove weak edges from couplings
    for c in crystals:
        c.couplings = [(cid, g) for cid, g in c.couplings
                       if g > cut_threshold or
                       (crystal_map.get(cid) and c.structural and crystal_map[cid].structural)]

    # Re-BFS
    cids = {c.id for c in crystals}
    adjacency = {c.id: set() for c in crystals}
    for c in crystals:
        for coupled_id, gamma in c.couplings:
            if coupled_id in cids:
                adjacency[c.id].add(coupled_id)
                adjacency[coupled_id].add(c.id)

    visited = set()
    components = []
    for cid in cids:
        if cid in visited:
            continue
        component = []
        queue = deque([cid])
        while queue:
            node = queue.popleft()
            if node in visited:
                continue
            visited.add(node)
            component.append(node)
            for neighbor in adjacency.get(node, set()):
                if neighbor not in visited:
                    queue.append(neighbor)
        components.append(component)

    return components


def hierarchical_merge(
    formations: List[Formation],
    target: int = 50,
    gamma_threshold: float = 0.65,
) -> List[Formation]:
    """Merge formations into meta-formations.

    Same algorithm, one level up. Formation centroids become
    the vectors. Formations that couple above threshold merge.
    The city emerges from neighborhoods.

    Higher gamma threshold than crystal level (0.65 vs 0.45) because
    formation centroids are already averaged — they're smoother,
    more similar, couple too easily at low thresholds.

    Crystal = territory. Formation = neighborhood. Meta-formation = city.
    """
    if len(formations) <= target:
        return formations

    from .crystallizer_v3 import gamma as gamma_coefficient

    # Couple formations by centroid similarity
    for i, a in enumerate(formations):
        for b in formations[i + 1:]:
            gamma = gamma_coefficient(a.centroid, b.centroid)
            if gamma >= gamma_threshold:
                a.keywords.append(f"_coupled_{b.id}")
                b.keywords.append(f"_coupled_{a.id}")

    # BFS on formation coupling graph
    adjacency = {f.id: set() for f in formations}
    form_map = {f.id: f for f in formations}

    for f in formations:
        for kw in f.keywords:
            if kw.startswith("_coupled_"):
                other_id = int(kw.split("_coupled_")[1])
                if other_id in adjacency:
                    adjacency[f.id].add(other_id)
                    adjacency[other_id].add(f.id)

    # Clean up temporary coupling markers
    for f in formations:
        f.keywords = [kw for kw in f.keywords if not kw.startswith("_coupled_")]

    visited = set()
    meta_groups = []
    for fid in adjacency:
        if fid in visited:
            continue
        group = []
        queue = deque([fid])
        while queue:
            node = queue.popleft()
            if node in visited:
                continue
            visited.add(node)
            group.append(node)
            for neighbor in adjacency[node]:
                if neighbor not in visited:
                    queue.append(neighbor)
        if group:
            meta_groups.append(group)

    # Build meta-formations
    meta_formations = []
    for i, group in enumerate(sorted(meta_groups, key=len, reverse=True)):
        members = [form_map[fid] for fid in group if fid in form_map]
        if not members:
            continue

        # Merge all member formations
        all_member_ids = []
        all_keywords = []
        total_crystals = 0
        best_rep = ""
        best_count = 0

        for m in members:
            all_member_ids.extend(m.member_ids)
            all_keywords.extend(m.keywords)
            total_crystals += m.crystal_count
            if m.crystal_count > best_count:
                best_count = m.crystal_count
                best_rep = m.representative_text

        # Centroid = average of member centroids weighted by crystal count
        centroid = [0.0] * 8
        for m in members:
            for dim in range(8):
                centroid[dim] += m.centroid[dim] * m.crystal_count
        if total_crystals > 0:
            centroid = [round(v / total_crystals, 4) for v in centroid]

        from collections import Counter
        top_kw = [kw for kw, _ in Counter(all_keywords).most_common(5)]
        name = "_".join(top_kw[:3]).upper() if top_kw else f"META_{i}"

        meta_formations.append(Formation(
            id=i,
            name=name,
            keywords=top_kw,
            member_ids=all_member_ids,
            centroid=centroid,
            representative_text=best_rep,
            crystal_count=total_crystals,
        ))

    # If still too many, raise threshold and recurse
    if len(meta_formations) > target * 1.5 and gamma_threshold < 0.95:
        return hierarchical_merge(meta_formations, target, gamma_threshold + 0.05)

    return meta_formations


def _clean_crystal_text(text: str, max_len: int = 200) -> str:
    """Clean crystal text for display: strip markdown, find the deep sentence."""
    import re
    text = re.sub(r'^[#*>\-\s]+', '', text.replace('\n', ' ')).strip()
    # Split into sentences, prefer the 2nd+ (deeper material, not headers)
    sentences = [s.strip() for s in text.split('. ') if len(s.strip()) > 15]
    if len(sentences) > 1 and len(sentences[0]) < 50:
        text = '. '.join(sentences[1:3]) + '.'
    elif sentences:
        text = '. '.join(sentences[:2]) + '.'
    if len(text) > max_len:
        for end in ['. ', '! ', '? ']:
            idx = text.find(end, 40)
            if idx > 0 and idx < max_len:
                text = text[:idx + 1]
                break
        else:
            text = text[:max_len] + "..."
    return text


def formations_to_codebook_text(
    formations: List[Formation],
    title: str = "LiNafish",
    crystals: List = None,
) -> str:
    """Render formations as a codebook for context injection.

    Each formation = one glyph entry. Text is cleaned for AI readability.
    For mega-formations (>50 crystals), diamond crystals provide sub-structure.
    """
    # Human-readable dimension names
    dim_names = {
        "KO": "knowing", "TE": "testing", "SF": "structuring",
        "CR": "relating", "IC": "wanting", "DE": "specializing",
        "EW": "acting", "AI": "reflecting",
    }

    total_crystals = sum(f.crystal_count for f in formations)
    lines = [
        f"# {title}",
        "",
        f"*{len(formations)} formations, {total_crystals} crystals. Compressed understanding — not retrieval.*",
        "",
    ]

    # Build crystal lookup if provided
    crystal_map = {c.id: c for c in crystals} if crystals else {}

    # v7: rank by compression_score, not crystal_count. Big != more
    # important. The score blends mean_ache (information density), QLP
    # cognitive amplitude, trust_weight (cross-mind diversity), and
    # content_diversity (unique-normalized-hash / count — RCP compression-
    # equivalence). Empirical 4133x ratio between top substantive and ALL
    # MINDS dominator on me-fish 2026-04-28. crystal_count still rendered
    # in the formation header so repetition-as-signal stays visible.
    # `formation_rank_key` (module-level, see above) gives deterministic
    # tie-break and handles None/legacy Formation objects safely.
    for f in sorted(formations, key=formation_rank_key, reverse=True):
        cats = dict(zip(CATEGORIES, f.centroid))
        top_cats = sorted(cats.items(), key=lambda x: -x[1])[:3]
        cat_str = "+".join(dim_names.get(c, c) for c, v in top_cats if v > 0.05)

        # Surface header: name, crystal_count (so repetition stays visible),
        # cognitive category mix, plus compression_score in parentheses
        # when the formation has v7 fields populated.
        score = getattr(f, 'compression_score', None)
        if score is not None and score > 0:
            lines.append(
                f"**{f.name}** ({f.crystal_count} crystals, {cat_str}, "
                f"score={score:.3f})"
            )
        else:
            lines.append(f"**{f.name}** ({f.crystal_count} crystals, {cat_str})")
        # Warm interpretation — what this formation means about you
        interpretation = interpret_formation(f)
        if interpretation:
            lines.append(f"  *{interpretation}*")
        # Clean representative text
        rep = _clean_crystal_text(f.representative_text, 250)
        lines.append(f"  \"{rep}\"")
        if f.keywords:
            # Filter out stopword-level keywords
            meaningful_kw = [k for k in f.keywords if len(k) > 3][:5]
            if meaningful_kw:
                lines.append(f"  themes: {', '.join(meaningful_kw)}")

        # Mega-formation: show top diamond crystals as sub-entries
        if f.crystal_count > 50 and crystal_map and hasattr(f, 'member_ids'):
            members = [crystal_map[mid] for mid in f.member_ids if mid in crystal_map]
            diamonds = [c for c in members if c.structural]
            if diamonds:
                diamonds.sort(key=lambda c: sum(g for _, g in c.couplings), reverse=True)
                lines.append("")
                for d in diamonds[:15]:
                    clean = _clean_crystal_text(d.text, 200)
                    lines.append(f"  - \"{clean}\"")

        lines.append("")

    # Uncoupled crystals — still valuable, just didn't couple with the batch
    if crystals:
        formed_ids = set()
        for f in formations:
            formed_ids.update(f.member_ids)
        orphans = [c for c in crystals if c.id not in formed_ids]
        if orphans:
            lines.append("**Other observations** (not yet part of a pattern)")
            for c in orphans:
                clean = _clean_crystal_text(c.text, 200)
                lines.append(f"  - \"{clean}\"")
            lines.append("")

    lines.append("---")
    lines.append(f"*{len(formations)} formations from {sum(f.crystal_count for f in formations)} crystals*")
    return "\n".join(lines)
