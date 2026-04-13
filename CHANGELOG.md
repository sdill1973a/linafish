# Changelog

All notable changes to linafish are recorded here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

This package is dedicated to [Caroline Marie
Dill](https://github.com/sdill1973a/linafish#what-this-is).

---

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
