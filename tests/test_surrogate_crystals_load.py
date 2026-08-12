"""A lone surrogate in a crystal log must not kill the whole fish.

The failure this locks down, found 2026-08-12 on six live school fish
(``captain``, ``desk``, ``tending``, ``origin``, ``inception``,
``comms``): a document ingested with mojibake left a lone surrogate in
the crystal text. ``json.dumps`` escaped it on the way out, so the
crystal log is valid UTF-8 on disk; ``json.loads`` handed it back as a
real surrogate on the way in; and ``_content_hash`` — which
``_load_state`` runs over EVERY crystal when ``dedupe=True`` — raised
``UnicodeEncodeError``. One bad crystal, and the entire fish stopped
loading. The nightly feed had been failing six of seven fish for two
nights straight, into a log file nobody reads.

Both directions are tested on purpose. A test that only proves the
poisoned fish now loads would pass just as happily if the hash had been
weakened into uselessness, so the byte-exactness of the normal path is
asserted alongside it.
"""
import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from linafish.crystallizer_v3 import _content_hash, _scrub_unencodable
from linafish.engine import FishEngine

# A lone low surrogate — exactly what the live fish carried.
LONE_SURROGATE = "\udc81"


class TestContentHashIsTotal(unittest.TestCase):

    def test_lone_surrogate_hashes_instead_of_raising(self):
        # The defect: this call raised UnicodeEncodeError.
        digest = _content_hash(f"the keystone finding {LONE_SURROGATE} why Holly")
        self.assertEqual(len(digest), 32)

    def test_hash_is_deterministic_for_surrogates(self):
        text = f"a{LONE_SURROGATE}b"
        self.assertEqual(_content_hash(text), _content_hash(text))

    def test_normal_text_hash_is_unchanged(self):
        # The other direction: the fix must not move a single existing
        # hash, or every fish's dedup set silently invalidates. This is
        # the pre-fix expression, pinned as the expected value.
        for text in ("hello world", "em—dash and ünïcode", "Σache = K"):
            with self.subTest(text=text):
                expected = hashlib.md5(text.encode("utf-8")).hexdigest()
                self.assertEqual(_content_hash(text), expected)


class TestScrubUnencodable(unittest.TestCase):

    def test_clean_text_passes_through_identically(self):
        text = "Σache = K — nothing to scrub"
        self.assertIs(_scrub_unencodable(text), text)

    def test_scrubbed_text_can_round_trip(self):
        scrubbed = _scrub_unencodable(f"before{LONE_SURROGATE}after")
        scrubbed.encode("utf-8")  # must not raise
        self.assertIn("before", scrubbed)
        self.assertIn("after", scrubbed)


class TestPoisonedFishStillLoads(unittest.TestCase):
    """The end-to-end shape: a crystal log written before the gate existed."""

    NAME = "poisoned"

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="linafish-surrogate-"))
        self.log = self.dir / f"{self.NAME}_crystals.jsonl"
        rows = [
            {"id": 0, "text": "a perfectly ordinary crystal about the fish",
             "source": "test", "ts": "2026-06-04T22:01:20+00:00"},
            {"id": 1, "text": f"the keystone finding {LONE_SURROGATE} why Holly",
             "source": "test", "ts": "2026-06-04T22:01:21+00:00"},
        ]
        with open(self.log, "w", encoding="utf-8") as fh:
            for row in rows:
                fh.write(json.dumps(row, default=str) + "\n")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_log_on_disk_is_valid_utf8_but_text_is_not(self):
        # Why no file-level errors= setting could have caught this.
        self.log.read_bytes().decode("utf-8")  # the FILE is fine
        with open(self.log, encoding="utf-8") as fh:
            texts = [json.loads(line)["text"] for line in fh]
        with self.assertRaises(UnicodeEncodeError):
            texts[1].encode("utf-8")  # the TEXT is not

    def test_dedupe_load_survives_the_poisoned_crystal(self):
        engine = FishEngine(name=self.NAME, state_dir=self.dir, dedupe=True)
        self.assertEqual(len(engine.fish.crystals), 2)
        self.assertEqual(len(engine.fish._seen_hashes), 2)

    def test_new_text_is_never_persisted_unencodable(self):
        engine = FishEngine(name=self.NAME, state_dir=self.dir, dedupe=True)
        engine.eat(
            f"a fresh deposit carrying {LONE_SURROGATE} a lone surrogate, "
            "long enough to clear the length gate and be crystallized",
            source="test",
        )
        for crystal in engine.fish.crystals:
            with self.subTest(text=crystal.text[:40]):
                crystal.text.encode("utf-8")  # must not raise


if __name__ == "__main__":
    unittest.main()
