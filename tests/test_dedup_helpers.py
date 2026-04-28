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


if __name__ == "__main__":
    unittest.main()
