"""Notion → fish bridge.

Pulls recently-edited Notion pages and deposits them into a linafish
fish. Stateful (incremental) by default: remembers each page's
last_edited_time so re-runs only deposit pages that changed since
the last marker.

Auth: requires a Notion integration token. Provide via:
  - NOTION_API_KEY environment variable, OR
  - --token flag on the CLI

To create a Notion integration token:
  1. Go to https://www.notion.so/my-integrations
  2. Click "New integration"
  3. Pick the workspace + capabilities (Read content is enough)
  4. Copy the "Internal Integration Token" (starts with `secret_` or `ntn_`)
  5. In Notion, share the pages/databases you want crawled WITH the integration

Default deposit target: a local fish named `notion` at ~/.linafish/notion/
via FishEngine (no HTTP server required). Override with --fish NAME to
send to a different local fish.

Origin: ported from scripts/notion_to_fish.py (anchor-side, 440 lines
of HTTP-deposit + retry/backoff bells). This 1.4 port is the minimal
useful shape: env-or-flag auth, incremental state, local deposit via
FishEngine, JSON-API search for recent pages, markdown-stripping page
body. Bells (HTTP target, retry/backoff, scheduling) are followup work.
"""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


NOTION_API = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"
HTTP_TIMEOUT = 30
SEARCH_PAGE_SIZE = 25
MAX_PAGE_CHARS = 20000


@dataclass
class NotionBridgeResult:
    pages_seen: int
    pages_deposited: int
    pages_skipped_unchanged: int
    pages_failed: int
    errors: list[str]


def _resolve_token(explicit: Optional[str] = None) -> str:
    """Resolve the Notion token from arg or NOTION_API_KEY env var."""
    if explicit:
        return explicit
    token = os.environ.get("NOTION_API_KEY")
    if not token:
        raise RuntimeError(
            "Notion token not found. Set NOTION_API_KEY env var, or pass --token. "
            "Create one at https://www.notion.so/my-integrations and share pages with it."
        )
    return token


def _default_state_path(state_root: Optional[Path] = None) -> Path:
    if state_root is None:
        state_root = Path.home() / ".linafish"
    bridges_dir = state_root / "bridges"
    bridges_dir.mkdir(parents=True, exist_ok=True)
    return bridges_dir / "notion-state.json"


def _load_state(state_path: Path) -> dict:
    if not state_path.exists():
        return {"pages": {}}
    try:
        return json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"pages": {}}


def _save_state(state_path: Path, state: dict) -> None:
    try:
        state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
    except OSError:
        pass


def _api_request(
    method: str,
    path: str,
    token: str,
    body: Optional[dict] = None,
    timeout: int = HTTP_TIMEOUT,
) -> dict:
    """Make a Notion API request. Raises on non-2xx."""
    url = f"{NOTION_API}{path}" if path.startswith("/") else path
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Notion-Version", NOTION_VERSION)
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    return json.loads(raw)


def search_recent_pages(token: str, page_size: int = SEARCH_PAGE_SIZE) -> list[dict]:
    """Use Notion /v1/search to list recently-edited pages."""
    body = {
        "filter": {"property": "object", "value": "page"},
        "sort": {"direction": "descending", "timestamp": "last_edited_time"},
        "page_size": page_size,
    }
    result = _api_request("POST", "/search", token, body=body)
    return result.get("results", [])


def _extract_page_title(page: dict) -> str:
    """Pull the title out of a Notion page object. Best-effort."""
    props = page.get("properties", {})
    for name, prop in props.items():
        if prop.get("type") == "title":
            title_arr = prop.get("title", [])
            if title_arr:
                return "".join(t.get("plain_text", "") for t in title_arr).strip()
    return "(untitled)"


def _fetch_page_blocks(token: str, page_id: str) -> list[dict]:
    """Pull all top-level blocks for a page."""
    result = _api_request("GET", f"/blocks/{page_id}/children?page_size=100", token)
    return result.get("results", [])


def _blocks_to_text(blocks: list[dict]) -> str:
    """Flatten Notion blocks into plain-ish markdown."""
    lines: list[str] = []
    for block in blocks:
        btype = block.get("type", "")
        content = block.get(btype, {})
        rich = content.get("rich_text", [])
        text = "".join(t.get("plain_text", "") for t in rich).strip()
        if not text:
            continue
        if btype == "heading_1":
            lines.append(f"# {text}")
        elif btype == "heading_2":
            lines.append(f"## {text}")
        elif btype == "heading_3":
            lines.append(f"### {text}")
        elif btype == "bulleted_list_item":
            lines.append(f"- {text}")
        elif btype == "numbered_list_item":
            lines.append(f"1. {text}")
        elif btype == "code":
            lines.append(f"```\n{text}\n```")
        elif btype == "quote":
            lines.append(f"> {text}")
        else:
            lines.append(text)
    return "\n\n".join(lines)


def _format_crystal_text(page: dict, body_text: str) -> str:
    """Compose the crystal text from page title + body. Caps length."""
    title = _extract_page_title(page)
    page_id = page.get("id", "")
    last_edited = page.get("last_edited_time", "")
    date_part = last_edited.split("T")[0] if last_edited else ""
    header = f"[notion {date_part} {title}]"
    full = f"{header}\n\n{body_text}".strip()
    if len(full) > MAX_PAGE_CHARS:
        full = full[:MAX_PAGE_CHARS] + "\n\n[truncated]"
    return full


def pull_notion(
    token: Optional[str] = None,
    fish_name: str = "notion",
    state_root: Optional[Path] = None,
    state_path: Optional[Path] = None,
    full: bool = False,
    dry_run: bool = False,
    page_size: int = SEARCH_PAGE_SIZE,
) -> NotionBridgeResult:
    """Pull recent Notion pages, deposit into the target fish.

    Args:
        token: Notion integration token. Falls back to NOTION_API_KEY env.
        fish_name: target fish name (default 'notion'). Fish lives at
            <state_root>/<fish_name>/.
        state_root: parent dir for state + fish (default ~/.linafish).
        state_path: override the state file location (default
            <state_root>/bridges/notion-state.json).
        full: ignore the state file's marks; re-deposit every page found.
        dry_run: scan + report, but don't deposit or update state.
        page_size: how many pages /v1/search returns per call (max 100).

    Returns:
        NotionBridgeResult with counts + any errors.
    """
    token = _resolve_token(token)
    if state_path is None:
        state_path = _default_state_path(state_root)
    state = _load_state(state_path)

    pages = search_recent_pages(token, page_size=page_size)
    seen = len(pages)
    deposited = 0
    skipped = 0
    failed = 0
    errors: list[str] = []

    if not pages:
        return NotionBridgeResult(
            pages_seen=0, pages_deposited=0,
            pages_skipped_unchanged=0, pages_failed=0,
            errors=[],
        )

    # Lazy import: only spin up FishEngine if we're going to actually deposit
    engine = None
    if not dry_run:
        if state_root is None:
            state_root = Path.home() / ".linafish"
        fish_dir = state_root / fish_name
        fish_dir.mkdir(parents=True, exist_ok=True)
        from ..engine import FishEngine
        engine = FishEngine(name=fish_name, state_dir=fish_dir)

    for page in pages:
        page_id = page.get("id", "")
        last_edited = page.get("last_edited_time", "")
        prev_mark = state["pages"].get(page_id)
        if not full and prev_mark == last_edited:
            skipped += 1
            continue
        try:
            blocks = _fetch_page_blocks(token, page_id)
            body_text = _blocks_to_text(blocks)
            crystal_text = _format_crystal_text(page, body_text)
            if not dry_run:
                # Engine.eat (single-string) — fall back to writing a
                # temp file + eat_path if engine has no eat method
                if hasattr(engine, "eat"):
                    engine.eat(crystal_text)
                else:
                    tmp = state_path.parent / f"_notion_{page_id}.tmp.md"
                    tmp.write_text(crystal_text, encoding="utf-8")
                    try:
                        engine.eat_path(tmp)
                    finally:
                        try:
                            tmp.unlink()
                        except OSError:
                            pass
                state["pages"][page_id] = last_edited
            deposited += 1
        except (urllib.error.HTTPError, urllib.error.URLError, Exception) as e:
            failed += 1
            errors.append(f"page {page_id[:8]}: {type(e).__name__}: {e}")

    if not dry_run:
        _save_state(state_path, state)

    return NotionBridgeResult(
        pages_seen=seen,
        pages_deposited=deposited,
        pages_skipped_unchanged=skipped,
        pages_failed=failed,
        errors=errors,
    )
