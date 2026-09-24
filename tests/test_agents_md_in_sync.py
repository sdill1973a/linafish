"""`linafish introduce` prints the packaged AGENTS.md; GitHub shows the repo one.

2.3.1's review found the packaged copy a release behind the repo copy — an assistant
that ran `introduce` got instructions the repo had already corrected. They are one
document in two places; this keeps them one.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_packaged_agents_md_matches_repo_copy():
    repo = (ROOT / "AGENTS.md").read_bytes()
    packaged = (ROOT / "linafish" / "data" / "AGENTS.md").read_bytes()
    assert packaged == repo, "copy AGENTS.md to linafish/data/AGENTS.md"
