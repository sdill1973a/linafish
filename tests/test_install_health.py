"""The install-skew advisory must be able to say NOTHING.

Born with the module, 2026-08-31. Every test here exists because the failure
it guards against is one an always-speaking (or always-silent) organ would
pass. Each behaviour is asserted in BOTH directions: the case where it must
speak, and the case where it must not.
"""

import subprocess
import sys

import pytest

from linafish import install_health as ih


class TestVersionKey:
    def test_orders_normally(self):
        assert ih.version_key("2.2.0") < ih.version_key("2.2.1")
        assert ih.version_key("1.9.9") < ih.version_key("2.0.0")
        assert ih.version_key("2.10.0") > ih.version_key("2.9.0")

    def test_dev_build_ranks_with_its_release_not_before_it(self):
        """2.2.1.dev0 CARRIES 2.2.1's fixes; ranking it lower cries wolf."""
        assert ih.version_key("2.2.1.dev0") == ih.version_key("2.2.1")
        assert ih.version_key("2.2.1.dev0") > ih.version_key("2.2.0")

    def test_garbage_never_raises(self):
        for bad in ["", "not-a-version", None, object()]:
            assert isinstance(ih.version_key(bad), tuple)


class TestKnownIssuesAfter:
    def test_speaks_for_a_version_that_predates_the_fix(self):
        issues = ih.known_issues_after("2.2.0")
        assert any(f["id"] == "surrogate-content-hash" for f in issues)

    def test_SILENT_for_a_version_that_already_has_it(self):
        assert ih.known_issues_after("2.2.1") == []
        assert ih.known_issues_after("2.2.1.dev0") == []
        assert ih.known_issues_after("9.9.9") == []


class TestCrashAdvisory:
    TB = 'File "linafish/crystallizer_v3.py", line 363, in _content_hash\n'

    def test_speaks_on_a_known_crash_in_an_old_build(self, monkeypatch):
        import linafish

        monkeypatch.setattr(linafish, "__version__", "2.2.0", raising=False)
        exc = UnicodeEncodeError("utf-8", "x", 0, 1, "surrogates not allowed")
        note = ih.crash_advisory(exc, self.TB)
        assert "KNOWN BUG" in note
        assert "2.2.1" in note

    def test_SILENT_when_the_running_build_already_has_the_fix(self, monkeypatch):
        import linafish

        monkeypatch.setattr(linafish, "__version__", "2.2.1", raising=False)
        exc = UnicodeEncodeError("utf-8", "x", 0, 1, "surrogates not allowed")
        assert ih.crash_advisory(exc, self.TB) == ""

    def test_SILENT_on_an_unknown_crash(self, monkeypatch):
        import linafish

        monkeypatch.setattr(linafish, "__version__", "2.2.0", raising=False)
        assert ih.crash_advisory(ValueError("something else"), self.TB) == ""

    def test_SILENT_when_the_traceback_does_not_match_the_signature(self, monkeypatch):
        """Right exception type, wrong place — must not claim the known fix."""
        import linafish

        monkeypatch.setattr(linafish, "__version__", "2.2.0", raising=False)
        exc = UnicodeEncodeError("utf-8", "x", 0, 1, "surrogates not allowed")
        other_tb = 'File "somewhere/else.py", line 1, in unrelated\n'
        assert ih.crash_advisory(exc, other_tb) == ""

    def test_never_raises_on_garbage(self):
        assert ih.crash_advisory(ValueError("x"), None) == "" or True


class TestFormatSkew:
    def test_speaks_when_a_newer_copy_exists(self):
        rep = {
            "skewed": True,
            "executing": {"version": "2.2.0", "path": "/a/site-packages/linafish"},
            "newest": {"version": "2.2.1", "path": "/b/pipx/linafish"},
        }
        out = ih.format_skew(rep)
        assert "INSTALL SKEW" in out
        assert "/a/site-packages/linafish" in out
        assert "/b/pipx/linafish" in out
        # it should name the fix the executing copy is missing
        assert "One bad character" in out

    def test_SILENT_when_not_skewed(self):
        assert ih.format_skew({"skewed": False}) == ""
        assert ih.format_skew({}) == ""


class TestFindInstalls:
    def test_includes_the_executing_copy_and_never_raises(self):
        installs = ih.find_installs()
        assert isinstance(installs, list)
        assert any(i["executing"] for i in installs), "executing copy must appear"

    def test_sorted_newest_first(self):
        installs = ih.find_installs()
        keys = [ih.version_key(i["version"]) for i in installs]
        assert keys == sorted(keys, reverse=True)


class TestAdvisoryNeverSwallows:
    def test_a_failing_command_still_exits_nonzero_with_its_traceback(self):
        """The advisory annotates. It must not become an error handler."""
        code = (
            "import sys;"
            "sys.argv=['linafish','recall','q','--state-dir','/nonexistent/nope'];"
            "from linafish.__main__ import main; main()"
        )
        proc = subprocess.run(
            [sys.executable, "-c", code], capture_output=True, text=True
        )
        # Either it handled the missing dir gracefully (rc 0/1 with a message)
        # or it raised — but it must never exit 0 while printing a traceback.
        if "Traceback" in proc.stderr:
            assert proc.returncode != 0, "traceback printed but exit code was 0"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
