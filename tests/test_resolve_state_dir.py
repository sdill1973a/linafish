"""Tests for linafish.__main__._resolve_state_dir.

The auto-detect rule: when a CLI verb is invoked with `-n <name>` and no
`--state-dir`, the helper should find the right place to look — flat root,
nested name-subdir, or school facet — instead of silently loading an empty
fish.

These three layouts are conventional in real linafish installs:

    ~/.linafish/anchor-writing_crystals.jsonl   (flat root)
    ~/.linafish/me/me_crystals.jsonl            (nested by name)
    ~/.linafish/school/captain/captain_crystals.jsonl   (school facet)

Without auto-detect, only the flat root resolves correctly. With it, all
three.
"""
import tempfile
import unittest
from pathlib import Path

from linafish.__main__ import _resolve_state_dir


class TestResolveStateDir(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _touch(self, *parts):
        path = self.root.joinpath(*parts)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}\n", encoding="utf-8")
        return path

    def test_explicit_state_dir_wins(self):
        # Explicit path always wins, even if a better auto-detect exists.
        self._touch("me", "me_crystals.jsonl")
        explicit = "/some/explicit/path"
        result = _resolve_state_dir("me", explicit, default_root=self.root)
        self.assertEqual(result, Path(explicit))

    def test_explicit_state_dir_string_or_path(self):
        # Both string and Path inputs work.
        result_str = _resolve_state_dir("me", "/x/y", default_root=self.root)
        result_path = _resolve_state_dir("me", Path("/x/y"), default_root=self.root)
        self.assertEqual(result_str, Path("/x/y"))
        self.assertEqual(result_path, Path("/x/y"))

    def test_flat_root_when_no_subdir(self):
        # Flat layout: anchor-writing_crystals.jsonl directly under root.
        self._touch("anchor-writing_crystals.jsonl")
        result = _resolve_state_dir("anchor-writing", None, default_root=self.root)
        self.assertEqual(result, self.root)

    def test_nested_name_subdir(self):
        # Nested layout: ~/.linafish/me/me_crystals.jsonl
        self._touch("me", "me_crystals.jsonl")
        result = _resolve_state_dir("me", None, default_root=self.root)
        self.assertEqual(result, self.root / "me")

    def test_school_facet_subdir(self):
        # School layout: ~/.linafish/school/captain/captain_crystals.jsonl
        self._touch("school", "captain", "captain_crystals.jsonl")
        result = _resolve_state_dir("captain", None, default_root=self.root)
        self.assertEqual(result, self.root / "school" / "captain")

    def test_nested_takes_precedence_over_school(self):
        # If both a top-level subdir AND a school facet exist for the same
        # name, the top-level wins (more specific user intent).
        self._touch("captain", "captain_crystals.jsonl")
        self._touch("school", "captain", "captain_crystals.jsonl")
        result = _resolve_state_dir("captain", None, default_root=self.root)
        self.assertEqual(result, self.root / "captain")

    def test_unknown_name_falls_back_to_root(self):
        # Name that has no subdir AND no flat file falls back to root —
        # FishEngine then loads as empty, the previous behavior preserved.
        result = _resolve_state_dir("phantom", None, default_root=self.root)
        self.assertEqual(result, self.root)

    def test_no_name_returns_root(self):
        # No name → no auto-detect — return root.
        result = _resolve_state_dir(None, None, default_root=self.root)
        self.assertEqual(result, self.root)

    def test_default_root_is_dot_linafish(self):
        # When default_root is None, fall back to ~/.linafish.
        result = _resolve_state_dir("phantom", None, default_root=None)
        self.assertEqual(result, Path.home() / ".linafish")

    def test_path_separator_in_name_raises(self):
        # Codex round-1 finding 2026-05-02: -n '../etc/passwd' previously
        # let FishEngine mkdir/append outside ~/.linafish. The guard
        # rejects names containing /, \, or .. so --state-dir remains the
        # only legitimate way to point outside the root.
        with self.assertRaises(ValueError):
            _resolve_state_dir("../etc/passwd", None, default_root=self.root)
        with self.assertRaises(ValueError):
            _resolve_state_dir("foo/bar", None, default_root=self.root)
        with self.assertRaises(ValueError):
            _resolve_state_dir("foo\\bar", None, default_root=self.root)
        with self.assertRaises(ValueError):
            _resolve_state_dir("..", None, default_root=self.root)

    def test_path_separator_in_name_with_explicit_state_dir_does_not_raise(self):
        # Explicit --state-dir is the legitimate escape; the name guard
        # should not fire when explicit_state_dir is set (legacy callers
        # may pass odd names + explicit dirs).
        result = _resolve_state_dir("../weird", "/tmp/my_dir", default_root=self.root)
        self.assertEqual(result, Path("/tmp/my_dir"))


if __name__ == "__main__":
    unittest.main()
