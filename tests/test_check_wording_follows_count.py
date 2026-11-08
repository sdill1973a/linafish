"""`check` must not claim "I know you." below the material bar.

Found 2026-11-07 (THX, Windows; Anchor, Linux) in a new-user audit: 13 passages from 8 short
documents gave 8 formations, and `check` said "I know you." while its own advice two lines
later said it needs about 30 entries to see clearly. The wording now follows the count.
"""
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

TOPICS = ["the garden in spring", "my father's workshop", "learning to fail", "rain on the tin roof",
          "a long drive home", "what I keep coming back to", "the garden after frost", "keeping promises"]


def _doc(topic, i):
    return (f"{topic.capitalize()}, entry {i}.\n\n" + " ".join(
        f"I think about {topic} and how it changed me. The garden taught patience; the work taught "
        f"care. I wanted to understand why I return to it, and I test what I believe against it."
        for _ in range(6)))


def _cli(home, *argv):
    env = {**os.environ, "HOME": str(home), "USERPROFILE": str(home), "PYTHONPATH": str(ROOT)}
    env.pop("LINAFISH_PROTECTED_VOCAB", None)
    return subprocess.run([sys.executable, "-m", "linafish", *argv], env=env, capture_output=True,
                          text=True, timeout=300)


def _fish(tmp_path, n_docs):
    home = tmp_path / "home"
    src = home / "my-writing"
    src.mkdir(parents=True)
    for i in range(n_docs):
        (src / f"d{i:02d}.txt").write_text(_doc(TOPICS[i % len(TOPICS)], i), encoding="utf-8")
    r = _cli(home, "go", str(src), "--no-serve")
    assert r.returncode == 0, r.stdout + r.stderr
    return home


def _counts(out):
    line = next(l for l in out.splitlines() if "You've fed me" in l)
    words = line.split()
    return int(words[words.index("me") + 1]), int(words[words.index("see") + 1])


def test_check_below_bar_does_not_claim_to_know_you(tmp_path):
    home = _fish(tmp_path, 8)
    r = _cli(home, "check", "-n", "my-writing")
    crystals, formations = _counts(r.stdout)
    assert 10 <= crystals < 30 and formations > 5, (crystals, formations)  # the case that misfired
    assert "I know you." not in r.stdout, r.stdout
    assert "guess" in r.stdout.lower(), r.stdout


def test_check_at_bar_still_says_it(tmp_path):
    home = _fish(tmp_path, 24)
    r = _cli(home, "check", "-n", "my-writing")
    crystals, formations = _counts(r.stdout)
    if crystals < 30 or formations <= 5:
        pytest.skip(f"fixture gave {crystals} crystals / {formations} formations; needs >=30 and >5")
    assert "I know you." in r.stdout, r.stdout
