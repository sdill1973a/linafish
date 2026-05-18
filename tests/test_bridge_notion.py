"""Tests for linafish.bridges.notion — Notion → fish sync.

Mocks the Notion API at the urllib level so tests don't hit real
endpoints. Verifies auth resolution, state-file load/save, page
formatting, incremental skip, and full-pull mode.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from linafish.bridges.notion import (
    NotionBridgeResult,
    _blocks_to_text,
    _default_state_path,
    _extract_page_title,
    _format_crystal_text,
    _load_state,
    _resolve_token,
    _save_state,
    pull_notion,
)


# ----------------------------- _resolve_token -----------------------------

def test_resolve_token_uses_explicit():
    assert _resolve_token("explicit-token-123") == "explicit-token-123"


def test_resolve_token_uses_env(monkeypatch):
    monkeypatch.setenv("NOTION_API_KEY", "env-token-xyz")
    assert _resolve_token() == "env-token-xyz"


def test_resolve_token_explicit_wins_over_env(monkeypatch):
    monkeypatch.setenv("NOTION_API_KEY", "env-token")
    assert _resolve_token("explicit") == "explicit"


def test_resolve_token_raises_when_missing(monkeypatch):
    monkeypatch.delenv("NOTION_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="Notion token not found"):
        _resolve_token()


# ----------------------------- state -----------------------------

def test_default_state_path_creates_bridges_dir(tmp_path: Path):
    p = _default_state_path(state_root=tmp_path)
    assert p == tmp_path / "bridges" / "notion-state.json"
    assert p.parent.exists()  # bridges/ was created


def test_load_state_returns_empty_when_absent(tmp_path: Path):
    state = _load_state(tmp_path / "missing.json")
    assert state == {"pages": {}}


def test_load_state_recovers_from_corruption(tmp_path: Path):
    p = tmp_path / "corrupt.json"
    p.write_text("not valid json", encoding="utf-8")
    state = _load_state(p)
    assert state == {"pages": {}}


def test_save_and_load_roundtrip(tmp_path: Path):
    p = tmp_path / "state.json"
    _save_state(p, {"pages": {"abc123": "2026-05-18T00:00:00Z"}})
    state = _load_state(p)
    assert state == {"pages": {"abc123": "2026-05-18T00:00:00Z"}}


# ----------------------------- page extraction -----------------------------

def test_extract_page_title_normal():
    page = {
        "properties": {
            "Name": {
                "type": "title",
                "title": [{"plain_text": "My Page"}],
            }
        }
    }
    assert _extract_page_title(page) == "My Page"


def test_extract_page_title_multipart():
    page = {
        "properties": {
            "Name": {
                "type": "title",
                "title": [{"plain_text": "Part "}, {"plain_text": "Two"}],
            }
        }
    }
    assert _extract_page_title(page) == "Part Two"


def test_extract_page_title_no_title_property():
    page = {"properties": {"Tags": {"type": "multi_select"}}}
    assert _extract_page_title(page) == "(untitled)"


# ----------------------------- blocks -----------------------------

def test_blocks_to_text_paragraphs_and_headings():
    blocks = [
        {"type": "heading_1", "heading_1": {"rich_text": [{"plain_text": "Title"}]}},
        {"type": "paragraph", "paragraph": {"rich_text": [{"plain_text": "Body line."}]}},
        {"type": "bulleted_list_item", "bulleted_list_item": {"rich_text": [{"plain_text": "item"}]}},
    ]
    out = _blocks_to_text(blocks)
    assert "# Title" in out
    assert "Body line." in out
    assert "- item" in out


def test_blocks_to_text_skips_empty():
    blocks = [
        {"type": "paragraph", "paragraph": {"rich_text": []}},
        {"type": "paragraph", "paragraph": {"rich_text": [{"plain_text": "real"}]}},
    ]
    out = _blocks_to_text(blocks)
    assert out == "real"


def test_format_crystal_text_includes_header():
    page = {
        "id": "abc",
        "last_edited_time": "2026-05-18T10:00:00.000Z",
        "properties": {
            "Name": {"type": "title", "title": [{"plain_text": "Test Page"}]}
        }
    }
    out = _format_crystal_text(page, "Body text")
    assert "[notion 2026-05-18 Test Page]" in out
    assert "Body text" in out


def test_format_crystal_text_truncates_long_bodies():
    page = {
        "id": "abc",
        "last_edited_time": "2026-05-18T10:00:00.000Z",
        "properties": {"Name": {"type": "title", "title": [{"plain_text": "Long"}]}}
    }
    long_body = "x" * 50000
    out = _format_crystal_text(page, long_body)
    assert len(out) < 50000
    assert out.endswith("[truncated]")


# ----------------------------- pull_notion (mocked API) -----------------------------

def test_pull_notion_dry_run_no_pages(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("NOTION_API_KEY", "fake-token")
    with patch(
        "linafish.bridges.notion._api_request",
        return_value={"results": []},
    ):
        result = pull_notion(
            state_root=tmp_path,
            dry_run=True,
        )
    assert result.pages_seen == 0
    assert result.pages_deposited == 0


def test_pull_notion_dry_run_with_pages(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("NOTION_API_KEY", "fake-token")
    fake_page = {
        "id": "page-1",
        "last_edited_time": "2026-05-18T10:00:00.000Z",
        "properties": {"Name": {"type": "title", "title": [{"plain_text": "P1"}]}}
    }
    # Mock /search returns one page; subsequent /blocks/... returns content
    call_count = {"n": 0}
    def fake_api(method, path, token, body=None, timeout=30):
        call_count["n"] += 1
        if path == "/search":
            return {"results": [fake_page]}
        if "/blocks/" in path:
            return {"results": [
                {"type": "paragraph", "paragraph": {"rich_text": [{"plain_text": "content"}]}}
            ]}
        return {"results": []}
    with patch("linafish.bridges.notion._api_request", side_effect=fake_api):
        result = pull_notion(state_root=tmp_path, dry_run=True)
    assert result.pages_seen == 1
    assert result.pages_deposited == 1  # incremented in dry_run too (logical "would deposit")
    # State NOT saved because dry_run
    state_path = tmp_path / "bridges" / "notion-state.json"
    assert not state_path.exists()


def test_pull_notion_incremental_skips_unchanged(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("NOTION_API_KEY", "fake-token")
    # Pre-populate state with this page's last_edited_time
    state_path = tmp_path / "bridges" / "notion-state.json"
    state_path.parent.mkdir(parents=True)
    _save_state(state_path, {"pages": {"page-1": "2026-05-18T10:00:00.000Z"}})

    fake_page = {
        "id": "page-1",
        "last_edited_time": "2026-05-18T10:00:00.000Z",
        "properties": {"Name": {"type": "title", "title": [{"plain_text": "P1"}]}}
    }
    with patch(
        "linafish.bridges.notion._api_request",
        return_value={"results": [fake_page]},
    ):
        result = pull_notion(state_root=tmp_path, dry_run=True)
    assert result.pages_seen == 1
    assert result.pages_deposited == 0
    assert result.pages_skipped_unchanged == 1


def test_pull_notion_full_mode_ignores_state(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("NOTION_API_KEY", "fake-token")
    # Pre-populate state with the page's mark
    state_path = tmp_path / "bridges" / "notion-state.json"
    state_path.parent.mkdir(parents=True)
    _save_state(state_path, {"pages": {"page-1": "2026-05-18T10:00:00.000Z"}})

    fake_page = {
        "id": "page-1",
        "last_edited_time": "2026-05-18T10:00:00.000Z",
        "properties": {"Name": {"type": "title", "title": [{"plain_text": "P1"}]}}
    }
    def fake_api(method, path, token, body=None, timeout=30):
        if path == "/search":
            return {"results": [fake_page]}
        return {"results": []}
    with patch("linafish.bridges.notion._api_request", side_effect=fake_api):
        result = pull_notion(state_root=tmp_path, dry_run=True, full=True)
    assert result.pages_seen == 1
    assert result.pages_deposited == 1  # full mode re-deposits
    assert result.pages_skipped_unchanged == 0


def test_pull_notion_raises_when_token_missing(monkeypatch, tmp_path: Path):
    monkeypatch.delenv("NOTION_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="Notion token not found"):
        pull_notion(state_root=tmp_path)
