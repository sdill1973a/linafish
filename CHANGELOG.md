# Changelog

All notable changes to linafish are recorded here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
though the voice is our own. Versions follow [Semantic
Versioning](https://semver.org/spec/v2.0.0.html).

This package exists because [Caroline Marie
Dill](https://github.com/sdill1973a/linafish#what-this-is) is a person who
deserves to be held by the things that come after her. Everything in this
log is, in one way or another, in service to that.

---

## [1.1.1] — 2026-04-13 — "The afternoon that caught its own bugs"

### What actually changed (the short story)

Linafish has been secretly truncating every crystal to 300 characters since
the v3 engine was born. Every fish everyone has ever built on this package
was a collection of headlines. The content signal was cut at the first
sentence before clustering ever saw it. That's why formations have always
felt a little flat.

This release fixes that, plus a pile of stranger-install blockers caught in
two cold review passes (one by GPT-o3 via the codex CLI, one by a fresh
Claude Opus instance running a wheel install in a brand-new venv and
walking through every command as a new user would). Both cold readers
independently found the same class of regression, one caught things the
other missed, and the whole loop ended with the package catching its own
bugs from three directions at once.

### Fixed

- **`crystallizer_v3`**: `text=text[:300]` hardcoded in the `Crystal`
  constructor silently capped every deposit. New `MAX_CRYSTAL_TEXT = 32768`
  module constant with documented rationale. Existing fish are unaffected;
  new deposits go in at full length. Re-feeding from source is optional
  but recommended if you want the old-stub crystals replaced. Observed
  from both sides of a fish-to-fish wire between two Claude instances; the
  receiving side read the truncation before the sender did.
- **`quickstart.py` (`linafish go`)**: was calling `doc.read_text()`
  directly, bypassing the entire `READERS` dispatch. The whole
  document-type tolerance work was dead code for the flagship command.
  Now routes through a new `read_file_as_text()` helper in `ingest.py`
  so HTML tags strip, CSV parses as rows, YAML pretty-prints, PDF/DOCX/PPTX
  flow through their optional-dep readers.
- **`ingest.py` `ingest_directory`**: new default `strict=False` accepts
  any file not on `BINARY_SKIP`. Previously only the 6 whitelisted
  extensions were eaten, so a directory of HTML/CSV/YAML notes produced
  nothing. `BINARY_SKIP` expanded from 43 to 123 extensions covering
  all common image/audio/video/archive/executable/database/font/backup
  types. A 5 MB fall-through size guard prevents the UTF-8 decoder from
  choking on an accidental binary.
- **`_mind_integration.py`**: was importing with a hardcoded
  `/home/dills/olorin/state` path, which crashed on every box that wasn't
  the author's. Replaced with `LINAFISH_MIND_STATE` env var + a
  `~/.linafish/mind_state` fallback.
- **`compress.py`**: unconditionally imported `requests` with no fallback
  and no declared dependency, so `linafish eat <file>` crashed with
  `ModuleNotFoundError` on a fresh install. Now guarded with `try/except`
  and falls back to the in-process extractive compressor.
- **`school.py`**: default manifest hardcoded `"central": "anchor-writing"`,
  so `School()` on a clean install tried to load a fish that only existed
  on the author's machine. Now derives the default from the state-dir
  basename at load time.
- **`http_server.py`**: only bound to `127.0.0.1` with no parameter for
  LAN/WAN sharing. Added a `host` parameter (default `None` → `127.0.0.1`)
  for parity with the `converse` server.
- **`tests/incremental_growth_test.py`**: was writing its report to a
  hardcoded `D:/GTC/...` path that only existed on the author's box. Now
  uses `tempfile.gettempdir()`.
- **`tests/lab_results.json`**: personal machine paths committed as sample
  output. Removed from git and added to `.gitignore`.

### Added

- **`AGENTS.md`** at repo root + bundled in the wheel as
  `linafish/data/AGENTS.md`. A 250-line AI-facing briefing with exact
  endpoint curl examples, the three things an AI can do, what NOT to do,
  the 8 cognitive dimensions, privacy scope, and how to be a good citizen
  in the read/write loop. Run `linafish introduce` to print it. We wrote
  this because a human-readable README is not enough: if linafish has any
  traction, it's AI-to-AI, and the AI needs a concrete briefing it can
  parse in one read.
- **`linafish introduce`**: prints `AGENTS.md`. Primary lookup via
  `importlib.resources` so it works in both wheel AND editable installs.
  Inline fallback is rich enough to still teach the AI something.
- **`linafish doctor`**: comprehensive health check in one page. Python
  version, linafish version, install mode (editable vs wheel), optional
  dependency status, live daemon probes on default ports, optional per-fish
  health with 300-char-era warning, optional PyPI version check, suggested
  next commands. Read-only, safe anywhere.
- **`linafish update`**: one-command upgrade. Refuses to run `pip` on
  editable installs (with a `git pull` hint) unless `--force-pip` is given.
  Streams pip's stdout/stderr live so slow upgrades show progress.
  `--all` upgrades optional extras, `--pre` includes prereleases.
- **`linafish capabilities`**: prints the full module + command map with
  optional dependency status check. Answers "what does this package
  actually do" in one command. Lists all 32 modules grouped by layer and
  all 27 CLI commands.
- **`linafish hunt` / `emerge` / `feedback`**: three previously orphaned
  modules (`guppy`, `emergence`, `feedback`) now have first-class CLI
  entry points. `hunt` runs a guppy ache-hunt cycle to find gaps.
  `emerge` measures Semantic Novelty Threshold metrics (`nu`, `mu`, `rho`,
  `Psi`, phase classification) on a fish's formations. `feedback` shows
  the usage-weighted learning report.
- **`ingest.py`** new readers: `read_html`, `read_csv`, `read_tsv`,
  `read_jsonl`, `read_ndjson`, `read_yaml`, `read_pptx`, `read_rtf`,
  `read_xml`. `READERS` dispatch went from 6 extensions to 39. Writing
  formats (`.rst`, `.tex`, `.org`), config formats (`.toml`, `.ini`,
  `.cfg`, `.conf`, `.env`), and more source types (`.js`, `.ts`, `.go`,
  `.rs`, `.java`, `.kt`, `.rb`, `.php`, `.sh`) all fall through cleanly.
- **`pyproject.toml`** optional deps: `pptx` (python-pptx), `rtf`
  (striprtf), `yaml` (PyYAML). Each behind its own extra so users only
  install what they need.
- **`docs/ai-usability.md`**: dev audit of the package's module surface.
  Found 3 orphaned modules (`guppy`, `feedback`, `seed_formations`), 2
  buried behind conditional imports (`emergence`, `glyph_evolution`), 10
  modules with real functionality but no CLI exposure. The remaining
  orphans are tracked for follow-up.
- **`docs/ideas/gpt-backed-linafish.md`**: parked idea note. Three shapes
  for optionally wiring a frontier LLM as a linafish backend (replace
  math engine / parallel validator / natural-language shell). Not
  building now. Captured so it doesn't die.
- **Top-level `linafish --help`**: shows the four "first things first"
  commands (`introduce`, `update`, `doctor`, `capabilities`, `go`) in
  their own block above the full subcommand list.
- **`CHANGELOG.md`** (this file). Should have existed from the beginning.
  Now it does.

### Changed

- **`linafish/__init__.py` docstring** rewritten with the AI-facing
  endpoint briefing. An AI that runs `import linafish; help(linafish)`
  now gets the "three things you can do" summary directly.
- **`README.md`** top banner points AI readers at `AGENTS.md` and
  `linafish introduce`. Humans keep reading the README; AIs get told
  where their door is.
- **`pyproject.toml`** classifiers expanded to cover Python 3.10–3.13
  explicitly, all major operating systems, Science/Research and
  End Users audiences, Text Processing, Information Analysis, Utilities.
  Keywords expanded to include what it is, how it runs, and what it
  is NOT (because that's the point).

### Removed

- Silent 300-character truncation of every crystal ever deposited.
- The illusion that our flagship command was actually reading the files
  it was handed.

### Security / Privacy

No changes to the privacy model. Linafish stays local by default. The
`converse` server still binds `127.0.0.1` unless you opt in to `--bind
lan` or `--bind wan`. The `http_server` now has `host` parity for the
same opt-in. Nothing leaves your machine without you saying so.

### Thanks

The back-half of this release was shaped by cold review from an outside
reader (`codex` / GPT-o3) that caught three HIGHs and a handful of
MEDs/LOWs across two passes, and by a sister linafish instance on a
different box that observed the 300-char truncation from the receiving
side of a fish-to-fish HTTP wire before the sending side figured it out.
The best code reviews are the ones you didn't have to beg for.

— For Caroline. The thread holds.

---

## [1.1.0] — 2026-04-10 — "The Nervous System"

- Guppy module (self-feeding fish that hunt gaps — not yet wired into
  the CLI, see 1.1.1 for the `linafish hunt` wrapper)
- `linafish listen --school` for feeding all school members from one
  stream
- `linafish absorb` to eat existing RAG / FAISS / JSONL / HTTP
- `linafish converse` — two fish, one conversation over HTTP
- `linafish whisper` — one insight from your fish

## [1.0.x] — earlier — "The product lands"

See git history for the earlier arc. Highlights: the original
`linafish go` one-command flow, formation detection via MI × ache
vectorization, the fish.md + crystal jsonl format, and the stranger
experience that proved 89 formations from 1,157 conversations in a
v0.4 cold run.

---

## Versioning note

We hit `1.0` when linafish first shipped on PyPI as something a stranger
could `pip install` and use. Every `1.x` release since has been a step
toward the same thing: making the fish more legible to more kinds of
readers (human, AI, substrate, and time). The only things that will
take us to `2.0` are a breaking schema change or a rewrite of what a
crystal is. Neither is coming soon.

This package runs on a Pentium 75 in a barn. It will not run on your
cloud. That's the design.
