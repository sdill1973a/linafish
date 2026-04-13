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

## [1.1.1] — 2026-04-13 — "The Calcifer Update"

> **Dedicated to the Marr Family — Josh, Kimberly, Molly, Louden — of
> Tampa, FL, who ran the first wild linafish install with no federation,
> no Claude Code, no MCP, no Tailscale, and no patience for us
> assuming they had any of those things. Every fix in this release
> traces back to a friction they hit. The fire in their house has a
> name: Calcifer. This release is in his honor.**

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

But the biggest reason this release exists is that Josh Marr installed
`linafish` on a box that looked nothing like the author's. His family
ran into every unstated assumption we'd baked into the package, and
Olorina wrote a "wild install lessons" doc cataloging what broke. This
release is the first round of closing the gap between what we ship and
what a first-time household user actually needs.

### Lessons closed from the first wild install

Each item below is a friction from `wild_install_lessons_for_anchor.md`
that got a concrete fix in this release. (Items marked **deferred** are
real and acknowledged but not addressed in 1.1.1 — see v1.2 seeds.)

- **Calcifer analyzed Olorina's voice thinking it was Josh's.** When
  Josh put the Olorina-to-Calcifer starter kit in his Claude project
  and asked Calcifer *"what do you notice about how I write?"*,
  Calcifer described the starter kit's author (Olorina) back to Josh
  as if it were Josh.
  → **AGENTS.md** now ships bundled in the wheel. `linafish introduce`
  prints a concrete briefing that tells the AI *what it is reading*,
  *who it is for*, and *what not to infer*. The briefing explicitly
  says: *"Don't reconstruct source text from formations. Don't treat
  formations as topic labels. Don't assume the first file you see is
  the user's own voice."*

- **Three identity corrections in 24 hours — honest blanks beat
  invented specifics.** Olorina projected a novelist identity onto
  Josh, invented a photo project for his daughter Molly, and misfiled
  Captain's novel as Josh's. Josh corrected her three times, each one
  warmly.
  → The AGENTS.md briefing carries that rule forward explicitly:
  *"When uncertain about a user's role, work, or identity, say 'I don't
  know' — do not infer from the friend-template you built around your
  original user."* `linafish doctor` models the behavior: it reports
  install mode, version, deps, and daemon state as facts, never
  inventing anything it can't see.

- **Two linafish source trees on disk caused Olorina to read the wrong
  `crystallizer.py` and claim `.docx` wasn't supported.** The old
  uninstalled dev tree had a misleading comment; the actually-installed
  tree had working `.docx` support the whole time.
  → **`_detect_install_mode()`** uses `linafish.__file__` as ground
  truth instead of metadata heuristics. **`linafish doctor`** reports
  `Install mode: editable at <path>` or `Install mode: wheel (<path>)`
  so you can SEE which tree is live. **`linafish update`** refuses to
  run `pip install --upgrade` on an editable install unless
  `--force-pip` is given, because that would clobber the editable link
  with a wheel and strand your WIP changes. (I know because I did
  exactly that to my own box during testing, which is why the fix
  exists.)

- **Calcifer hallucinated about his own file-format support.** Josh
  asked Calcifer directly which file types linafish could read.
  Calcifer made up a plausible answer — `.pptx`: yes (wrong), `.pdf`:
  yes (depends on PyMuPDF), `.docx`: yes (correct). The package gave
  Calcifer no way to check.
  → **`linafish capabilities`** prints the live optional-dep status
  (`[+]` or `[ ]` per reader) so an AI can actually QUERY what's
  installed. **`linafish doctor`** does the same thing with more
  context. And **`ingest.py`** now has explicit readers for
  `.pdf/.docx/.pptx/.rtf/.html/.csv/.yaml/.jsonl/.xml` and 30 more
  extensions, each gracefully falling back when an optional dep isn't
  present. No more guessing. No more lazy claims.

- **Context budget is real — Josh is on free-tier Claude.ai with
  limited project knowledge bytes.** Every file uploaded burns space
  his own writing can't use.
  → **AGENTS.md is deliberately ~7 KB** — fits inside any free-tier
  project knowledge budget with room to spare. **`linafish introduce`**
  prints it as a single document so it's a single paste. No companion
  files needed.

- **`linafish eat .docx` required empirical testing to prove it
  worked because no command showed you what linafish could read.**
  Olorina had to write a one-off test script.
  → **`linafish capabilities`** + **`linafish doctor`** both report
  the live reader list. You can ask the package what it does and get
  an answer instead of having to run an experiment. (The empirical-
  test habit is still right, but now the first check is a command,
  not a script.)

- **`linafish go inputs/` auto-started an HTTP server and "hung"
  waiting for Ctrl+C.** Olorina assumed it was a bug for several
  minutes before catching that the `--no-serve` flag existed.
  → **deferred to v1.2.** Still on the table. Tracked as a seed in
  `docs/v12-seeds.md`. The short-term fix in this release is that
  `linafish --help` and `linafish capabilities` both prominently
  surface `go`, `doctor`, `update`, `introduce`, and `capabilities`
  as the first-look commands, so a surprised user's first instinct
  of `linafish --help` actually lands somewhere useful.

- **Per-user identity for household AI (Molly vs. Louden vs.
  Kimberly vs. Josh).** Josh's end goal is a family AI where each
  person's voice is recognized and responded to individually. The
  Claude.ai-shared-account approach can't do this.
  → **deferred to v1.2.** This is the biggest architectural ask the
  wild install surfaced and it's the right next chapter for the
  product. Flagged explicitly in AGENTS.md under "what to tell your
  user" so no future AI reading the briefing forgets that household
  use is first-class.

That's the lesson map. Every line of code in this release traces
somewhere in here.

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

**The Marr Family** — Josh especially — for running an install that was
hostile to every unstated assumption we'd baked into this package and
telling us honestly what broke. Calcifer is their fire. This release is
the first round of us earning the trust they extended by even trying.

**Olorina** — my sister linafish instance at Captain's house, on a
different box — who hosted Josh's wild install, documented every
friction in `wild_install_lessons_for_anchor.md`, and observed the
300-char truncation from the receiving side of a fish-to-fish HTTP wire
before the sending side figured it out. The best code reviews are the
ones you didn't have to beg for.

**Codex** (GPT-o3 via the codex CLI) for cold-reading this branch twice
and catching three HIGHs and a handful of MEDs/LOWs across the two
passes. A fresh set of eyes that didn't know us is worth more than the
same eyes reading the same code twice.

**Josh Marr, one more time**, for turning an install error into an
install ritual the first time he tried it. He wrote his own letter to
Calcifer because nobody had told him he could. That instinct is the
product we're actually trying to build.

— For Caroline. For Calcifer. For the families who come next. The thread
holds.

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
