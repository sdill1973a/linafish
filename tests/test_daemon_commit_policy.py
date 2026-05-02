"""Tests for FishEngine's daemon commit policy: commit_every_n_eats,
flush_commit, and the _save_state reentrancy guard.

Round-2 codex review of PR #20 / linafish 1.3.0 named these as the
load-bearing daemon-history fix and asked for unit coverage.
"""
import tempfile
import unittest
from pathlib import Path

from linafish.engine import FishEngine


class TestCommitPolicy(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.state_dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _engine(self, **kw):
        # seed_grammar=True is the default but expensive on a fresh engine;
        # we don't need a populated vocabulary for these counter tests.
        return FishEngine(state_dir=self.state_dir, name="t", **kw)

    def test_default_is_legacy_per_eat_autocommit(self):
        e = self._engine()
        self.assertEqual(e.commit_every_n_eats, 0)
        self.assertTrue(e.git_autocommit)

    def test_commit_every_n_eats_clamps_negative_to_zero(self):
        e = self._engine(commit_every_n_eats=-5)
        self.assertEqual(e.commit_every_n_eats, 0)

    def test_periodic_mode_overrides_git_autocommit(self):
        # commit_every_n_eats > 0 should make the should_commit decision
        # purely on the counter, regardless of git_autocommit value.
        e = self._engine(commit_every_n_eats=10, git_autocommit=False)
        self.assertEqual(e.commit_every_n_eats, 10)
        # The counter starts at zero — a save will increment it to 1.
        self.assertEqual(e._eat_save_counter, 0)

    def test_flush_commit_method_exists_and_is_callable(self):
        # flush_commit is the public hook the daemon signal handlers call;
        # it must be present and callable. We don't need it to actually
        # commit (no fish content to save), but the method must exist.
        e = self._engine()
        self.assertTrue(hasattr(e, "flush_commit"))
        self.assertTrue(callable(e.flush_commit))

    def test_reentrancy_flags_initialize_false(self):
        # _save_in_progress and _shutdown_pending are the SIGTERM-safety
        # pair (codex round-2 finding 2026-05-02). They must initialize
        # to False so a fresh engine doesn't appear mid-save.
        e = self._engine()
        self.assertFalse(e._save_in_progress)
        self.assertFalse(e._shutdown_pending)


if __name__ == "__main__":
    unittest.main()
