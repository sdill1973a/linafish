"""
Init — the fish eats everything, finds the best, keeps chugging.

linafish init reads .mcp.json files — yours, your sister's, your
fleet's — eats every server's tool definitions, and builds a shared
codebook. The crystallizer deduplicates naturally. Compression IS
curation.

Controlled borg reaction. Shared context. Everyone works as hard
as they need to.
"""

from __future__ import annotations


import json
import shutil
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional

from .codebook import Codebook, Glyph
from .eat import eat_mcp_schema, eat_mcp_live


def find_mcp_json() -> Optional[Path]:
    """Find the local .mcp.json file by walking up from CWD (like git finds .git)."""
    # Walk up from CWD
    current = Path.cwd()
    while current != current.parent:
        candidate = current / ".mcp.json"
        if candidate.exists():
            return candidate
        current = current.parent

    # Fallback to home dir locations
    for p in [
        Path.home() / ".claude" / ".mcp.json",
        Path.home() / ".mcp.json",
    ]:
        if p.exists():
            return p
    return None


def fetch_remote_config(remote: str) -> Optional[dict]:
    """Fetch a .mcp.json from a remote host.

    Accepts:
      ssh://user@host/path/to/.mcp.json
      user@host:/path/to/.mcp.json
      http://host:port/.mcp.json
    """
    if remote.startswith("ssh://") or "@" in remote:
        # SSH fetch
        ssh_target = remote.replace("ssh://", "")
        if ":" not in ssh_target.split("@")[-1]:
            # ssh://user@host/.mcp.json -> user@host:.mcp.json
            parts = ssh_target.split("/", 1)
            ssh_target = f"{parts[0]}:{parts[1]}" if len(parts) > 1 else ssh_target
        try:
            result = subprocess.run(
                ["ssh", ssh_target.split(":")[0], "cat", ssh_target.split(":")[-1]],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                return json.loads(result.stdout)
        except Exception as e:
            print(f"  Remote fetch failed ({remote}): {e}")
        return None

    if remote.startswith("http"):
        import urllib.request
        try:
            with urllib.request.urlopen(remote, timeout=10) as resp:
                return json.loads(resp.read())
        except Exception as e:
            print(f"  Remote fetch failed ({remote}): {e}")
        return None

    # Try as a local path
    p = Path(remote)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))

    return None


def _eat_servers(servers: dict, codebook: Codebook, source_label: str,
                 live: bool = False) -> int:
    """Eat all servers from a config dict into the codebook.
    Returns count of servers eaten."""
    eaten = 0
    for server_name, server_config in servers.items():
        if server_name == "linafish":
            continue

        server_config["name"] = server_name
        print(f"  [{source_label}] {server_name}...", end="")

        if live:
            eat_mcp_live(server_name, server_config, codebook)
            print(f" (live)")
        else:
            # Build a glyph from the config metadata
            desc = f"MCP server: {server_name}"
            command = server_config.get("command", "")
            args = server_config.get("args", [])
            if command:
                desc += f" (cmd: {command})"
            if args:
                desc += f" args: {' '.join(str(a) for a in args[:3])}"

            env = server_config.get("env", {})
            env_keys = [k for k in env.keys() if "token" not in k.lower()
                        and "key" not in k.lower() and "secret" not in k.lower()]
            if env_keys:
                desc += f" env: {', '.join(env_keys[:5])}"

            glyph = Glyph(
                id=f"MCP_{server_name}".upper().replace("-", "_")[:20],
                layer=1,
                dense=desc[:500],
                sources=[f"mcp://{source_label}/{server_name}"],
                weight=1.5,
            )
            codebook.add_glyph(glyph)
            print(f" -> {glyph.id}")

        eaten += 1
    return eaten


def init_fish(
    mcp_json_path: Optional[Path] = None,
    remotes: Optional[list[str]] = None,
    fish_name: str = "linafish",
    live: bool = False,
    backup: bool = True,
) -> tuple[Codebook, Path]:
    """Initialize LiNafish from one or more .mcp.json files.

    The fish eats everything. Yours, your sister's, your fleet's.
    The crystallizer finds the best. The codebook keeps chugging.

    Args:
        mcp_json_path: Local .mcp.json (auto-detected if None)
        remotes: List of remote configs to also eat
                 (ssh://user@host/path, http://..., or local paths)
        fish_name: Name for the codebook
        live: If True, spawn servers to discover tools (slow but thorough)
        backup: Backup local .mcp.json before eating

    Returns (codebook, mcp_json_path)
    """
    if mcp_json_path is None:
        mcp_json_path = find_mcp_json()

    codebook = Codebook(name=fish_name, description="LiNafish — shared context")
    total_servers = 0

    # Eat local config
    if mcp_json_path and mcp_json_path.exists():
        with open(mcp_json_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        servers = config.get("mcpServers", {})
        print(f"Local: {len(servers)} servers in {mcp_json_path}")

        if backup:
            backup_path = mcp_json_path.with_suffix(
                f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
            shutil.copy2(mcp_json_path, backup_path)
            print(f"Backup: {backup_path}")

        total_servers += _eat_servers(servers, codebook, "local", live=live)
    else:
        print("No local .mcp.json found.")
        if mcp_json_path is None:
            mcp_json_path = Path.cwd() / ".mcp.json"

    # Eat remote configs
    if remotes:
        for remote in remotes:
            print(f"\nRemote: {remote}")
            remote_config = fetch_remote_config(remote)
            if remote_config:
                servers = remote_config.get("mcpServers", {})
                print(f"  Found {len(servers)} servers")
                label = remote.split("@")[-1].split("/")[0].split(":")[0] if "@" in remote else remote
                total_servers += _eat_servers(servers, codebook, label, live=False)
            else:
                print(f"  Could not read remote config")

    codebook.exchanges = total_servers
    codebook.description = f"LiNafish — ate {total_servers} servers"

    print(f"\nCodebook: {len(codebook.glyphs)} glyphs from {total_servers} servers")
    print(f"Saturation: {codebook.saturation:.0f}%")

    return codebook, mcp_json_path
