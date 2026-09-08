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

The fish starts empty. Use `fish_eat` to feed it during sessions. State saves to `~/.linafish/linafish_v3_state.json` (plus `linafish_crystals.jsonl` and `linafish.fish.md`).

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

State saves to `~/.linafish/my-project_v3_state.json` (plus `my-project_crystals.jsonl` and `my-project.fish.md`). Use different names for different projects.

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

## Environment variables

Every setting the package reads from the environment. Unset means the default.

| variable | default | what it does |
|---|---|---|
| `LINAFISH_HABITUATION` | `on` | The listener (`linafish listen`, `linafish room`) writes in proportion to surprise: a message its source's stream predicts is refused and counted, not crystallized. `off` writes everything. |
| `LINAFISH_HABITUATION_FLOOR` | `0.05` | Surprise below this is refused. Measured default: refused 89% of a real repetitive stream and 0% of real prose. Raise to refuse more, lower to refuse less. |
| `LINAFISH_SKIP_PREFIXES` | `T^keeper\|,T^boot\|` | Comma-separated. A message starting with any of these is a heartbeat and is never crystallized. |
| `LINAFISH_SKIP_MARKERS` | `heartbeat,reason=session_keeper` | Comma-separated, case-insensitive. A message containing any of these is a heartbeat and is never crystallized. |
| `LINAFISH_MAX_CRYSTALS` | unset (no ceiling) | A fish at this many crystals refuses further eats with `reason: "ceiling"` instead of growing. Every crystal is resident in memory (~90 KB each); set this on a machine that has been running out of memory. |
| `LINAFISH_NO_HEAT` | unset | `1`/`true`: the engine is an ambient reader — it never writes on its own. |
| `LINAFISH_EXPOSE_FULL_SOURCES` | unset | `1`/`true`: the converse server's `/moment/<episode_id>` returns untruncated episode source. Off by default because it is the highest-fidelity surface the fish has. |
| `LINAFISH_MAX_PAIR_COUNTS` | engine default | Cap on the co-occurrence pair table. Truncation is reported at save, never silent. |
| `LINAFISH_MESSAGES_FILE` | per-fish default | Override the HTTP server's messages file path. |
| `LINAFISH_MQTT_HOST` / `_PORT` / `_USER` / `_PASS` | unset / `1883` / unset / unset | Broker for the guppy's publish and for authenticated `listen mqtt://` / `room`. Credentials come from the environment, never from the command line. |
| `LINAFISH_HUNT_INTERVAL` | `300` | Seconds between guppy hunts in `linafish guppy --swim`. |
| `LINAFISH_FAISS_URL` / `_ROOM_URL` / `_BERT_URL` | unset | External endpoints the guppy hunts against. Unset disables that leg. |
| `LINAFISH_LLM_URL` / `_KEY` / `_MODEL` / `_FORMAT` | unset | The optional model behind `meditate --deep` and the crucible. Unset keeps the fish inference-free. |

## File Locations

| File | Purpose |
|------|---------|
| `~/.linafish/{name}_v3_state.json` | Persisted engine state |
| `~/.linafish/{name}_crystals.jsonl` | Crystal log (one crystal per line) |
| `{name}.fish.md` | Human-readable codebook |
| `domain.json` | Domain vocabulary extension |

## Supported File Types

The ingest layer reads:
- `.md` — Markdown (chunked by headers)
- `.txt` — Plain text (chunked by paragraphs)
- `.pdf` — PDF (requires `pip install linafish[pdf]`)
- `.docx` — Word documents (requires `pip install linafish[docx]`)
- `.json` — JSON (stringified values)
- `.py` — Python source (chunked by functions/classes)
