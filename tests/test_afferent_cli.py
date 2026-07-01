"""Tests for the `linafish afferent` top-level CLI verb.

`linafish.afferent` is a built, tested module (the school-router organ) but
until now was only reachable via `python -m linafish.afferent`. This test
covers the fold-in: (a) `afferent` is a recognized top-level subcommand, and
(b) `build` + `route` work end-to-end through the CLI against a tiny temp
school fixture, wrapping `build_index`/`surface_for` without reimplementing
them.
"""
import json
import subprocess
import sys
from pathlib import Path


def _run(*args):
    return subprocess.run(
        [sys.executable, "-m", "linafish", *args],
        capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )


def test_afferent_is_a_recognized_subcommand():
    result = _run("--help")
    assert result.returncode == 0
    assert "afferent" in result.stdout


def test_afferent_build_and_route_end_to_end(tmp_path: Path):
    # A tiny two-member school, each with a distinct topic.
    school_dir = tmp_path / "school"
    billing_dir = school_dir / "billing"
    billing_dir.mkdir(parents=True)
    garden_dir = school_dir / "garden"
    garden_dir.mkdir(parents=True)

    def _write_crystals(member_dir, name, texts):
        cf = member_dir / f"{name}_crystals.jsonl"
        with cf.open("w", encoding="utf-8") as fh:
            for t in texts:
                fh.write(json.dumps({"text": t, "ache": 1.0}) + "\n")

    _write_crystals(billing_dir, "billing", [
        "the billing webhook failed to reset the invoice charge",
        "billing webhook retried the charge and the invoice cleared",
        "reset the billing webhook before the next invoice cycle",
    ])
    _write_crystals(garden_dir, "garden", [
        "the tomatoes need watering before the frost tonight",
        "planted basil and peppers near the tomatoes this weekend",
        "the frost warning means covering the tomatoes and basil",
    ])

    topics = {
        "billing": ["billing", "webhook"],
        "garden": ["tomatoes", "frost"],
    }
    (school_dir / "afferent_topics.json").write_text(
        json.dumps(topics), encoding="utf-8"
    )

    index_path = school_dir / "afferent_index.json"

    build_result = _run("afferent", "build", str(school_dir), str(index_path))
    assert build_result.returncode == 0, build_result.stderr
    assert "billing" in build_result.stdout
    assert "garden" in build_result.stdout
    assert index_path.exists()

    index_data = json.loads(index_path.read_text(encoding="utf-8"))
    assert index_data["_meta"]["n_members"] == 2
    assert set(index_data["members"]) == {"billing", "garden"}

    route_result = _run(
        "afferent", "route", str(index_path),
        "reset", "the", "billing", "webhook",
    )
    assert route_result.returncode == 0, route_result.stderr
    assert "billing" in route_result.stdout
    assert "garden" not in route_result.stdout

    # `surface` is an accepted alias for `route`.
    surface_result = _run(
        "afferent", "surface", str(index_path),
        "cover", "the", "tomatoes", "before", "frost",
    )
    assert surface_result.returncode == 0, surface_result.stderr
    assert "garden" in surface_result.stdout
