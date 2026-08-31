"""Does the code you are RUNNING match the code you think you installed?

Born 2026-08-31, from a failure that cost two nights of feeding.

A box had two linafish installs: a pipx venv at 2.2.1.dev0 and a `pip --user`
copy at 2.2.0. ``import linafish`` resolved to the older one. The older one
raised ``UnicodeEncodeError`` on a lone surrogate — a bug already fixed in the
newer copy sitting on the same disk. Six fish went unfed for two consecutive
nights, and every check anyone ran was green, because every check asked the
REPOSITORY what the code said instead of asking the FILESYSTEM what was going
to execute.

The rule that failed here was already written down: *a defect is closed when
the fix is in the path that EXECUTES, not when it is written.* Nothing
enforced it. This module enforces it.

Design constraints, all load-bearing:

- **No network.** linafish promises no cloud, no accounts, no telemetry. Every
  check here reads the local filesystem only. The optional PyPI lookup lives
  in ``doctor --check-updates`` and stays opt-in, where it always was.
- **Total.** Nothing in here raises. A health check that crashes the program
  it is auditing is worse than no check.
- **Able to say nothing.** Silence is the correct output for a healthy,
  single-install box, and the tests assert that it actually happens. An
  advisory that always has something to say is an advisory nobody reads.

The honest limit, stated because it decides what this module can and cannot
do: **a build can only carry knowledge of fixes that existed when it was
built.** 2.2.0 can never warn you about a fix that landed in 2.2.1 — so a
local table of known fixes cannot, on its own, tell a stale install that it is
stale. That is why the primary signal here is *skew between installs on this
machine*, which IS knowable offline and with certainty, rather than a table
consulted by the very build that lacks the entry.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

__all__ = [
    "version_key",
    "read_version",
    "find_installs",
    "skew_report",
    "known_issues_after",
    "format_skew",
    "crash_advisory",
]


# --------------------------------------------------------------------------
# Version comparison — PEP 440-lite, no dependency on `packaging`.
# --------------------------------------------------------------------------

_VERSION_RE = re.compile(r"^(\d+(?:\.\d+)*)")


def version_key(version: str) -> tuple:
    """Sortable key for a version string. Never raises.

    Pre-release/dev suffixes are DELIBERATELY discarded: ``2.2.1.dev0`` is a
    build cut from the branch that already carries 2.2.1's fixes, so for
    "do you have the fix?" purposes it ranks WITH 2.2.1, not before it.
    Ranking it below would make this module advise an upgrade to code the
    caller is already running — an advisory that cries wolf gets muted, and a
    muted advisory is the thing this module exists to prevent.
    """
    try:
        m = _VERSION_RE.match(str(version).strip())
        if not m:
            return (-1,)
        return tuple(int(p) for p in m.group(1).split("."))
    except Exception:
        return (-1,)


def read_version(pkg_dir) -> str | None:
    """Read ``__version__`` out of a linafish package dir WITHOUT importing it.

    Importing a second copy of linafish to ask its version would execute it,
    and executing the thing you are auditing is how you get an auditor that
    agrees with whatever it just ran. Text-scrape instead.
    """
    try:
        init = Path(pkg_dir) / "__init__.py"
        text = init.read_text(encoding="utf-8", errors="replace")
        m = re.search(r"^__version__\s*=\s*['\"]([^'\"]+)['\"]", text, re.M)
        return m.group(1) if m else None
    except Exception:
        return None


# --------------------------------------------------------------------------
# Finding every copy on the box
# --------------------------------------------------------------------------


def _candidate_roots() -> list:
    """Directories that plausibly hold a linafish package. Never raises."""
    roots = []
    try:
        import site

        try:
            usersite = site.getusersitepackages()
            if isinstance(usersite, str):
                roots.append(usersite)
            else:
                roots.extend(usersite)
        except Exception:
            pass
        try:
            roots.extend(site.getsitepackages())
        except Exception:
            pass
    except Exception:
        pass

    roots.extend(p for p in sys.path if p)

    # pipx keeps each app in its own venv, which sys.path never mentions when
    # you are running from a different interpreter. This is exactly the copy
    # that went unnoticed on 2026-08-31, so look for it explicitly.
    try:
        pipx_home = os.environ.get("PIPX_HOME") or (Path.home() / ".local/share/pipx")
        venv = Path(pipx_home) / "venvs" / "linafish" / "lib"
        if venv.is_dir():
            for pydir in venv.iterdir():
                roots.append(str(pydir / "site-packages"))
    except Exception:
        pass

    return roots


def find_installs() -> list:
    """Every linafish package dir on this box, de-duplicated by real path.

    Returns a list of dicts: ``{"path", "version", "executing"}``, newest
    first. Never raises; an unreadable candidate is simply skipped.
    """
    try:
        executing_path = None
        try:
            import linafish as _lf

            executing_path = str(Path(_lf.__file__).resolve().parent)
        except Exception:
            pass

        seen = {}
        for root in _candidate_roots():
            try:
                pkg = Path(root) / "linafish"
                if not (pkg / "__init__.py").is_file():
                    continue
                real = str(pkg.resolve())
                if real in seen:
                    continue
                seen[real] = {
                    "path": real,
                    "version": read_version(real) or "unknown",
                    "executing": real == executing_path,
                }
            except Exception:
                continue

        # The executing copy must appear even if it lives somewhere odd
        # (an editable checkout, a vendored tree, a zipapp extraction).
        if executing_path and executing_path not in seen:
            seen[executing_path] = {
                "path": executing_path,
                "version": read_version(executing_path) or "unknown",
                "executing": True,
            }

        return sorted(
            seen.values(), key=lambda d: version_key(d["version"]), reverse=True
        )
    except Exception:
        return []


def skew_report() -> dict:
    """Is the copy that will execute the newest copy present?

    Returns ``{"installs", "executing", "newest", "skewed", "behind_by"}``.
    ``skewed`` is True only when a strictly newer copy exists on this machine
    than the one ``import linafish`` resolves to — the case that is knowable
    for certain, offline, and that nothing was checking.
    """
    out = {
        "installs": [],
        "executing": None,
        "newest": None,
        "skewed": False,
        "behind_by": None,
    }
    try:
        installs = find_installs()
        out["installs"] = installs
        if not installs:
            return out
        executing = next((i for i in installs if i["executing"]), None)
        newest = installs[0]
        out["executing"] = executing
        out["newest"] = newest
        if executing and newest and executing["path"] != newest["path"]:
            if version_key(newest["version"]) > version_key(executing["version"]):
                out["skewed"] = True
                out["behind_by"] = (executing["version"], newest["version"])
    except Exception:
        pass
    return out


# --------------------------------------------------------------------------
# What this build knows is broken in older ones
# --------------------------------------------------------------------------

# Each entry is sourced from a CHANGELOG "Fixed" bullet. `signature` is matched
# against an exception's rendered traceback, and is only ever used to ANNOTATE
# a crash the caller already had — it never suppresses or alters the exception.
#
# Keep this honest: only add an entry when the fix is real and the version is
# the one that actually carries it.
KNOWN_FIXES = [
    {
        "id": "surrogate-content-hash",
        "fixed_in": "2.2.1",
        "exc": "UnicodeEncodeError",
        "signature": "_content_hash",
        "title": "One bad character no longer kills an entire fish.",
        "detail": (
            "A lone surrogate in a crystal's text made _content_hash raise, and "
            "_load_state hashes every crystal when dedupe=True — so the fish did "
            "not skip the bad crystal, it failed to load at all."
        ),
    },
]


def known_issues_after(version: str) -> list:
    """Fixes this build knows about that ``version`` predates.

    Returns [] when ``version`` already carries them — which is the normal
    case, and is why this function is usually silent.
    """
    try:
        vk = version_key(version)
        return [f for f in KNOWN_FIXES if vk < version_key(f["fixed_in"])]
    except Exception:
        return []


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------


def format_skew(report: dict | None = None) -> str:
    """Human-readable skew block, or '' when there is nothing to say."""
    try:
        rep = report if report is not None else skew_report()
        if not rep.get("skewed"):
            return ""
        ex = rep["executing"]
        new = rep["newest"]
        lines = [
            "  ! INSTALL SKEW — the code that runs is not the newest code here.",
            f"      executing: {ex['version']}  {ex['path']}",
            f"      newer:     {new['version']}  {new['path']}",
        ]
        issues = known_issues_after(ex["version"])
        if issues:
            lines.append(
                f"      {len(issues)} known fix(es) are missing from the executing copy:"
            )
            for f in issues:
                lines.append(f"        - [{f['fixed_in']}] {f['title']}")
        lines.append(
            "      A defect is closed when the fix is in the path that EXECUTES."
        )
        return "\n".join(lines)
    except Exception:
        return ""


def crash_advisory(exc: BaseException, tb_text: str = "") -> str:
    """Annotate an uncaught exception. '' when nothing useful is known.

    NEVER swallows, alters, or delays the exception — the caller re-raises.
    """
    try:
        parts = []
        try:
            import linafish as _lf

            version = getattr(_lf, "__version__", "unknown")
            path = str(Path(_lf.__file__).resolve().parent)
        except Exception:
            version, path = "unknown", "unknown"

        name = type(exc).__name__
        for f in KNOWN_FIXES:
            if f["exc"] != name:
                continue
            if f["signature"] and f["signature"] not in tb_text:
                continue
            if version_key(version) >= version_key(f["fixed_in"]):
                continue
            parts.append(
                f"  This crash is a KNOWN BUG, fixed in linafish {f['fixed_in']}.\n"
                f"    {f['title']}\n"
                f"    You are running {version} from {path}\n"
                f"    Run: linafish update"
            )
            break

        skew = format_skew()
        if skew:
            parts.append(skew)

        if not parts:
            return ""
        return "\n\n".join(["", "-" * 60, "linafish says:"] + parts + ["-" * 60])
    except Exception:
        return ""
