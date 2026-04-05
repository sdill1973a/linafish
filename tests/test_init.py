"""Tests for init — can the fish eat a whole .mcp.json?"""
import json
import tempfile
from pathlib import Path

from linafish.init import init_fish, fetch_remote_config


def test_init_from_mcp_json():
    """Feed the fish a minimal .mcp.json."""
    config = {
        "mcpServers": {
            "clipboard": {
                "command": "python",
                "args": ["clipboard_server.py"],
            },
            "notify": {
                "command": "python",
                "args": ["notify_server.py"],
                "env": {"PYTHONPATH": "/opt/notify"},
            },
        }
    }

    with tempfile.NamedTemporaryFile(
        suffix=".json", delete=False, mode="w", encoding="utf-8"
    ) as f:
        json.dump(config, f)
        path = Path(f.name)

    codebook, _ = init_fish(mcp_json_path=path, backup=False)
    assert len(codebook.glyphs) == 2
    assert any("CLIPBOARD" in gid for gid in codebook.glyphs)
    assert any("NOTIFY" in gid for gid in codebook.glyphs)
    path.unlink()


def test_init_skips_linafish():
    """The fish doesn't eat itself."""
    config = {
        "mcpServers": {
            "linafish": {"command": "linafish", "args": ["serve"]},
            "ollama": {"command": "python", "args": ["ollama_server.py"]},
        }
    }

    with tempfile.NamedTemporaryFile(
        suffix=".json", delete=False, mode="w", encoding="utf-8"
    ) as f:
        json.dump(config, f)
        path = Path(f.name)

    codebook, _ = init_fish(mcp_json_path=path, backup=False)
    assert len(codebook.glyphs) == 1  # only ollama, not linafish
    assert not any("LINAFISH" in gid for gid in codebook.glyphs)
    path.unlink()


def test_init_fresh_when_no_config():
    """No .mcp.json = fresh fish, not crash."""
    codebook, _ = init_fish(mcp_json_path=Path("/nonexistent/.mcp.json"), backup=False)
    assert len(codebook.glyphs) == 0
    assert codebook.name == "linafish"


def test_init_strips_secrets():
    """Tokens and keys should not appear in glyph descriptions."""
    config = {
        "mcpServers": {
            "ha": {
                "command": "uvx",
                "args": ["hass-mcp"],
                "env": {
                    "HA_URL": "http://10.0.0.1:8123",
                    "HA_TOKEN": "eyJ_secret_token_here",
                    "API_KEY": "sk-secret-key",
                },
            }
        }
    }

    with tempfile.NamedTemporaryFile(
        suffix=".json", delete=False, mode="w", encoding="utf-8"
    ) as f:
        json.dump(config, f)
        path = Path(f.name)

    codebook, _ = init_fish(mcp_json_path=path, backup=False)
    for glyph in codebook.glyphs.values():
        assert "secret" not in glyph.dense.lower()
        assert "TOKEN" not in glyph.dense
        assert "KEY" not in glyph.dense

    path.unlink()


def test_fetch_remote_local_path():
    """fetch_remote_config works with local paths."""
    config = {"mcpServers": {"test": {"command": "echo"}}}

    with tempfile.NamedTemporaryFile(
        suffix=".json", delete=False, mode="w", encoding="utf-8"
    ) as f:
        json.dump(config, f)
        path = Path(f.name)

    result = fetch_remote_config(str(path))
    assert result is not None
    assert "mcpServers" in result
    path.unlink()


def test_init_multiple_remotes():
    """init_fish can eat local + multiple remote configs."""
    local = {"mcpServers": {"clipboard": {"command": "python", "args": ["clip.py"]}}}
    remote1 = {"mcpServers": {"notify": {"command": "python", "args": ["notify.py"]}}}
    remote2 = {"mcpServers": {"speak": {"command": "python", "args": ["speak.py"]}}}

    files = []
    for config in [local, remote1, remote2]:
        f = tempfile.NamedTemporaryFile(
            suffix=".json", delete=False, mode="w", encoding="utf-8"
        )
        json.dump(config, f)
        f.close()
        files.append(Path(f.name))

    codebook, _ = init_fish(
        mcp_json_path=files[0],
        remotes=[str(files[1]), str(files[2])],
        backup=False,
    )
    assert len(codebook.glyphs) == 3
    assert any("CLIPBOARD" in gid for gid in codebook.glyphs)
    assert any("NOTIFY" in gid for gid in codebook.glyphs)
    assert any("SPEAK" in gid for gid in codebook.glyphs)

    for f in files:
        f.unlink()


def test_init_deduplicates_same_server():
    """When two configs have the same server name, the glyph merges."""
    config1 = {"mcpServers": {"ollama": {"command": "python", "args": ["v1.py"]}}}
    config2 = {"mcpServers": {"ollama": {"command": "python", "args": ["v2.py"]}}}

    files = []
    for config in [config1, config2]:
        f = tempfile.NamedTemporaryFile(
            suffix=".json", delete=False, mode="w", encoding="utf-8"
        )
        json.dump(config, f)
        f.close()
        files.append(Path(f.name))

    codebook, _ = init_fish(
        mcp_json_path=files[0],
        remotes=[str(files[1])],
        backup=False,
    )
    # Same glyph ID — should be 1, not 2
    assert len(codebook.glyphs) == 1
    assert "MCP_OLLAMA" in codebook.glyphs

    for f in files:
        f.unlink()
