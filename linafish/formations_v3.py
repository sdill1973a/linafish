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

import re
from collections import Counter, deque
from dataclasses import dataclass, field
from typing import List, Optional

from .crystallizer import Crystal, CATEGORIES


# Constants from Mind

def _name_from_text(text, fallback_keywords=None, max_len=30):
    """Extract meaningful name from representative text."""
    text = text.strip()
    m = re.search(r'\[Conversation:\s*(.+?)(?:\s*\(continued\))?\]', text)
    if m:
        return m.group(1).strip()[:max_len].upper().replace(' ', '_')
    m = re.search(r'"title":\s*"(.+?)"', text)
    if m:
        return m.group(1).strip()[:max_len].upper().replace(' ', '_')
    m = re.search(r'^#+ (.+)', text, re.MULTILINE)
    if m:
        return m.group(1).strip()[:max_len].upper().replace(' ', '_')
    if text.startswith('A^') or text.startswith('O^'):
        parts = text.split('|')
        if len(parts) > 2:
            return parts[1][:max_len].upper().replace('.', '_')
    words = [w for w in re.findall(r'[a-zA-Z]+', text) if len(w) > 3][:4]
    if words:
        return '_'.join(w.upper() for w in words)
    if fallback_keywords:
        return '_'.join(fallback_keywords[:3]).upper()
    return 'UNNAMED'

GAMMA_THRESHOLD = 0.45
MIN_FORMATION_SIZE = 2
FISSION_THRESHOLD = 0.15
FISSION_CUT_PERCENTILE = 30


@dataclass
class Formation:
    """A named cluster of coupled crystals. Becomes a glyph."""
    id: int
    name: str                        # top keywords joined
    keywords: List[str]              # top 5 by frequency
    member_ids: List[str]            # crystal ids
    centroid: List[float]            # average QLP vector
    representative_text: str         # most-connected crystal's text
    crystal_count: int = 0
    birth_signal: str = "mixed"      # "gamma" (structural), "cosine" (emotional), "both", "mixed"
    source_minds: List[str] = field(default_factory=list)  # which minds contributed
    trust_weight: float = 1.0        # cross-mind coupling > single-source (Section 3.8 defense)
    self_referential_pct: float = 0.0  # % of crystals that are meta/recursive (Section 6.8)


def detect_formations(crystals: List[Crystal], fission_pct: float = 0.15) -> List[Formation]:
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
            if len(comp) / total_crystals > fission_pct:
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
        top_keywords = [kw for kw, _ in Counter(all_keywords).most_common(5)]

        # Centroid — average vector (dynamic width for v3 MI vectors)
        n = len(member_crystals)
        vec_len = len(member_crystals[0].resonance) if member_crystals[0].resonance else 8
        centroid = [0.0] * vec_len
        for mc in member_crystals:
            for dim in range(min(vec_len, len(mc.resonance))):
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

        # Name from top keywords
        name = _name_from_text(rep_text, fallback_keywords=top_keywords)

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

    from .crystallizer import gamma_coefficient

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
        vec_len = len(members[0].centroid) if members and members[0].centroid else 8
        centroid = [0.0] * vec_len
        for m in members:
            for dim in range(min(vec_len, len(m.centroid))):
                centroid[dim] += m.centroid[dim] * m.crystal_count
        if total_crystals > 0:
            centroid = [round(v / total_crystals, 4) for v in centroid]

        from collections import Counter
        top_kw = [kw for kw, _ in Counter(all_keywords).most_common(5)]
        name = _name_from_text(best_rep, fallback_keywords=top_kw)

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


def formations_to_codebook_text(
    formations: List[Formation],
    title: str = "LiNafish",
    crystals: List = None,
) -> str:
    """Render formations as a codebook for context injection.

    Each formation = one glyph entry.
    For mega-formations (>50 crystals), diamond crystals provide sub-structure.
    """
    total_crystals = sum(f.crystal_count for f in formations)
    lines = [
        f"# {title}",
        "",
        f"*{len(formations)} formations, {total_crystals} crystals. Compressed understanding — not retrieval.*",
        "",
    ]

    # Build crystal lookup if provided
    crystal_map = {c.id: c for c in crystals} if crystals else {}

    for f in sorted(formations, key=lambda x: x.crystal_count, reverse=True):
        cats = dict(zip(CATEGORIES, f.centroid))
        top_cats = sorted(cats.items(), key=lambda x: -x[1])[:3]
        cat_str = "+".join(f"{c}" for c, v in top_cats if v > 0.05)

        lines.append(f"**{f.name}** ({f.crystal_count} crystals, {cat_str})")
        lines.append(f"  {f.representative_text[:250]}")
        if f.keywords:
            lines.append(f"  keys: {', '.join(f.keywords)}")

        # Mega-formation: show top diamond crystals as sub-entries
        if f.crystal_count > 50 and crystal_map and hasattr(f, 'member_ids'):
            members = [crystal_map[mid] for mid in f.member_ids if mid in crystal_map]
            diamonds = [c for c in members if c.structural]
            if diamonds:
                # Sort by coupling strength (most connected diamond first)
                diamonds.sort(key=lambda c: sum(g for _, g in c.couplings), reverse=True)
                lines.append("")
                for d in diamonds[:15]:
                    kw = ", ".join(d.keywords[:3]) if d.keywords else ""
                    lines.append(f"  - **[{kw}]** {d.text[:200]}")

        lines.append("")

    # Uncoupled crystals — still valuable, just didn't couple with the batch
    if crystals:
        formed_ids = set()
        for f in formations:
            formed_ids.update(f.member_ids)
        orphans = [c for c in crystals if c.id not in formed_ids]
        if orphans:
            lines.append("**Additional notes** (uncoupled)")
            for c in orphans:
                kw = ", ".join(c.keywords[:3]) if c.keywords else ""
                lines.append(f"  - [{kw}] {c.text[:200]}")
            lines.append("")

    lines.append("---")
    lines.append(f"*{len(formations)} formations from {sum(f.crystal_count for f in formations)} crystals*")
    return "\n".join(lines)
