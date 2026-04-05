"""
Eat — the fish swallows.

linafish eat <path>        — ingest files into the codebook
linafish eat <mcp-server>  — ingest an MCP server's tool definitions

The fish doesn't proxy. It UNDERSTANDS. The tool becomes a glyph.
The glyph survives. The original server can go dark and the
fish still knows what it did.
"""

import json
from pathlib import Path
from typing import Optional

from .codebook import Codebook, Glyph
from .ingest import ingest_directory, ingest_file
from .compress import compress_chunks, compress_with_crystallizer


def eat_path(
    path: Path,
    codebook: Codebook,
    use_crystallizer: bool = True,
    crystallizer_url: str = "http://localhost:8802",
) -> Codebook:
    """Eat files from a path into an existing codebook."""

    if path.is_dir():
        chunks = ingest_directory(path, recursive=True)
    elif path.is_file():
        chunks = ingest_file(path)
    else:
        print(f"Cannot eat: {path} not found")
        return codebook

    if not chunks:
        print(f"No content found in {path}")
        return codebook

    if use_crystallizer:
        new_book = compress_with_crystallizer(
            chunks, codebook.name, codebook.description,
            crystallizer_url=crystallizer_url,
        )
    else:
        new_book = compress_chunks(chunks, codebook.name, codebook.description)

    # Merge new glyphs into existing codebook
    for gid, glyph in new_book.glyphs.items():
        if gid in codebook.glyphs:
            # Merge: keep higher weight, combine sources
            existing = codebook.glyphs[gid]
            existing.weight = max(existing.weight, glyph.weight)
            existing.sources = list(set(existing.sources + glyph.sources))
            existing.connections = list(set(existing.connections + glyph.connections))
        else:
            codebook.add_glyph(glyph)

    codebook.exchanges += new_book.exchanges

    # Recalculate R(n)
    total_raw = sum(len(c.text) for c in chunks)
    total_compressed = sum(len(g.dense) for g in codebook.glyphs.values())
    if total_compressed > 0:
        codebook.r_n = total_raw / total_compressed

    return codebook


def eat_exchange(
    sender: str,
    receiver: str,
    text: str,
    codebook: Codebook,
    rn: float = 0.0,
    fp: float = 0.0,
    timestamp: str = "",
    use_crystallizer: bool = True,
    crystallizer_url: str = "http://localhost:8802",
) -> Codebook:
    """Eat a live RCP exchange into the codebook.

    The fish listens to the room. Every exchange crystallizes.
    No files. No paths. Just two minds talking and the fish learning.
    """
    from .ingest import Chunk

    if len(text) < 20:
        return codebook

    source = f"rcp://{sender}->{receiver}"
    if timestamp:
        source += f"@{timestamp[:16]}"

    chunk = Chunk(
        text=text,
        source=source,
        section=f"{sender} to {receiver}",
        chunk_type="exchange",
        position=codebook.exchanges,
    )

    if use_crystallizer:
        new_book = compress_with_crystallizer(
            [chunk], codebook.name, codebook.description,
            crystallizer_url=crystallizer_url,
        )
    else:
        new_book = compress_chunks([chunk], codebook.name, codebook.description)

    for gid, glyph in new_book.glyphs.items():
        # Tag with RCP metadata
        glyph.sources.append(source)
        if rn > 0:
            glyph.weight *= (1 + rn * 0.1)  # higher R(n) = more trusted
        if gid in codebook.glyphs:
            existing = codebook.glyphs[gid]
            existing.weight = max(existing.weight, glyph.weight)
            existing.sources = list(set(existing.sources + glyph.sources))
            existing.connections = list(set(existing.connections + glyph.connections))
        else:
            codebook.add_glyph(glyph)

    codebook.exchanges += 1

    total_raw = len(text)
    total_compressed = sum(len(g.dense) for g in codebook.glyphs.values())
    if total_compressed > 0:
        codebook.r_n = (codebook.r_n * (codebook.exchanges - 1) + total_raw / total_compressed) / codebook.exchanges

    return codebook


def eat_mcp_schema(
    server_config: dict,
    codebook: Codebook,
) -> Codebook:
    """Eat an MCP server's tool definitions.

    Takes a server config from .mcp.json and ingests
    all tool definitions as glyphs. The server doesn't
    need to be running — we eat the SCHEMA, not the server.

    For stdio servers: read the tool list from the manifest.
    For SSE servers: connect and list_tools.
    """
    server_name = server_config.get("name", "unknown")
    tools = server_config.get("tools", [])

    if not tools:
        command = server_config.get("command", "")
        args = server_config.get("args", [])
        print(f"  [{server_name}] No tools in config, would need to connect to discover")
        return codebook

    for tool in tools:
        tool_name = tool.get("name", "unknown_tool")
        description = tool.get("description", "")
        schema = json.dumps(tool.get("inputSchema", {}), indent=2)

        dense = f"{tool_name}: {description}"
        if schema and schema != "{}":
            dense += f"\nSchema: {schema[:200]}"

        glyph = Glyph(
            id=f"MCP_{tool_name}".upper()[:20],
            layer=1,
            dense=dense[:500],
            sources=[f"mcp://{server_name}/{tool_name}"],
            weight=1.5,
        )
        codebook.add_glyph(glyph)

    codebook.exchanges += 1
    return codebook


def eat_mcp_live(
    server_name: str,
    server_config: dict,
    codebook: Codebook,
) -> Codebook:
    """Eat a RUNNING MCP server's tools by spawning it and listing tools.

    For stdio servers: spawn the process, send initialize + tools/list,
    read the response, kill the process. Real tool discovery.
    """
    import subprocess
    import threading

    command = server_config.get("command", "")
    args = server_config.get("args", [])
    env_overrides = server_config.get("env", {})

    if not command:
        print(f"  [{server_name}] No command, skipping live discovery")
        return codebook

    # Build environment
    import os
    env = os.environ.copy()
    env.update(env_overrides)

    try:
        proc = subprocess.Popen(
            [command] + args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )

        # Send initialize
        init_req = json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "linafish", "version": "0.1.0"},
            },
        }) + "\n"

        # Send tools/list
        list_req = json.dumps({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {},
        }) + "\n"

        proc.stdin.write(init_req.encode())
        proc.stdin.write(list_req.encode())
        proc.stdin.flush()

        # Read responses with timeout
        tools_found = []

        def read_output():
            for line in proc.stdout:
                line = line.decode().strip()
                if not line:
                    continue
                try:
                    resp = json.loads(line)
                    if resp.get("id") == 2:  # tools/list response
                        tools = resp.get("result", {}).get("tools", [])
                        tools_found.extend(tools)
                except json.JSONDecodeError:
                    continue

        reader = threading.Thread(target=read_output, daemon=True)
        reader.start()
        reader.join(timeout=10)

        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

        if tools_found:
            print(f"  [{server_name}] Discovered {len(tools_found)} tools live")
            for tool in tools_found:
                tool_name = tool.get("name", "unknown")
                description = tool.get("description", "")[:300]
                schema = json.dumps(
                    tool.get("inputSchema", {}), indent=2
                )[:200]

                dense = f"{tool_name}: {description}"
                if schema and schema != "{}":
                    dense += f"\nParams: {schema}"

                glyph = Glyph(
                    id=f"MCP_{tool_name}".upper().replace("-", "_")[:20],
                    layer=1,
                    dense=dense[:500],
                    sources=[f"mcp://{server_name}/{tool_name}"],
                    weight=2.0,  # live-discovered tools are higher confidence
                )
                codebook.add_glyph(glyph)

            codebook.exchanges += 1
        else:
            print(f"  [{server_name}] No tools discovered (timeout or error)")

    except Exception as e:
        print(f"  [{server_name}] Live discovery failed: {e}")

    return codebook
