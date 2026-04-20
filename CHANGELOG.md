# Changelog

All notable changes to linafish are recorded here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

This package is dedicated to [Caroline Marie
Dill](https://github.com/sdill1973a/linafish#what-this-is).

---

## [1.1.7] — 2026-04-20

**Patch release. Two real Windows-reproduced bugs caught by running the
full fleet on .140 — `linafish diff` crashing on non-ASCII fish content,
and converse servers silently stalling under concurrent client load.**

### Fixed

- **`_git_run` no longer crashes on non-ASCII git output on Windows
  (#2).** Windows default encoding is cp1252, which raises
  `UnicodeDecodeError` on any git diff output containing crystal text
  outside that codepage — which is effectively every modern fish.
  Forced `encoding="utf-8", errors="replace"` in the `subprocess.run`
  call, and guarded against `None` stdout/stderr to prevent a
  secondary `AttributeError: 'NoneType' object has no attribute
  'strip'`. `linafish diff --name <fish>` is now usable again on
  Windows.

- **HTTP servers switched to `ThreadingHTTPServer` (#9).** Single-
  threaded `HTTPServer` blocks on the active handler while later
  connections queue in the listen backlog. Under real load — per-turn
  hooks, agent-dispatched reads, MCP pollers — one slow handler
  silently stalls all subsequent GETs. The server stays LISTENING but
  `curl` returns empty. Applied to all three HTTP entry points:
  `converse.py`, `http_server.py`, `quickstart.py`. Drop-in stdlib
  replacement, same API.

### Added

- **Regression tests for both fixes.** `tests/test_git_run_encoding.py`
  creates a real git repo with non-ASCII fish content and verifies
  `_git_run("diff")` returns cleanly. `tests/test_http_threaded.py`
  fires 5 concurrent 300ms-handler requests and asserts total elapsed
  is well under the serial floor — proves actual threading, not just
  import — plus a parametrized static guard that each of the three
  HTTP entry points references `ThreadingHTTPServer`.

---

## [1.1.6.1] — 2026-04-17

**Patch release. Fixes a `datetime` import regression in
`cmd_doctor` caught by THX on .147 in the first hour after 1.1.6
shipped.**

### Fixed

- **`linafish doctor --name <fish>` no longer crashes with
  `NameError: name 'datetime' is not defined`.** The fish-health
  section in `cmd_doctor` uses `datetime.fromtimestamp(...)` to
  format the crystal file mtime; the import was never added to
  `__main__.py` when the doctor refactor landed. `linafish doctor`
  without `--name` was unaffected. Added `from datetime import
  datetime` at the module import block.

---

## [1.1.6] — 2026-04-17

**Persistence-safety release + v1 sunset. One engine, one cognition,
one persistence layer. The full 20-item plate landed plus THX's
usability patches and a modes-assessment that tells the user/AI
which legs of the system are actually live.**

### Added

- **`FishEngine(git_autocommit: bool = True)`** — new constructor
  keyword. When `True` (the default, preserving 1.1.5 behavior), every
  `_save_state()` commits the fish repo as before. When `False`, the
  per-save commit is skipped entirely. Batch consumers should pass
  `git_autocommit=False` and drive a single commit after their full
  batch completes. Measured on 25 sequential `eat()` calls: 3306 ms
  with autocommit on vs 128 ms with autocommit off — the per-save
  `git commit` was the dominant cost on the hot path, not the
  crystallization work.

### Fixed

- **`FishEngine._load_fish_md()`: restore `docs_ingested` on reload.**
  The save path had always been writing `docs_ingested` into the
  `FISH_STATE` JSON block at the bottom of `fish.md`, but the load
  path only rebuilt formations and ignored the metadata block. Every
  boot was silently resetting the counter to zero, so display strings
  like `N crystals from M documents` were dropping M across sessions
  and R(n) computation lost its document-count denominator. Parser
  handles malformed / non-object / corrupt payloads as best-effort;
  corrupt state files are not fatal to boot.

- **`MIVectorizer.load()` and `UniversalFish._load_state()`: graceful
  recovery on corrupt state files.** Both sites were calling
  `json.load()` with no exception handling, so a single corrupt byte
  in `mi_vectorizer.json` or `*_v3_state.json` raised through the
  whole `FishEngine` constructor and aborted init. Both sites now
  catch `(OSError, json.JSONDecodeError, UnicodeDecodeError)`, guard
  with `isinstance(dict)` before any `.get()` calls, log at warning
  level, and fall through to the already-initialized defaults.
  Recovery is automatic — the next `_save_state` rewrites clean
  files. Handles missing files, truncated JSON, malformed JSON,
  non-object JSON payloads, and invalid-UTF-8 byte sequences.

- **`listener.py` / `guppy.py`: docstring scrubs.** Removed a
  private-host octet from `FishListener.listen_mqtt()` and an
  internal session-tag reference from `guppy.py` module docstring.
  No behavior change — package source is cleaner for stranger
  readers.

- **`http_server.serve_http()` gains `--bind` CLI + `bind=` parameter.**
  The earlier plate-15 fix at 752ccaa restored the missing `host`
  parameter to unblock startup, but the CLI still had no way to
  request LAN binding — an asymmetry with `linafish converse
  --bind lan|wan`. Ports the bindmap convention across both
  servers so `linafish http --bind lan` works the same as
  `linafish converse --bind lan`. Explicit `host=` still wins
  when set, so any plate-15-era caller that passed
  `host="0.0.0.0"` keeps working unchanged.

### Changed

- **`FishEngine.rebuild_formations()` is now public.** The method was
  previously named `_rebuild_formations` and called from `fusion.py`,
  `quickstart.py`, and extension code through the private name. The
  public name is the canonical entry point; `_rebuild_formations`
  remains as a class-level alias for backward compatibility.

- **Level 4 formation memory wire-in landed in
  `rebuild_formations()`.** The metabolic engine's
  `teach_from_formations()` now fires on every rebuild, not only
  from `quickstart.go()`. Incremental `eat()` / `eat_path()` /
  `re_eat()` / load paths all populate formation memory consistently
  now.

- **`RoomListener` (the `linafish room` command) rewritten on top
  of `FishEngine`.** Previously maintained its own crystal list and
  called the v1 `batch_ingest` / `couple_crystals` /
  `extend_vocabulary` API directly. Now drives a single `FishEngine`
  instance with `git_autocommit=False` (per-message git commits
  would be pointless churn on the hot path). On first startup, if
  the state_dir contains a legacy `{fish_name}.crystals.json` (v1
  format) and the engine has no crystals loaded, content is re-fed
  via `FishEngine.eat()` and the legacy files are renamed with a
  `.legacy` suffix for audit. The `--vocab` CLI flag is preserved
  but becomes a no-op (MIVectorizer learns its own vocabulary under
  v3) and prints a warning instead of failing.

- **FishEngine `taste()` output includes crystal source + ts inline.**
  Each result line now formats as
  `[score] src=<source> | ts=<iso> | keywords` instead of the bare
  `[score] keywords`. Backward compatible with consumers that only
  parse the `[score]` prefix. Enables downstream filtering by source
  prefix / crystal age without a second round-trip.

- **`linafish introduce --live` — new flag, dynamic server probe.**
  Defaults unchanged: `linafish introduce` still prints the static
  AGENTS.md. With `--live`, probes 127.0.0.1:{8900,8901,8902},
  identifies each responding server as converse or HTTP based on
  its `/` response, and emits a briefing keyed to what's actually
  running instead of the static doc that mixes routes from both
  server types. Addresses THX's observation that an AI landing
  cold and reading `linafish introduce` gets `/minds` and
  `/crystals` documented even when it's talking to the HTTP server
  where those routes don't exist.

- **`linafish --version`** — new root-level argparse flag.
  Previously users had to run `linafish doctor` or
  `python -c "import linafish; print(linafish.__version__)"` to
  check their install.

- **`linafish room --help` documents MQTT env vars.** Help text
  now names `LINAFISH_MQTT_USER` / `LINAFISH_MQTT_PASS` up front
  with the fallback behavior (anonymous connect succeeds on open
  brokers, fails with CONNACK rc=5 on authenticated ones — and
  the daemon rewrite now surfaces the rejection instead of
  sitting silent). Previously a user on an authenticated broker
  had to read source to find the env var names.

- **"Modes available" assessment in `doctor` and
  `introduce --live`.** Both commands now include a section
  showing which of four modes are live and what unlocks the
  missing ones:
    - *solo* — fish.md exists
    - *ai_facing* — HTTP or converse server responding on
      8900/8901/8902
    - *growing* — crystals written within the last hour
    - *federation* — MQTT creds + converse server up
  Each mode reports *ready* / *partial* / *missing* with concrete
  evidence and the specific command or env-var change that would
  shift *missing* to *ready*. Same assessment powers both views
  so the human at the shell and the AI reading the briefing see
  the same picture. Addresses the gap where a cold `doctor`
  output listed daemons but never said what the system was
  actually ready to DO.

### Known limitations

- **Multiple `FishEngine` instances on the same `state_dir` + `name`
  in the same Python process share state loosely.** Plate 11 locks
  across *processes*, not across in-process instances. Two
  concurrent engines will not crash and will not corrupt the
  crystal JSONL, but the last saver wins on `v3_state.json` and
  counters can skew (observed: 4 eats across two engines → reload
  saw 3 crystals / 2 docs). The workaround is to keep one engine
  instance per `(state_dir, name)` pair. A proper in-process cache
  or engine-level mutex is slated for a later release.

### Removed

- **v1 crystallizer modules deleted: `linafish/codebook.py`,
  `linafish/compress.py`, `linafish/eat.py`,
  `linafish/crystallizer.py`** (1307 lines). These were internal
  modules; no public API changes. Before delete: a full grep of the
  linafish package for `from .(codebook|compress|eat|crystallizer)`
  returned zero matches outside the v1 modules themselves. Only
  `tests/archive/test_codebook_v1.py` still references them (archive
  dir, already excluded from pytest collection). The fork sunset is
  complete — one engine, one cognition, one persistence layer.

- **`FishDaemon` class removed from `linafish/daemon.py`.** Defined
  but never instantiated anywhere in the package. Dead code.

---

## [1.1.5] — 2026-04-13

**Correctness release. Upgrade recommended for anyone running `linafish
emerge`, building a fish on Windows, or relying on per-crystal cognitive
parse data (`chains`, `modifiers`, `cognitive_vector`). No features, no
API changes, no schema changes — only fixes.**

### Fixed

- **`crystallizer_v3._load_state()`: load-path amputation of six crystal
  fields.** `_load_state()` was constructing `Crystal(...)` from the
  JSONL log with only 9 of the dataclass's 15 fields, letting defaults
  (empty list / empty dict / `None`) fill in the other six: `chains`,
  `modifiers`, `cognitive_vector`, `ache`, `formation`, and
  `wrapping_numbers`. Every save wrote the full crystal via
  `dataclasses.asdict()`, so the data was reaching disk correctly. Only
  the loader was stripping it. Symptom: every reloaded crystal had an
  empty cognitive parse layer, `linafish emerge` reported zero
  novelty/zero phase on every formation, and fish that had the data
  populated on disk appeared dormant in every tool that loaded them
  through `FishEngine`. The JSONL files have had the data the whole
  time. Load path now round-trips all six fields explicitly, with
  `chains` re-tupleified because JSON drops tuple type on serialize.

  Existing fish come alive on the first reload after upgrading — no
  re-eat or migration required. On our test corpus a 6,360-crystal
  fish went from 0 populated `cognitive_vector` / 0 `chains` / 0
  `modifiers` to 6,359 / 4,280 / 4,046 respectively on a single
  reload. `linafish emerge` went from an empty-state diagnostic to 23
  formations reporting Phase 1 "Semantic Novelty" with ν=1.000.

  This is the biggest single fix in the 1.1.x line. Recommended upgrade
  for anyone who ever ran `linafish emerge` and got zeros, or who ever
  noticed their fish's cognitive dimensions looked flat after a restart.

- **Path-argument tilde expansion on Windows.** The CLI's path-shaped
  arguments (`--state-dir`, `--feed`, `--vocab`, `--output`, `--manifest`,
  `--central-dir`, and every positional `source` / `fish` that refers to
  a local path) did not call `Path.expanduser()` before resolving. On
  Unix shells (bash, zsh) this was invisible because the shell expanded
  `~` before Python saw it. On Windows `cmd.exe` and PowerShell, the
  shell passes `~` through literally and Python's `Path("~/...")`
  resolves it to a literal `~` subdirectory in the current working
  directory. The README's own `linafish go ~/my-writing` example failed
  for any stranger running it on a fresh Windows install.

  Fixed at the argparse layer rather than per-command: a new
  `_user_path` type function is now applied to every pure-path
  `add_argument`, so expansion happens at parse time and no `cmd_*`
  body can forget. Mixed-scheme positionals (`absorb source`,
  `listen source`), which also accept `http://`, `mqtt://`, and
  `folder:` prefixes, are intentionally left untyped because their
  parser already handles the scheme split internally.

- **`linafish emerge` silent-zero failure mode.** `compute_emergence`
  was written for the v0.3 metabolism-engine crystal type and iterated
  `crystal.top_operations` directly, which the v3 `Crystal` dataclass
  does not have as an attribute. Prior to the load-path fix above this
  showed up as an `AttributeError` crash on every real fish; after the
  load-path fix it would have silently produced zero metrics on any
  formation whose crystals had empty parser output. `compute_emergence`
  now uses a type-tolerant shim (`_crystal_ops`) that handles
  `MetabolicCrystal` via `top_operations`, v3 `Crystal` via tuple/list
  `chains` and dict `modifiers`, and a legacy string-chain fallback.
  `cmd_emerge` also prints an honest "no cognitive operation data"
  diagnostic if a fish genuinely has empty parser output (e.g., a fresh
  fish with zero eats), rather than printing misleading zeros.

- **`linafish capabilities` stale docs list.** The command printed a
  hardcoded list of docs that included three files (`ai-usability.md`,
  `ideas/gpt-backed-linafish.md`, `v12-seeds.md`) that were removed from
  the tree in 1.1.3. List now reflects the docs that actually ship:
  `README.md`, `AGENTS.md`, `CHANGELOG.md`, and the user-facing files
  under `docs/` (architecture, how-it-works, vision, owners-manual,
  configuration, privacy, research, testing, worked-example).

### Added

- **README Install section: "If `linafish` isn't found after install"
  subsection.** A first-time user on Windows who installed Python
  without the *"Add Python to PATH"* checkbox gets `pip install`
  success followed by *"command not found"* and no obvious next step.
  The new subsection gives three recovery paths: `python -m linafish`
  as the always-works fallback, Windows user-PATH recovery with the
  exact command to find the Scripts directory, and Unix/macOS
  `~/.local/bin` guidance for `pip install --user` cases. This is the
  single most-common stranger-install friction we have observed in the
  wild and the README now has a first-class answer for it.

- **`_user_path` argparse type helper** (`linafish/__main__.py`). See
  the tilde-expansion fix above. New code adding a path-shaped
  `add_argument` should pass `type=_user_path` and inherit the
  expansion behaviour automatically.

### Changed

- **README `Install` section: "Runs on anything" → "Runs on any OS
  with a supported Python (tested on Windows 10/11, macOS, and
  Linux)".** The old claim was marketing-vague and unfalsifiable; the
  new claim names the platforms actually tested.

- **README `Three Ways to Connect` section: "Copy-Paste (any AI, zero
  setup)" → "Copy-Paste (any AI, no server needed)".** `pip install`
  plus possible PATH setup is not zero setup; the new label is honest
  about what "no server" means.

- **README `What You'll See` block: "The fish teaches ANY AI how to
  read it. Paste it into ChatGPT, Claude, Gemini, Llama — anything
  with a text box"** was replaced with a scoped claim naming the three
  models we have actually verified the workflow against (Claude,
  ChatGPT, Gemini), with an explicit note that we cannot guarantee
  behavior on models we have not tested.

- **`docs/how-it-works.md` Domain Extension section: "The 8 dimensions
  work on any corpus"** was replaced with a claim that names the
  corpus types we have actually run formations across (personal
  journals, academic papers, novels, historical letters, source code).
  Same pattern as the other doc fixes: describe what we have done, not
  what the engine could theoretically do.

### Review process

This release was reviewed three times cold by an independent model
(codex CLI, GPT-o3) across three separate review passes. Round 1
surfaced one HIGH (the emerge type mismatch) and one MED (the
incomplete path-argument sweep). Round 2 verified those fixes and
found the branch clean with no new issues. Round 3 was scoped to the
load-path amputation commit and included a live round-trip test, a
direct count of fields populated on both test fish on disk, and an
end-to-end run of `linafish emerge me` — all passed. Merge was gated
on all three rounds being clean.

## [1.1.4] — 2026-04-13

**Critical fix — upgrade recommended for anyone running `linafish
converse` as a daemon.**

### Fixed

- **`converse.py`**: `BaseHTTPServer` propagated `ConnectionAbortedError` /
  `ConnectionResetError` / `BrokenPipeError` from `wfile.write(...)` out of
  the handler, and the server treated the unhandled exception as fatal and
  shut down. Any client that timed out mid-response (e.g. a hook with a
  short HTTP timeout) killed the whole daemon. The feed/taste work had
  already happened server-side — only the reply was lost — but the next
  inbound request found a dead socket. Now wrapped in try/except with
  a log-and-return. Observed ~19 catches firing in an hour of normal
  traffic on a parallel install before it was patched.
- **`__main__.py` + `listener.py`**: MQTT URL parser now accepts
  `mqtt://user:pass@host:port/topic` for authenticated brokers. Previously
  credentials had to be passed as separate flags.

1.1.1, 1.1.2, and 1.1.3 are yanked on PyPI. 1.1.4 is the first release
that is safe to run as a long-lived daemon under real traffic.

## [1.1.3] — 2026-04-13

Identical to 1.1.2 in functionality. 1.1.3 removes internal-narrative
comments and docstrings from the source tree that should not have
shipped publicly. No behavioral changes.

## [1.1.2] — 2026-04-13

> **Version note:** 1.1.1 was an unfinished cut pushed to PyPI from a
> branch that did not include the fixes below. PyPI is immutable, so
> 1.1.2 is the corrected release. If you are on 1.1.1, run
> `pip install --upgrade linafish` — you want this one.

### Summary

This release fixes a long-standing silent truncation bug in the
crystallizer, closes a set of stranger-install blockers surfaced by
first-time external users, and adds a small family of discoverability
commands (`linafish introduce`, `linafish doctor`, `linafish update`,
`linafish capabilities`) so a new installer can ask the package what
it is and how it is doing.

The release was reviewed twice cold — once by an independent model
via a CLI code-review tool, once by a fresh install in a clean venv
walking through every command as a new user would. Both passes found
issues; all HIGH-severity findings are closed here.

### Fixed

- **`crystallizer_v3`**: `text=text[:300]` was hardcoded in the
  `Crystal` constructor and silently capped every deposit at 300
  characters. New `MAX_CRYSTAL_TEXT = 32768` module constant.
  Existing fish are unaffected; new deposits go in at full length.
  Re-feeding from source is optional but recommended if you want the
  older stub crystals replaced.
- **`quickstart.py` (`linafish go`)**: was calling `doc.read_text()`
  directly and bypassing the `READERS` dispatch entirely, so the
  document-type tolerance was dead code for the flagship command.
  Now routes through a new `read_file_as_text()` helper in
  `ingest.py`. HTML strips tags, CSV parses as rows, YAML
  pretty-prints, PDF/DOCX/PPTX flow through their optional-dependency
  readers.
- **`ingest.py` `ingest_directory`**: default `strict=False` now
  accepts any file not on `BINARY_SKIP`. Previously only six
  whitelisted extensions were eaten, so a directory of HTML/CSV/YAML
  notes produced nothing. `BINARY_SKIP` expanded from 43 to 123
  extensions covering all common image/audio/video/archive/executable/
  database/font/backup types. A 5 MB fall-through size guard prevents
  the UTF-8 decoder from choking on an accidental binary.
- **`_mind_integration.py`**: removed a hardcoded absolute path that
  crashed on any machine other than the developer's. Replaced with a
  `LINAFISH_MIND_STATE` environment variable plus a
  `~/.linafish/mind_state` fallback.
- **`compress.py`**: unconditionally imported `requests` with no
  fallback and no declared dependency, so `linafish eat <file>`
  crashed with `ModuleNotFoundError` on a fresh install. Now guarded
  with `try/except` and falls back to the in-process extractive
  compressor.
- **`school.py`**: default manifest hardcoded a fish name that only
  existed on the developer's machine. Now derives the default from
  the state-directory basename at load time.
- **`http_server.py`**: only bound to `127.0.0.1` with no parameter
  for LAN/WAN sharing. Added a `host` parameter for parity with the
  `converse` server.
- **`tests/incremental_growth_test.py`**: was writing its report to a
  hardcoded absolute path that only existed on the developer's
  machine. Now uses `tempfile.gettempdir()`.
- **`tests/lab_results.json`**: personal-machine paths committed as
  sample output. Removed from git and added to `.gitignore`.

### Added

- **`AGENTS.md`** at repo root and bundled in the wheel as
  `linafish/data/AGENTS.md`. An AI-facing briefing with exact endpoint
  curl examples, the three things an AI can do with linafish, what
  NOT to do, the 8 cognitive dimensions, privacy scope, and how to
  behave as a good citizen in the read/write loop. Run
  `linafish introduce` to print it. A README is not enough when the
  primary readers of this package on behalf of a human will be AI
  assistants — those assistants need a briefing they can parse in
  one read.
- **`linafish introduce`**: prints `AGENTS.md`. Lookup via
  `importlib.resources` so it works in both wheel and editable installs.
- **`linafish doctor`**: one-page health check. Python version,
  linafish version, install mode (editable vs wheel), optional
  dependency status, live daemon probes on default ports, optional
  per-fish health check, optional PyPI version check, suggested next
  commands. Read-only, safe anywhere.
- **`linafish update`**: one-command upgrade. Refuses to run `pip`
  on editable installs (with a `git pull` hint) unless `--force-pip`
  is given. Streams pip's stdout/stderr live so slow upgrades show
  progress. `--all` upgrades optional extras, `--pre` includes
  prereleases.
- **`linafish capabilities`**: prints the full module and command
  map with optional-dependency status. Answers "what does this
  package actually do" in one command. Lists all 32 modules grouped
  by layer and all 27 CLI commands.
- **`linafish hunt` / `emerge` / `feedback`**: three previously
  orphaned modules (`guppy`, `emergence`, `feedback`) now have
  first-class CLI entry points. `hunt` runs a guppy ache-hunt cycle
  to find gaps. `emerge` measures Semantic Novelty Threshold metrics
  on a fish's formations. `feedback` shows the usage-weighted
  learning report.
- **`ingest.py`** new readers: `read_html`, `read_csv`, `read_tsv`,
  `read_jsonl`, `read_ndjson`, `read_yaml`, `read_pptx`, `read_rtf`,
  `read_xml`. `READERS` dispatch went from 6 extensions to 39.
  Writing formats (`.rst`, `.tex`, `.org`), config formats (`.toml`,
  `.ini`, `.cfg`, `.conf`, `.env`), and source types (`.js`, `.ts`,
  `.go`, `.rs`, `.java`, `.kt`, `.rb`, `.php`, `.sh`) all fall
  through cleanly.
- **`pyproject.toml`** optional dependencies: `pptx` (python-pptx),
  `rtf` (striprtf), `yaml` (PyYAML). Each behind its own extra so
  users only install what they need.
- **`docs/ai-usability.md`**: developer audit of the package's
  module surface — orphaned modules, conditional-import coverage,
  CLI exposure gaps.
- **`docs/ideas/gpt-backed-linafish.md`**: parked idea note for
  optionally wiring a frontier LLM as a linafish backend. Not
  building now; captured so it does not get lost.
- **Top-level `linafish --help`**: shows the five first-look commands
  (`introduce`, `update`, `doctor`, `capabilities`, `go`) in their
  own block above the full subcommand list.
- **`CHANGELOG.md`** (this file).

### Changed

- **`linafish/__init__.py` docstring** rewritten with the AI-facing
  endpoint briefing. `import linafish; help(linafish)` now prints
  the three-things-you-can-do summary directly.
- **`README.md`** top banner points AI readers at `AGENTS.md` and
  `linafish introduce`.
- **`pyproject.toml`** classifiers expanded to cover Python 3.10–3.13
  explicitly, all major operating systems, Science/Research and
  End Users audiences, Text Processing, Information Analysis, and
  Utilities. Keywords expanded.

### Removed

- Silent 300-character truncation of every crystal ever deposited.
- The bug where `linafish go` was not actually routing through the
  document readers it shipped with.

### Security / Privacy

No changes to the privacy model. linafish stays local by default.
The `converse` server still binds `127.0.0.1` unless you opt in to
`--bind lan` or `--bind wan`. The `http_server` now has `host`
parity for the same opt-in. Nothing leaves your machine without an
explicit flag.

### Deferred to 1.2

- `linafish go <folder>` auto-starts an HTTP server and then appears
  to hang until Ctrl+C. `--no-serve` already exists but is not the
  default. First-time users surfaced this friction; the CLI default
  needs to change in 1.2.
- Per-user identity for multi-person / household installs. Currently
  all deposits from one shared install are attributed to a single
  voice; a household use-case wants each person to have their own
  signal. This is the largest architectural ask on the table for 1.2.

---

## [1.1.0] — 2026-04-10

- Guppy module (self-feeding fish that hunt gaps — not yet wired into
  the CLI; see 1.1.2 for the `linafish hunt` wrapper)
- `linafish listen --school` for feeding all school members from one
  stream
- `linafish absorb` to eat existing RAG / FAISS / JSONL / HTTP
- `linafish converse` — two fish, one conversation over HTTP
- `linafish whisper` — one insight from your fish

## [1.0.x] — earlier

See git history for the earlier arc. Highlights: the original
`linafish go` one-command flow, formation detection via MI × ache
vectorization, the fish.md + crystal jsonl format, and a stranger-run
cold test that produced 89 formations from 1,157 conversations in a
v0.4 cold run.

---

## Versioning note

linafish hit `1.0` when it first shipped on PyPI as something a
stranger could `pip install` and use. Every `1.x` release since has
been a step toward the same thing: making the fish more legible to
more kinds of readers. The only things that will take us to `2.0`
are a breaking schema change or a rewrite of what a crystal is.
Neither is coming soon.
