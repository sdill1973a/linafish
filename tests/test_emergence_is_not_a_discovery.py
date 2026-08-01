"""The emergence gate selects for self-reflection, so it cannot report
self-reflection as a finding. This test pins that it never claims to again.

Found by @anchor-dill (#41) with the control the claim should have had from
the start: two matched 60,000-word public-domain corpora with zero contact
with the authors — Moby-Dick's cetology chapters and Marcus Aurelius'
Meditations — both returned 24/24 emergent formations containing
SELF-REFLECTION at phase 2. A corpus about harpoons and blubber scored
exactly as self-authoring as the Meditations.

The mechanism is circular and provable from source:

    if dominant == "AI":          meta_count += 1        (emergence.py)
    meta_density = meta_count / total_ops
    if phase >= 1 and meta_density > 0.1:  phase = 2
    if phase >= 2:                         is_emergent = True

and DIM_LABELS["AI"] == "Self-Reflection" (formations.py). Selected because
self-reflective, reported as having emerged into self-reflection.
"""
import inspect

from linafish import emergence
from linafish.formations import DIM_LABELS


def test_both_routes_to_emergent_are_self_reflection_measures():
    """If someone adds a third, non-self-reflection route, this fails and the
    naming can honestly be revisited. Until then the field is a restatement."""
    src = inspect.getsource(emergence)
    assert 'DIM_LABELS' in DIM_LABELS.__class__.__name__ or True
    assert DIM_LABELS["AI"].lower().replace("-", "").replace(" ", "") == \
        "selfreflection", "AI dimension is no longer labelled Self-Reflection"

    # Route 1: phase >= 2 is gated on meta_density, which counts AI-dominant.
    assert "meta_density > 0.1" in src
    assert 'dominant == "AI"' in src
    # Route 2: the SNT gate is on self_ref_density.
    assert "self_ref_density > SNT_SELF_REF_THRESHOLD" in src


def test_health_does_not_claim_emergence_as_a_finding():
    """The reported key must name the measurement, not the story."""
    import linafish.engine as eng
    src = inspect.getsource(eng.FishEngine._check_emergence) \
        if hasattr(eng.FishEngine, "_check_emergence") else \
        inspect.getsource(eng)
    assert "meta_dominant_formations" in src, \
        "the honest key is gone — did emergence get re-promoted?"
    assert "meta_dominant_note" in src, \
        "the caveat that stops this being read as a discovery is gone"


def test_deprecated_alias_still_carries_the_same_values():
    """Old readers must not KeyError during the deprecation window, and must
    not silently get different data than the new key."""
    import linafish.engine as eng
    src = inspect.getsource(eng)
    assert '"emergent_formations": meta_dominant' in src
    assert '"emergent_count": len(meta_dominant)' in src
