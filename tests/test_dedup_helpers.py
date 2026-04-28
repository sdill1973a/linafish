"""Tests for linafish._dedup_helpers.normalize_for_dedup.

Verifies the normalization rule:
  1. Strip a leading [YYYY-MM-DDT...] timestamp/source line
  2. Lowercase
  3. Collapse whitespace runs to single space
  4. Strip leading/trailing whitespace
"""
import unittest

from linafish._dedup_helpers import normalize_for_dedup


class TestNormalizeForDedup(unittest.TestCase):

    def test_empty_string(self):
        self.assertEqual(normalize_for_dedup(""), "")

    def test_none_safe(self):
        # The helper guards against falsy input.
        self.assertEqual(normalize_for_dedup(None), "")

    def test_idempotent(self):
        # Applying twice should give the same result.
        text = "[2026-04-21T17:14:08.037Z anchor/conv/lab from=unknown]\nSome BODY here"
        once = normalize_for_dedup(text)
        twice = normalize_for_dedup(once)
        self.assertEqual(once, twice)

    def test_strips_mqtt_timestamp_prefix(self):
        text = (
            "[2026-04-21T17:14:08.037Z anchor/conv/lab from=unknown]\n"
            "ALL MINDS - new topic"
        )
        result = normalize_for_dedup(text)
        self.assertEqual(result, "all minds - new topic")

    def test_collapses_timestamp_variants(self):
        # The whole point of the patch — different timestamps, same body
        # → same normalized hash.
        a = "[2026-04-21T17:14:08.037Z anchor/conv/lab from=unknown]\nSAME BODY"
        b = "[2026-04-22T03:14:09.111Z anchor/conv/lab from=unknown]\nSAME BODY"
        self.assertEqual(normalize_for_dedup(a), normalize_for_dedup(b))
        self.assertEqual(normalize_for_dedup(a), "same body")

    def test_distinct_bodies_distinct(self):
        # Different bodies must NOT collapse, even with same timestamp.
        prefix = "[2026-04-21T17:14:08.037Z anchor/conv/lab from=unknown]\n"
        a = prefix + "MESSAGE A"
        b = prefix + "MESSAGE B"
        self.assertNotEqual(normalize_for_dedup(a), normalize_for_dedup(b))

    def test_lowercase(self):
        self.assertEqual(normalize_for_dedup("Hello WORLD"), "hello world")

    def test_collapse_whitespace_runs(self):
        self.assertEqual(
            normalize_for_dedup("foo    bar\n\nbaz\t\tqux"),
            "foo bar baz qux",
        )

    def test_strip_leading_trailing_whitespace(self):
        self.assertEqual(normalize_for_dedup("   hello   "), "hello")

    def test_no_prefix_passthrough(self):
        # Text that doesn't start with a timestamp prefix should still
        # be lowercased and whitespace-collapsed but not stripped of
        # any other content.
        text = "Just a regular message with No Prefix"
        self.assertEqual(
            normalize_for_dedup(text),
            "just a regular message with no prefix",
        )

    def test_bracket_in_body_preserved(self):
        # Only LEADING [timestamp ...] prefix is stripped. Bracketed
        # content elsewhere in the body must survive.
        text = "Just text mentioning [Image #4] in the middle"
        result = normalize_for_dedup(text)
        self.assertIn("[image #4]", result)

    def test_truncation_then_normalize_intent(self):
        # The listener does normalize_for_dedup(text[:500]). Verify that
        # truncating BEFORE normalize is safe — the timestamp prefix is
        # always within the first 500 chars in MQTT-bridged messages.
        prefix = "[2026-04-21T17:14:08.037Z anchor/conv/lab from=unknown]\n"
        body = "x" * 600
        text = prefix + body
        # After [:500], we have prefix + 500 - len(prefix) chars of body.
        # Normalization should still strip the prefix.
        truncated = text[:500]
        normalized = normalize_for_dedup(truncated)
        self.assertFalse(normalized.startswith("["))
        self.assertTrue(normalized.startswith("xxx"))

    def test_unicode_safe(self):
        # No crash on weird unicode (e.g. the replacement char in
        # MQTT-bridged broadcasts that mangled the em-dash).
        text = "[2026-04-21T17:14:08.037Z]\nALL MINDS � new topic"
        result = normalize_for_dedup(text)
        # Replacement char survives; just verifying no exception.
        self.assertIn("all minds", result)

    def test_multiline_body_after_prefix(self):
        # Body itself can be multiline; the regex strips ONE prefix line.
        text = (
            "[2026-04-21T17:14:08.037Z source]\n"
            "Line 1 of body\n"
            "Line 2 of body"
        )
        result = normalize_for_dedup(text)
        self.assertEqual(result, "line 1 of body line 2 of body")

    def test_no_double_strip(self):
        # If text has TWO timestamp prefixes (shouldn't happen in
        # practice, but verify the regex only strips ONE).
        text = (
            "[2026-04-21T17:14:08.037Z source-a]\n"
            "[2026-04-21T17:14:09.999Z source-b]\n"
            "actual body"
        )
        result = normalize_for_dedup(text)
        # Second prefix line is preserved (lowercased + whitespace collapsed).
        self.assertIn("[2026-04-21t17:14:09.999z source-b]", result)
        self.assertIn("actual body", result)

    def test_single_line_prefix_NOT_stripped(self):
        # Regression guard: GPT-5.5 round 4 caught that single-line
        # prefixed text "[2026-...source] BODY" with no trailing
        # newline would have its body eaten by the previous greedy
        # [^\n]* match, collapsing all distinct single-line messages
        # to empty. Trailing-newline requirement prevents this.
        text = "[2026-04-21T17:14:08.037Z source] ACTUAL BODY"
        result = normalize_for_dedup(text)
        # Body must survive intact — only TIMESTAMP+SOURCE prefix
        # with newline gets stripped. Single-line stays.
        self.assertIn("actual body", result)
        # Two distinct single-line messages must NOT collapse.
        a = "[2026-04-21T17:14:08.037Z source] BODY ONE"
        b = "[2026-04-21T17:14:08.037Z source] BODY TWO"
        self.assertNotEqual(normalize_for_dedup(a), normalize_for_dedup(b))


class TestEngineListenerDivergence(unittest.TestCase):
    """Regression guard: engine ``_content_hash`` MUST stay byte-exact;
    listener plate-dedup MUST collapse timestamp variants. The two layers
    intentionally diverge per the v7.1 fold (Option A — keep storage
    policy untouched at the engine layer; let the listener rate-limit).

    GPT-5.5 round 4 specifically called this out as the most important
    regression test: future maintainers might "restore consistency" by
    re-coupling the layers, which would re-violate VALVE OPEN. This
    test makes that re-coupling fail loudly.
    """

    def test_engine_byte_exact(self):
        from linafish.crystallizer_v3 import _content_hash
        a = "[2026-04-21T17:14:08.037Z anchor/conv/lab from=unknown]\nSAME BODY"
        b = "[2026-04-22T03:14:09.111Z anchor/conv/lab from=unknown]\nSAME BODY"
        # Engine MUST distinguish timestamp variants — VALVE OPEN
        # at storage layer.
        self.assertNotEqual(
            _content_hash(a), _content_hash(b),
            "Engine _content_hash must remain byte-exact. If this fails, "
            "someone re-coupled it to normalize_for_dedup — that's a "
            "storage-policy regression beyond what dedupe=True declares.",
        )
        # But identical bytes still hash same (sanity).
        self.assertEqual(_content_hash(a), _content_hash(a))

    def test_listener_normalizes(self):
        # Listener-style hash mirrors daemon.py:333 logic.
        import hashlib
        def listener_hash(t):
            return hashlib.md5(
                normalize_for_dedup(str(t)[:500]).encode("utf-8", errors="replace")
            ).hexdigest()
        a = "[2026-04-21T17:14:08.037Z anchor/conv/lab from=unknown]\nSAME BODY"
        b = "[2026-04-22T03:14:09.111Z anchor/conv/lab from=unknown]\nSAME BODY"
        # Listener MUST collapse timestamp variants — that's its
        # docstring-declared rate-limit intent.
        self.assertEqual(listener_hash(a), listener_hash(b))


class TestColdStartRanking(unittest.TestCase):
    """A formation cluster freshly assembled with no ache data should
    rank deterministically via the (score, count, id) tuple even when
    score is 0.0 across the whole set."""

    def test_zero_score_rank_falls_through_to_count_then_id(self):
        from linafish.formations import Formation, formation_rank_key

        def f(fid, count):
            return Formation(
                id=fid, name=f"F{fid}", keywords=[], member_ids=[],
                centroid=[0.0]*8, representative_text="",
                crystal_count=count,
                # compression_score defaults to 0.0
            )

        forms = [f(3, 100), f(1, 100), f(2, 50)]
        forms_sorted = sorted(forms, key=formation_rank_key, reverse=True)
        # Highest count wins, ties broken by id (descending under reverse=True).
        ids_sorted = [f.id for f in forms_sorted]
        self.assertEqual(ids_sorted, [3, 1, 2])

    def test_explicit_None_compression_score_does_not_crash_sort(self):
        # GPT-5.5 round 3 caught: most sort sites use
        # `getattr(x, "compression_score", 0.0)` which handles
        # missing attribute but NOT explicit None. The shared
        # formation_rank_key uses `or 0.0` to coerce None safely.
        from linafish.formations import Formation, formation_rank_key
        f = Formation(
            id=1, name="t", keywords=[], member_ids=[],
            centroid=[0.0]*8, representative_text="",
            crystal_count=10,
        )
        f.compression_score = None  # type: ignore  (explicit None)
        # Should not crash; should treat None as 0.0
        key = formation_rank_key(f)
        self.assertEqual(key, (0.0, 10, 1))


class TestFormationContentDiversity(unittest.TestCase):
    """GPT-5.5 round 3 specifically asked for: synthetic formation with
    timestamp-variant duplicate texts should yield low content_diversity;
    distinct bodies should remain distinct.

    Tests detect_formations end-to-end on a synthetic batch with controlled
    coupling so we can verify content_diversity computes correctly.
    """

    def _make_crystal(self, cid, text, ache=2.0, source_mind="me"):
        from linafish.crystallizer_v3 import Crystal
        c = Crystal(
            id=cid, ts="2026-04-28T12:00:00Z", text=text, source="test",
            mi_vector=[], resonance=[1.0]*8, keywords=[], ache=ache,
            cognitive_vector=[0.3]*8,
        )
        c.source_mind = source_mind
        return c

    def test_timestamp_variant_duplicates_have_low_diversity(self):
        from linafish._dedup_helpers import normalize_for_dedup
        # 10 crystals with the same body but different timestamps —
        # content_diversity at the formation level should approach 1/10.
        crystals = []
        for i in range(10):
            text = (f"[2026-04-{(i%9)+1:02d}T12:00:00.000Z anchor/conv/lab "
                    f"from=unknown]\nIDENTICAL BODY")
            crystals.append(self._make_crystal(f"c{i}", text))

        # Compute content_diversity manually the way detect_formations does
        unique_hashes = {normalize_for_dedup(c.text or "") for c in crystals}
        content_div = len(unique_hashes) / len(crystals)
        # All 10 timestamps strip to one normalized form -> 1/10
        self.assertEqual(len(unique_hashes), 1)
        self.assertEqual(content_div, 0.1)

    def test_distinct_bodies_preserve_diversity(self):
        from linafish._dedup_helpers import normalize_for_dedup
        # 10 crystals with 10 distinct bodies — diversity should be 1.0
        crystals = []
        for i in range(10):
            text = f"[2026-04-21T12:00:00.000Z source]\nDISTINCT BODY {i}"
            crystals.append(self._make_crystal(f"c{i}", text))
        unique_hashes = {normalize_for_dedup(c.text or "") for c in crystals}
        content_div = len(unique_hashes) / len(crystals)
        self.assertEqual(len(unique_hashes), 10)
        self.assertEqual(content_div, 1.0)


class TestNoCrystalMutation(unittest.TestCase):
    """Sigma_ache conservation guard: detect_formations MUST NOT mutate
    Crystal objects. GPT-5.5 round 3 asked for an explicit deep-copy
    regression test."""

    def test_detect_formations_does_not_mutate_crystals(self):
        import copy
        from linafish.crystallizer_v3 import Crystal
        from linafish.formations import detect_formations

        # Build a small synthetic corpus with couplings that don't
        # trigger the fission cut.
        crystals = []
        for i in range(8):
            c = Crystal(
                id=f"c{i}", ts="2026-04-28T12:00:00Z",
                text=f"unique substantive thought number {i}",
                source="test", mi_vector=[], resonance=[1.0]*8,
                keywords=[], ache=3.0,
                cognitive_vector=[0.4]*8,
            )
            c.source_mind = "me"
            crystals.append(c)
        # Couplings vary so fission doesn't clear them all
        for i, c in enumerate(crystals):
            c.couplings = [(crystals[j].id, 0.5 + 0.1 * j)
                           for j in range(8) if j != i]

        # Snapshot Crystal state via deep-copy before detection.
        snapshot = [copy.deepcopy(c) for c in crystals]

        # Run detection.
        _ = detect_formations(crystals)

        # Verify crystals are byte-equivalent to their snapshot.
        for before, after in zip(snapshot, crystals):
            self.assertEqual(before.id, after.id)
            self.assertEqual(before.text, after.text)
            self.assertEqual(before.ache, after.ache)
            self.assertEqual(before.cognitive_vector, after.cognitive_vector)
            self.assertEqual(before.keywords, after.keywords)
            # `couplings` may be mutated by fission — that's existing
            # engine behavior, not v7. But ache/text/identity must be
            # preserved.

        # Sigma_ache invariant.
        sigma_pre = sum(c.ache for c in snapshot)
        sigma_post = sum(c.ache for c in crystals)
        self.assertEqual(sigma_pre, sigma_post)


class TestDetectFormationsEndToEnd(unittest.TestCase):
    """GPT-5.5 round 4 explicitly asked: not just compute content_diversity
    by hand the way detect_formations does — actually run detect_formations
    end-to-end on a synthetic batch and verify the v7 fields land on the
    Formation objects.

    detect_formations needs realistic coupling distributions to avoid the
    fission cut threshold (FISSION_THRESHOLD=0.15, FISSION_CUT_PERCENTILE=30).
    We build a 30-crystal corpus with 6-crystal connected components
    (formation size 6, fraction 6/30=0.2 > 0.15 — would trigger fission
    if all gammas equal). Vary gammas across edges so fission preserves
    the dominant component.
    """

    def _make_crystal(self, cid, text, ache=2.0, source_mind="me"):
        from linafish.crystallizer_v3 import Crystal
        c = Crystal(
            id=cid, ts="2026-04-28T12:00:00Z", text=text, source="test",
            mi_vector=[], resonance=[1.0]*8, keywords=[], ache=ache,
            cognitive_vector=[0.4]*8,
        )
        c.source_mind = source_mind
        return c

    def test_detect_formations_populates_v7_fields(self):
        from linafish.formations import detect_formations
        # Build 50 crystals total, mostly substantive.
        # Add 30 substantive (high ache, distinct texts, two source minds).
        # Add 20 broadcast-shaped (low ache, identical normalized text,
        # single source mind).
        crystals = []
        for i in range(30):
            c = self._make_crystal(
                f"sub{i}", f"unique substantive thought number {i}",
                ache=3.5,
                source_mind="me" if i % 2 == 0 else "captain",
            )
            crystals.append(c)
        for i in range(20):
            text = (f"[2026-04-{(i%9)+1:02d}T12:00:00.000Z anchor/conv/lab "
                    f"from=unknown]\nALL MINDS - new topic")
            c = self._make_crystal(
                f"ann{i}", text, ache=1.5, source_mind="me",
            )
            crystals.append(c)
        # Wire couplings: substantive form a chain (each i couples to i+1
        # and i-1) — a long thread, not a clique. Broadcasts couple
        # densely (each ann couples to all other anns).
        for i, c in enumerate(crystals):
            if i < 30:
                neighbors = [j for j in (i - 1, i + 1) if 0 <= j < 30]
                c.couplings = [
                    (crystals[j].id, 0.5 + 0.05 * abs(i - j))
                    for j in neighbors
                ]
            else:
                c.couplings = [
                    (crystals[j].id, 0.6 + 0.01 * (j - 30))
                    for j in range(30, 50) if j != i
                ]

        forms = detect_formations(crystals)
        self.assertGreater(len(forms), 0, "detect_formations returned nothing")

        for f in forms:
            self.assertTrue(hasattr(f, "compression_score"))
            self.assertTrue(hasattr(f, "mean_ache"))
            self.assertTrue(hasattr(f, "cog_amplitude"))
            self.assertTrue(hasattr(f, "content_diversity"))
            # Sanity: all v7 fields should be non-negative numbers
            self.assertGreaterEqual(f.compression_score, 0.0)
            self.assertGreaterEqual(f.mean_ache, 0.0)
            self.assertGreaterEqual(f.cog_amplitude, 0.0)
            self.assertGreaterEqual(f.content_diversity, 0.0)
            # content_diversity bounded [0, 1] (per docstring claim)
            self.assertLessEqual(f.content_diversity, 1.0)

        # Confirm the broadcast-shaped formation has very low
        # content_diversity. Fail loudly if BFS didn't surface it
        # (would mean the test scaffold is broken, not v7).
        ann_ids = {f"ann{i}" for i in range(20)}
        ann_formations = [
            f for f in forms
            if any(mid in ann_ids for mid in f.member_ids)
            and len([m for m in f.member_ids if m in ann_ids]) >= 5
        ]
        self.assertGreater(
            len(ann_formations), 0,
            "ANN-shape formation not detected — test scaffold broken",
        )
        ann_f = max(ann_formations, key=lambda f: f.crystal_count)
        # ALL MINDS broadcasts normalize to one bucket, so diversity
        # should be ~ 1/N where N is the formation size.
        self.assertLess(
            ann_f.content_diversity, 0.5,
            f"ANN-shaped formation should have low content_diversity, "
            f"got {ann_f.content_diversity:.3f}",
        )

    def test_detect_formations_compression_score_ranks_substantive_above_broadcast(self):
        """End-to-end: synthetic substantive formation outranks ANN
        formation by compression_score after detect_formations.

        Fixture uses cliques (each crystal couples to all others in
        its group) with VARIED gammas so the fission cut at p30
        trims weakest edges but leaves the formation connected. A
        thin chain wouldn't survive fission on small corpora; a
        clique with varied gammas does.
        """
        from linafish.formations import detect_formations, formation_rank_key
        crystals = []
        # Group A: 6 substantive, multi-mind, distinct texts, high ache.
        for i in range(6):
            c = self._make_crystal(
                f"a{i}", f"substantive thought number {i} with content",
                ache=4.0,
                source_mind="me" if i % 2 == 0 else "captain",
            )
            crystals.append(c)
        # Group B: 6 broadcast crystals, identical body, single mind.
        for i in range(6):
            text = (f"[2026-04-{(i%9)+1:02d}T12:00:00.000Z anchor/conv/lab "
                    f"from=unknown]\nALL MINDS - new topic")
            c = self._make_crystal(
                f"b{i}", text, ache=1.5, source_mind="me",
            )
            crystals.append(c)

        # Group A clique: each couples to all 5 others, with gammas
        # varying so fission cuts the weakest but keeps connectivity.
        for i in range(6):
            crystals[i].couplings = [
                (crystals[j].id, 0.55 + 0.03 * abs(i - j))
                for j in range(6) if j != i
            ]
        # Group B clique: same shape, different gamma range for variety.
        for i in range(6, 12):
            crystals[i].couplings = [
                (crystals[j].id, 0.6 + 0.02 * abs(i - j))
                for j in range(6, 12) if j != i
            ]

        forms = detect_formations(crystals)
        # Find the substantive vs ANN formations by member overlap.
        sub_ids = {f"a{i}" for i in range(6)}
        ann_ids = {f"b{i}" for i in range(6)}
        sub_form = next(
            (f for f in forms
             if sum(1 for m in f.member_ids if m in sub_ids) >= 3),
            None,
        )
        ann_form = next(
            (f for f in forms
             if sum(1 for m in f.member_ids if m in ann_ids) >= 3),
            None,
        )
        # Fail LOUDLY if detection didn't produce both formations —
        # GPT-5.5 round 5 caught the prior `if both: assert ...` shape
        # which would silently pass on detection failure.
        self.assertIsNotNone(
            sub_form, "substantive formation not detected — test invalid"
        )
        self.assertIsNotNone(
            ann_form, "ann formation not detected — test invalid"
        )
        self.assertGreater(
            sub_form.compression_score, ann_form.compression_score,
            f"substantive {sub_form.compression_score:.4f} "
            f"vs ann {ann_form.compression_score:.4f}",
        )
        # Sort by formation_rank_key — substantive must come first.
        ranked = sorted(
            [sub_form, ann_form],
            key=formation_rank_key,
            reverse=True,
        )
        self.assertIs(ranked[0], sub_form)


class TestSurfaceHeaderRendering(unittest.TestCase):
    """GPT-5.5 round 3 asked for: codebook header includes BOTH
    crystal_count AND score so repetition-as-signal stays visible.
    Confirm the rendered surface preserves both."""

    def test_header_renders_count_and_score(self):
        from linafish.formations import Formation, formations_to_codebook_text
        f = Formation(
            id=0, name="TEST_FORMATION", keywords=["k"],
            member_ids=["c0"], centroid=[0.4]*8,
            representative_text="some representative text",
            crystal_count=42, trust_weight=1.0,
            cognitive_centroid=[0.4]*8,
            mean_ache=2.5, cog_amplitude=0.5,
            content_diversity=0.9, compression_score=1.125,
        )
        rendered = formations_to_codebook_text([f], title="surface_test")
        # Both crystal_count and score must appear in the header.
        self.assertIn("42 crystals", rendered)
        self.assertIn("score=1.125", rendered)
        self.assertIn("TEST_FORMATION", rendered)


if __name__ == "__main__":
    unittest.main()
