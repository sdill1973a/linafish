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

### Existing Fish (built with `linafish go`)

```json
{
  "mcpServers": {
    "linafish": {
      "command": "linafish",
      "args": ["serve", "-n", "my-writing"]
    }
  }
}
```

`linafish go ~/my-writing` makes a fish named after the folder, `my-writing`. Pass that name with `-n` and leave out `--feed`; the server loads the fish as it is. Without `-n`, `serve` uses a fish named `linafish`.

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

Fish that share a state directory share one vectorizer (`mi_vectorizer.json` at the root of that directory), so feeding one fish changes the vectorizer the others use. Give unrelated fish separate state directories.

### Domain Vocabulary (`--vocab`) — no effect

`serve`, `http`, `eat` and `room` still accept `--vocab <file.json>` so that old scripts and configs keep working, but it does nothing: the current engine learns its vocabulary from your writing and never reads the file. `eat` and `room` print a warning when you pass it; `serve` and `http` ignore it silently. To make terms you care about always get a vocabulary axis, use [`LINAFISH_PROTECTED_VOCAB`](#environment-variables) instead.

## CLI Reference

### `linafish eat <path>`

Ingest a file or directory into a fish and write its `.fish.md` codebook.

| Flag | Description |
|------|-------------|
| `-n, --name` | Fish name. Without it: if exactly one fish lives in the state directory, `eat` feeds it and says so; if several do, it refuses and lists them; if none do, it creates a fish named after the file or directory stem. |
| `--state-dir` | Where the fish lives (default: `~/.linafish/`). Write the path unquoted or absolute: this flag does not expand a quoted `"~/…"`. |
| `-d, --description` | Replaces the title line of the written codebook |
| `-o, --output` | Also write the codebook here. Default: without `--state-dir`, a copy is written to `./{name}.fish.md` in the current directory; with `--state-dir`, nothing is written outside the state directory. |
| `--hint` | No effect. Accepted for old scripts; prints a warning. |
| `--vocab` | No effect. Accepted for old scripts; prints a warning. |

`eat` does not skip text the fish already holds: eating the same file twice stores it twice.

### `linafish go [folder]`

Build a fish from a folder (default: the current directory) and print its portrait.

| Flag | Description |
|------|-------------|
| `-n, --name` | Fish name (default: the folder's name) |
| `--state-dir` | Where to store the fish (default: `~/.linafish/`) |
| `--no-serve` | Stop after building. Without it, `go` serves the fish over HTTP and keeps running until Ctrl+C. |
| `-p, --port` | Port for that server (default: a random free port) |

Re-running `go` on the same folder does not re-eat files it has already read.

### `linafish serve`

Start the MCP server (stdio transport).

| Flag | Description |
|------|-------------|
| `--feed` | Directory or file to ingest on startup. Leave it out to serve an existing fish as it is. |
| `--state-dir` | State directory (default: `~/.linafish/`) |
| `-n, --name` | Fish name (default: `linafish`). Use the name `go` gave your fish. |
| `--vocab` | No effect (see [Domain Vocabulary](#domain-vocabulary---vocab--no-effect)) |

### `linafish http`

Serve a fish over HTTP for any AI or tool that can fetch a URL. Runs until Ctrl+C.

| Flag | Description |
|------|-------------|
| `-n, --name` | Fish name (default: `linafish`). To serve the fish `go` built from `~/my-writing`, use `-n my-writing`. |
| `--feed` | Directory or file to ingest on startup. Leave it out to serve an existing fish as it is. |
| `--state-dir` | State directory (default: `~/.linafish/`) |
| `-p, --port` | Port (default: 8900) |
| `--bind` | `local` (default, loopback only), `lan` or `wan` (both bind `0.0.0.0`) |
| `--vocab` | No effect |

`GET /pfc` returns the portrait as markdown; `POST /taste` with `{"text": "...", "top": 5}` is a meaning search. The full endpoint list is in [AGENTS.md](../AGENTS.md#endpoints-quick-reference).

### `linafish converse`

The multi-fish, federation-oriented HTTP server (default port 8901).

| Flag | Description |
|------|-------------|
| `-n, --name` | Fish name (default: `linafish`) |
| `--state-dir` | State directory |
| `-p, --port` | Port (default: 8901) |
| `--bind` | `local` (default), `lan` or `wan` |
| `--token` | Auth token for `lan`/`wan` access |
| `--mind` | This mind's display name (default: hostname) |
| `--dedupe` | `POST /eat` refuses a byte-exact repeat of a text the fish already holds; the reply is `crystals_added: 0` with reason `duplicate`. Off by default. |

### `linafish school eat <text-or-file>`

Feed every member of a school at once.

| Flag | Description |
|------|-------------|
| `--state-dir` | School state directory (default: `~/.linafish/school/`) |
| `--central-dir` | Central fish state directory (default: `~/.linafish/`) |
| `--source` | Source label for the eaten text (default: `session`) |
| `--dedupe` | Every member refuses a byte-exact repeat of a text it already holds. Off by default. |

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
| `--hint` | No effect. Accepted for old scripts; prints a warning. |
| `--api-key` | Gemini API key |
| `--model` | Gemini model (default: gemini-2.5-flash) |

### `linafish room`

Listen to MQTT federation room and eat every exchange.

| Flag | Description |
|------|-------------|
| `--broker` | MQTT broker host (default: localhost) |
| `--port` | MQTT port (default: 1883) |
| `-n, --name` | Fish name (default: room) |
| `--state-dir` | State directory (default: the current directory, not `~/.linafish/`) |
| `--vocab` | No effect; prints a warning |

Broker credentials come from `LINAFISH_MQTT_USER` and `LINAFISH_MQTT_PASS`. The broker host and port come only from `--broker` and `--port`.

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
| `LINAFISH_HABITUATION` | `off` | Opt in with `on`: the fish writes in proportion to surprise on every ingest path except deliberate deposits (`eat FILE`, `go`, `eat(..., admit=False)` from Python): a message its source's stream predicts is refused with `reason: "habituated"` and counted, not crystallized. Off by default — the design's store rule is "everything enters, ache sorts"; refusing at the door is a departure a node chooses until post-entry decay is wired. |
| `LINAFISH_HABITUATION_FLOOR` | `0.05` | Surprise below this is refused. Measured default: refused 89% of a real repetitive stream and 0% of real prose. Raise to refuse more, lower to refuse less. |
| `LINAFISH_SKIP_PREFIXES` | `T^keeper\|,T^boot\|` | Comma-separated; the trailing pipe is part of each prefix. A message starting with any of these is a heartbeat and is never crystallized. |
| `LINAFISH_SKIP_MARKERS` | `heartbeat,reason=session_keeper` | Comma-separated, case-insensitive. A message whose first line contains any of these is a heartbeat and is never crystallized. |
| `LINAFISH_SKIP_MARKER_WINDOW` | `64` | How many characters of the first line the marker scan reads. Measured default: on 2,299 real paragraphs, 64 refused none; every heartbeat fixture declares itself within the first ~10. |
| `LINAFISH_MAX_CRYSTALS` | unset (no ceiling) | A fish at this many crystals refuses further eats with `reason: "ceiling"` instead of growing. Every crystal is resident in memory (~90 KB each); set this on a machine that has been running out of memory. A ceiling is a stop, not a cleaner: the fish holds at N, it does not prune itself (post-entry decay is not yet in the package). |
| `LINAFISH_NO_HEAT` | unset | `1`/`true`: the engine is an ambient reader — it never writes on its own. |
| `LINAFISH_EXPOSE_FULL_SOURCES` | unset | `1`/`true`: the converse server's `/moment/<episode_id>` returns untruncated episode source. Off by default because it is the highest-fidelity surface the fish has. |
| `LINAFISH_MAX_PAIR_COUNTS` | engine default | Cap on the co-occurrence pair table. Truncation is reported at save, never silent. |
| `LINAFISH_MESSAGES_FILE` | `<state_dir>/messages.jsonl` | Override the HTTP server's messages file path (absolute path). |
| `LINAFISH_MQTT_USER` / `_PASS` | unset | Broker credentials for `room` and for the guppy's publish. |
| `LINAFISH_MQTT_HOST` / `_PORT` | unset / `1883` | Broker for the guppy's publish only. `room` takes its broker from `--broker` / `--port`. `listen mqtt://…` reads none of these: it takes host, port and optional `user:pass@` from its URL. |
| `LINAFISH_HUNT_INTERVAL` | `300` | Seconds between guppy hunts, as read by the guppy module (`python -m linafish.guppy`). `linafish hunt <name> --swim` uses its own `--interval` flag (default 300). |
| `LINAFISH_FAISS_URL` / `_ROOM_URL` / `_BERT_URL` | unset | External endpoints the guppy hunts against. Unset disables that leg. |
| `LINAFISH_LLM_URL` / `_KEY` / `_MODEL` / `_FORMAT` | unset | The optional model behind `meditate --descend` and the crucible. Unset keeps the fish inference-free. |
| `LINAFISH_PROTECTED_VOCAB` | unset (`off`) | Terms that are always given a vocabulary axis. Unset or `off`: no reserved axes (the default). `on`: the package's built-in identity set. Anything else is read as a comma-separated list of your own terms, e.g. `maria,river,garden` (case-insensitive). A protected term that occurs at least once in your writing is reserved an axis; a term that never occurs is never invented. Reserved axes are capped at half the vocabulary. The variable is read each time the vocabulary is chosen, so set it before `go`/`eat` builds the fish (or before a later `revectorize`). |

Not a setting, always on: **a retained MQTT delivery is refused, on `listen` and on `room`.** A
broker answers every new subscription with the last retained value of each topic, and both
verbs subscribe on every (re)connect — so without this, every restart re-ate the same state
messages as new crystals. The listener counts these as `retained` in its refusal summary; the
room daemon counts them as skips. Nothing about your broker session (`clean_session`) changes.

## File Locations

| File | Purpose |
|------|---------|
| `~/.linafish/{name}_v3_state.json` | Persisted engine state |
| `~/.linafish/{name}_crystals.jsonl` | Crystal log (one crystal per line) |
| `~/.linafish/{name}.fish.md` | Human-readable codebook |
| `./{name}.fish.md` | Copy of the codebook that `eat` writes to the current directory when run without `--state-dir` |
| `~/.linafish/mi_vectorizer.json` | The vectorizer, shared by every fish in that state directory |
| `~/.linafish/.git` | The fish's history (`linafish history -n {name}`) |

With `--state-dir <dir>`, replace `~/.linafish/` with `<dir>`.

## Supported File Types

The ingest layer reads:
- `.md` — Markdown (chunked by headers)
- `.txt` — Plain text (chunked by paragraphs)
- `.pdf` — PDF (requires `pip install "linafish[pdf]"`)
- `.docx` — Word documents (requires `pip install "linafish[docx]"`)
- `.json` — JSON (stringified values)
- `.py` — Python source (chunked by functions/classes)
