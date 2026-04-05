# Configuration Reference

## MCP Server Setup

### Minimal (start empty, feed via tool)

```json
{
  "mcpServers": {
    "linafish": {
      "command": "linafish",
      "args": ["serve"]
    }
  }
}
```

The fish starts empty. Use `fish_eat` to feed it during sessions. State saves to `~/.linafish/linafish.state.json`.

### Auto-Feed (recommended)

```json
{
  "mcpServers": {
    "linafish": {
      "command": "linafish",
      "args": ["serve", "--feed", "./my-docs"]
    }
  }
}
```

On first run, the fish eats everything in `./my-docs`. On subsequent runs, it loads from saved state (skips re-ingest). Feed more via `fish_eat` during sessions.

### Named Fish

```json
{
  "mcpServers": {
    "linafish": {
      "command": "linafish",
      "args": ["serve", "--feed", "./my-docs", "-n", "my-project"]
    }
  }
}
```

State saves to `~/.linafish/my-project.state.json`. Use different names for different projects.

### Custom State Directory

```json
{
  "mcpServers": {
    "linafish": {
      "command": "linafish",
      "args": ["serve", "--feed", "./docs", "--state-dir", "./.linafish"]
    }
  }
}
```

State saves in the project directory instead of home. Useful for per-project fish that travel with the repo.

### Domain Vocabulary

```json
{
  "mcpServers": {
    "linafish": {
      "command": "linafish",
      "args": ["serve", "--feed", "./docs", "--vocab", "./domain.json"]
    }
  }
}
```

Extends the 8-dimension keyword vocabulary with domain-specific terms. See `docs/how-it-works.md` for the vocabulary format.

## CLI Reference

### `linafish eat <path>`

Ingest files and produce a `.fish.md` codebook.

| Flag | Description |
|------|-------------|
| `-n, --name` | Fish name (default: directory/file stem) |
| `-d, --description` | Fish description |
| `-o, --output` | Output path (default: `{name}.fish.md`) |
| `--hint` | Context hint for better vectorization |
| `--vocab` | Path to domain vocabulary JSON |

### `linafish serve`

Start the MCP server (stdio transport).

| Flag | Description |
|------|-------------|
| `--feed` | Directory or file to ingest on startup |
| `--state-dir` | State directory (default: `~/.linafish/`) |
| `-n, --name` | Fish name (default: `linafish`) |
| `--vocab` | Path to domain vocabulary JSON |

### `linafish taste <fish.md>`

Print the contents of a fish codebook.

### `linafish status <fish.md>`

Show fish stats (size, formation count).

### `linafish demo <path>`

End-to-end demo: eat, show, optionally test with Gemini.

| Flag | Description |
|------|-------------|
| `-q, --question` | Question to test with Gemini |
| `-n, --name` | Fish name |
| `--hint` | Context hint |
| `--api-key` | Gemini API key |
| `--model` | Gemini model (default: gemini-2.5-flash) |

### `linafish room`

Listen to MQTT federation room and eat every exchange.

| Flag | Description |
|------|-------------|
| `--broker` | MQTT broker (default: localhost) |
| `--port` | MQTT port (default: 1883) |
| `-n, --name` | Fish name (default: room) |
| `--state-dir` | State directory |
| `--vocab` | Domain vocabulary JSON |

## MCP Tools

### `fish_pfc`

Returns the metacognitive overlay. Call at session start for a warm boot. Returns formations with their cognitive dimensions, crystal counts, and representative text.

**No parameters.**

### `fish_eat`

Feed new content to the fish.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `text` | string | yes | The text to feed |
| `source` | string | no | Label (default: "session") |

Returns: crystals added, total crystals, formation count.

### `fish_taste`

Cross-corpus matching. What does the fish know about this?

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `text` | string | yes | What to search for |
| `top` | integer | no | Number of results (default: 5) |

Returns: matching crystals ranked by gamma (cognitive similarity).

### `fish_match`

Tight recall. Higher threshold than taste.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `text` | string | yes | Text to match |
| `top` | integer | no | Number of results (default: 3) |

Returns: only strong matches (gamma > 0.4).

### `fish_health`

Engine stats.

**No parameters.**

Returns: crystal count, formation count, docs ingested, state file path, top formation names.

## File Locations

| File | Purpose |
|------|---------|
| `~/.linafish/{name}.state.json` | Persisted crystal state |
| `{name}.fish.md` | Human-readable codebook (from `eat` command) |
| `domain.json` | Domain vocabulary extension |

## Supported File Types

The ingest layer reads:
- `.md` — Markdown (chunked by headers)
- `.txt` — Plain text (chunked by paragraphs)
- `.pdf` — PDF (requires `pip install linafish[pdf]`)
- `.docx` — Word documents (requires `pip install linafish[docx]`)
- `.json` — JSON (stringified values)
- `.py` — Python source (chunked by functions/classes)
