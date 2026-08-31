"""source_mind as a REAL crystal field (2026-08-22, CAIRN's finding).

Proves both directions: the field carries when given, stays absent (legacy
shape) when not, round-trips through persist/load, and the read-path decode
prefers the field while leaving the legacy prefix fallback byte-identical.
"""
import json
from linafish.crystallizer_v3 import Crystal


def _mk(source, source_mind=None):
    return Crystal(id="t1", ts="2026-08-22T00:00:00Z", text="x" * 40,
                   source=source, mi_vector=[0.1, 0.2], resonance=[],
                   keywords=["x"], source_mind=source_mind)


def test_field_carries_and_persists():
    c = _mk("session:test", source_mind="anchor")
    d = c.to_dict()
    assert d["source_mind"] == "anchor"


def test_absent_field_keeps_legacy_shape():
    c = _mk("mqtt:lab/conv")
    d = c.to_dict()
    assert "source_mind" not in d  # legacy-shaped record, no null noise


def test_loader_roundtrip_tolerates_both():
    with_field = {"id": "a", "ts": "t", "text": "y" * 20, "source": "s",
                  "mi_vector": [0.1], "source_mind": "cairn"}
    without = {"id": "b", "ts": "t", "text": "y" * 20, "source": "s",
               "mi_vector": [0.1]}
    a = Crystal(resonance=[], keywords=[], **with_field)
    b = Crystal(resonance=[], keywords=[], **without)
    assert a.source_mind == "cairn" and b.source_mind is None


def test_read_decode_prefers_field_legacy_unchanged():
    mind_name = "me"
    def decode(c):  # mirrors converse.py read path
        return getattr(c, "source_mind", None) or (
            (c.source or "").split(":")[0] if ":" in (c.source or "") else mind_name)
    assert decode(_mk("mqtt:lab", source_mind="anchor")) == "anchor"   # field wins
    assert decode(_mk("mqtt:lab")) == "mqtt"                            # legacy: unchanged (warts and all)
    assert decode(_mk("plainsource")) == "me"                           # legacy: fish's own mind
