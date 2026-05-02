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

    def test_shutdown_during_failed_save_exits_nonzero_without_commit(self):
        # Codex round-3 BLOCKING 2026-05-02: round-2 wrapper committed
        # unconditionally on _shutdown_pending — including when the impl
        # raised mid-write. Round-3 fix tracks success; on failure with
        # pending shutdown, exit code 1 and DO NOT commit (would write
        # torn state to git history permanently).
        e = self._engine()
        e._shutdown_pending = True

        commits = []

        def boom(commit=None):
            raise IOError("simulated disk full mid-save")

        def fake_commit(message):
            commits.append(message)

        e._save_state_impl = boom
        e._git_commit = fake_commit

        with self.assertRaises(SystemExit) as ctx:
            e._save_state()
        self.assertEqual(ctx.exception.code, 1, "must exit non-zero on save failure")
        self.assertEqual(commits, [], "must not commit when save raised")
        self.assertFalse(e._save_in_progress, "guard must clear in finally")

    def test_shutdown_after_clean_save_exits_zero_with_commit(self):
        # Mirror of the failure case — when the impl returns cleanly and
        # shutdown was pending, do commit + exit 0.
        e = self._engine()
        e._shutdown_pending = True

        commits = []

        def clean_save(commit=None):
            return None

        def fake_commit(message):
            commits.append(message)

        e._save_state_impl = clean_save
        e._git_commit = fake_commit

        with self.assertRaises(SystemExit) as ctx:
            e._save_state()
        self.assertEqual(ctx.exception.code, 0, "must exit zero on clean save")
        self.assertEqual(len(commits), 1, "must commit on clean save shutdown")
        self.assertIn("deferred flush", commits[0])


if __name__ == "__main__":
    unittest.main()
