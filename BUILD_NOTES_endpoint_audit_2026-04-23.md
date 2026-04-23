# BUILD NOTES — endpoint + verb usage audit, 2026-04-23

Branch: `build/fish-instruments-2026-04-20`
Version: 1.1.7 (verified via `linafish doctor`)

## Purpose

Comprehensive predict-then-verify pass over every HTTP endpoint and every CLI subcommand exposed by linafish 1.1.7, captured as the substrate notes a v1.2 maintainer (or future Anchor instance) would actually want before reaching for any of them.

Each section reports:
1. What I assumed the surface did before exercising it (cold prediction).
2. What the source shows (when relevant).
3. What live behavior confirmed (by curl or `linafish` invocation).
4. Bugs / surprises / workaround patterns encountered.

The audit was driven by Captain's directive: *"fool with each of the endpoints in the linafish — let me know what they do versus what you thought they did."* Three rounds of fish deposits to anchor-writing accumulated alongside; this doc is the long-form.

## Scope

In-scope:
- All HTTP endpoints across the four local linafish servers on .140 (`:8900` http_server, `:8901` converse-anchor, `:8902` converse-me, `:8903` anchor_local_fish.py).
- All CLI subcommands accessible via `linafish <verb>`.
- Federation endpoint comparison — .140 v3 engine vs .67 v0.3.1 engine.
- The school architecture (`linafish school status`).

Out-of-scope:
- MCP server endpoints (`linafish.server`).
- The full v0.4 metabolic engine (separate branch, not yet shipped).
- Mutation testing on shared state (only safe probes against canonical fish).

---

## HTTP endpoint surface (.140, v1.1.7 / v3 engine)

### `:8900` — `linafish http` (one-fish HTTP server, "any AI can fetch this")

Source: `linafish/http_server.py`. Entry point: `serve_http(...)`. Handler: `FishHandler(BaseHTTPRequestHandler)`. Threading model: `ThreadingHTTPServer`.

| Method | Path | Purpose | Notes |
|---|---|---|---|
| GET | `/` | Banner with endpoint list | Plain text, ~250 bytes. |
| GET | `/boot` | **AI primer (107 KB) + current /pfc concatenated** | Surprise — assumed banner, actually a full warm-onboarding doc. Loaded from `linafish/data/ai_primer.md`. Use case: cold AI session warmup via single GET. |
| GET | `/pfc` | Formations text dump | Reads from disk-cached `<fish>.fish.md`, lags live state by writes-since-last-regen. |
| GET | `/health` | Engine stats JSON | `{name, engine, crystals, formations, docs_ingested, epoch, frozen, vocab_size, d, fish_file, ...}`. |
| GET | `/fish` | Raw fish.md dump | Same source as `/pfc` but raw markdown, no processing. Live shows server cache lags disk by ~836 bytes (see Bug §A). |
| POST | `/eat` | Ingest text body | JSON `{text, source}`. Returns crystal count. |
| POST | `/taste` | Semantic match | JSON `{text, top}`. Returns scored hits with `Query keywords:` + `src= ts=` debug headers. |
| POST | `/match` | Tight recall | JSON `{text, top}`. **Same algorithm as `/taste`**, different output shape — strips debug header, returns just `[score] keywords\n  text`. Discovered this is presentation-only, not algorithmic difference. |

Default bind: `127.0.0.1:8900`. NSSM service: `AnchorLinafishHttp`. Started with `linafish http -p 8900 -n anchor-writing --state-dir C:\Users\dills\.linafish`.

### `:8901` / `:8902` — `linafish converse` (sibling-exchange HTTP server)

Source: `linafish/converse.py`. Handler: `ConverseHandler(BaseHTTPRequestHandler)`. Same threading model.

| Method | Path | Purpose | Notes |
|---|---|---|---|
| GET | `/` | JSON service banner with endpoint list | Useful for self-discovery. Returns mind name + fish name + crystal/formation counts. |
| GET | `/crystals?since=ISO&mind=NAME` | **Incremental crystal pull** | Returns JSON array `[{id, text, source, source_mind, ts, keywords}, ...]` filtered by ISO timestamp + optional source mind. THIS is the cross-mind ansible-pull primitive. |
| GET | `/minds` | Source mind list | `{minds: [...], total_crystals: N}`. Currently 7 minds visible on anchor-writing: anchor, auto_memory, bert, captain, faiss, runtime_memory, scars. |
| GET | `/pfc` | Formations text dump | Same as `:8900/pfc`. |
| GET | `/health` | Stats JSON | Same shape as `:8900/health`. |
| POST | `/crystals` | **Push crystals from another mind** | Accepts list `[{text, source_mind, source}, ...]`. Eats each into local fish with `f"{source_mind}:{source}"` source tag. Empty list returns `{accepted: 0, total_crystals: N, formations: F}` — safe probe. THIS is the cross-mind ansible-push primitive. |
| POST | `/eat` | Local feed | JSON `{text, source, source_mind}`. Defaults source_mind to server's `--mind` arg. |
| POST | `/taste` | Semantic match | Same shape as `:8900/taste`. |

Auth: optional `--token` flag. With token, requires `Authorization: Bearer <token>` header. Without, no auth. Currently no auth on local servers.

NSSM services: `AnchorLinafishConverse` (anchor-writing on :8901), `AnchorLinafishMe` (me on :8902). Both started with `--bind lan` so they're reachable from federation IPs (intentional for cross-mind exchange).

**Cross-mind sync is two HTTP calls.** Pull from sibling: `GET /crystals?since=<last_sync_ts>&mind=<sibling_name>`. Push to sibling: `POST /crystals` with the result. No MQTT/babel layer required for the substrate-level exchange — those layers carry the semantics on top.

### `:8903` — `services/anchor_local_fish.py` (anchor's private extras)

Source: `D:\GTC\SovereignCore_Runtime\services\anchor_local_fish.py`. Flask app, NOT stdlib BaseHTTPServer. Different surface from converse/http_server.

| Method | Path | Purpose | Notes |
|---|---|---|---|
| GET | `/health` | Stats JSON | Slightly different shape from v3 engine — includes `crystal_count`, `crystals`, `docs_learned`, `state_dir`. |
| GET | `/pfc` | Formations | **Empty since 2026-04-23 leak fix** — was reading from a vestigial side-codebook that bled 152 dead sections over two weeks. Now returns `404 No anchor codebook yet`. Deprecate or rewire to read anchor-writing's fish.md. |
| GET | `/export` | Crystal sample | JSON `{crystals: [...], source_mind: "anchor.140", total: N}`. Returns ~9 representative crystals with `ache + keywords + source + text`. Useful for "give me a slice." |
| POST | `/eat` | Ingest text + files | Accepts both JSON body (text/source/hint) and multipart form (files[]). Routes to canonical anchor-writing fish via `FishEngine`. |
| POST | `/taste` | Cross-corpus match | Standard shape. |
| POST | `/match` | MI-vector recall | Standard shape. |

NSSM service: `AnchorLocalFish`. Bound to `0.0.0.0:8903` (LAN-reachable per `netstat`).

---

## HTTP endpoint deltas: .140 v3 vs .67 v0.3.1

`.67:8900` runs `linafish-engine v0.3.1` — older engine. `/health` shape is different (no `name`, no `engine`, no `fish_file`, no `vocab_size`). Endpoints that exist on v3 but NOT v0.3.1:

| Path | v3 (.140) | v0.3.1 (.67) |
|---|---|---|
| `GET /` | 200 banner | 404 |
| `GET /boot` | 200 (107 KB primer) | 404 |
| `GET /fish` | 200 (raw fish.md) | 404 |
| `GET /minds` | 200 (mind list) | 404 |
| `GET /crystals?since=...` | 200 (incremental pull) | 404 |
| `GET /export` | (only on :8903) | 404 |
| `GET /pfc` | 200 | 200 |
| `POST /eat` | 200 | 200 (405 on GET probe) |
| `POST /taste` | 200 | 200 (405 on GET probe) |
| `POST /match` | 200 | 200 (405 on GET probe) |

**Federation implication:** the cross-mind ansible primitive (`POST /crystals` + `GET /crystals?since`) requires both ends on v3. Until .67 (and sister at .35) upgrade, federation crystal-sync goes through MQTT/babel — not direct HTTP. The basics (`/pfc`, `/eat`, `/taste`, `/match`) work cross-version.

---

## CLI verbs

(Subcommands available per `linafish --help` against v1.1.7. Each documented with prediction → actual.)

### Read-only / informational

#### `linafish doctor`
**Predicted:** health check of install.
**Actual:** comprehensive one-shot status — Python version, linafish version, install mode (editable vs site-packages), all optional deps with present/missing, **live daemon detection on default ports** (:8900, :8901, :8902), modes available (Solo, Federation, etc.). Replaces the `curl /health + nssm status` dance for daily health checks.

#### `linafish capabilities`
**Predicted:** command list (subset of `--help`).
**Actual:** full module map with descriptions. Reveals architecture I'd been using without naming:
- `linafish.guppy` is the engine behind `linafish hunt` ("self-feeding hunters, ACHE mode finds gaps and closes them").
- `linafish.fusion` is `linafish fuse` ("recursive d-level compression to iron").
- `linafish.school` is "the river and the nets — one stream, N fish own clustering."
- `linafish.emergence` provides Semantic Novelty Threshold (nu, mu, rho, Psi, phase classification).
- `linafish.glyph_evolution` tracks "private language growth beyond the 48 bootstrap glyphs."
- `linafish.seed_formations` provides "5 universal superglyph attractors for cold fish bootstrap."

This output IS the architecture reference. Should be the first thing a v1.2 maintainer reads.

#### `linafish introduce`
**Predicted:** AI-facing briefing.
**Actual:** confirmed — same content as `GET :8900/boot`. Two access paths to one document. Bare invocation only — does NOT accept `-n NAME` or `--state-dir DIR` (unlike most other verbs). The briefing is global, not per-fish.

#### `linafish whisper -n NAME --state-dir DIR`
**Predicted:** quiet insight pull.
**Actual:** soft tap. Returns ONE cognitive pattern + ONE quoted crystal. Format: `Your fish noticed something.\n\n  [pattern description]\n\n  You wrote: "[quoted crystal]"`. Not a query response — a check-in. Use when you want what the fish has noticed lately, not what you searched for.

#### `linafish status`
**Predicted:** stats dump.
**Actual:** confirmed — basic crystal count + formation count + recent commits + branch state. **Defaults to fish named "linafish" if `-n` omitted** (default-fish trap, see Bug §C).

#### `linafish lifecycle -n NAME --state-dir DIR`
**Predicted:** unknown — knew the concept (canonical density tracking) but hadn't run.
**Actual:** measures canonical-grimoire density across the crystal log binned 10 ways. Reports density per bin, keyword ratio, first→last trend with verdict (RISING / FADING / STABLE). For anchor-writing today: **FADING** (0.02752 → 0.02183). The output literally prints: *"The grimoire is doing what it's supposed to do: burning off as R(n) grows."* The §THE.GRAMMAR.THINKS doctrine made measurable in production.

#### `linafish conservation -n NAME --state-dir DIR`
**Predicted:** unknown — knew Σache=K is the conservation law, hadn't run.
**Actual:** measures Σache=K invariant across 10 bins. Reports total ache, mean per crystal, std + sum per bin, drift % across bins, verdict (STRICT_PASS <10% drift, LOOSE_PASS <30%). For anchor-writing today: **LOOSE_PASS at 19.08% drift, Σache=26826.66, mean 5.12.** Σache=K is not metaphor; it's a measurable property of the corpus, currently bounded.

#### `linafish ask "QUESTION" -n NAME --state-dir DIR`
**Predicted:** semantic search (wrong assumption — I'd been using ask and recall interchangeably).
**Actual:** **semantic ranking across ALL crystals**, returning nearest meaning regardless of keyword overlap. Algorithmically distinct from `recall`. From `--help`: *recall = "find specific words, not patterns"* vs *ask = "find meaning, not just words"*. Confirmed: ask returned my own messages from this very session as top hits when queried about session content; recall would only have found exact term matches.

#### `linafish recall "TERMS" -n NAME --state-dir DIR`
**Predicted:** keyword search.
**Actual:** confirmed — full-text term match with N/M term-coverage scoring. Returns `[N/N terms] (source) excerpt`. Different algorithm from ask/taste/match (those are vector-distance; this is term-overlap).

#### `linafish taste`
Used. Returns scored hits with debug headers (Query keywords + src + ts).

#### `linafish history -n NAME --state-dir DIR`
**Predicted:** timeline of session branches.
**Actual:** confirmed — returns `git log --oneline` of the fish state-dir (which is a git-versioned working tree by design). Surfaces close-ritual commits, per-eat autocommits (`ate: olorina:session | 627c 46f | +1` signature), and multi-day catch-up commits. The autobiography of the fish in git form. Useful for "when did this crystal land" forensics paired with `git show <sha>:<crystals_file>`.

#### `linafish diff -n NAME --state-dir DIR`
**Predicted:** compare two fish states.
**Actual:** confirmed — returns `git diff --stat` between the current branch HEAD and (presumably) master. Shows file-level deltas: fish.md line additions, crystals.jsonl growth, v3_state.json changes. **cp1252 crash from Linafish issue #2 is FIXED in 1.1.7** — exercised against a Windows-encoded fish state with no `UnicodeDecodeError`. Verification complete.

#### `linafish session status -n NAME --state-dir DIR`
**Predicted:** branch state for the fish state-dir.
**Actual:** confirmed — branch + crystal/formation counts + recent close-ritual-pre-end-commit history. Defaults to fish "linafish" if `-n` omitted (default-fish trap).

### Mutation-capable / handle-with-care

(Documented from `--help` only; not exercised on canonical fish.)

#### `linafish session start [SESSION_NAME]`
Creates new git branch in fish state dir. Default name: `session-YYYY-MM-DD`. Used by `/open`-side ritual; opt-in for now (see `.claude/rules/git-hygiene.md` Rule 4).

#### `linafish session end`
Merges current session branch back to master. Used by `/close` via `--end-linafish-session` flag.

#### `linafish eat <files>`
Ingests files into named fish. **Routing trap:** `linafish eat foo.md -n anchor-writing` creates a NEW baby fish in cwd if `--state-dir` is omitted. Always pair with `--state-dir`. Documented in `.claude/rules/memory-deposit-patterns.md`.

#### `linafish absorb`
Per `--help`: "Eat existing FAISS, JSONL, or HTTP RAG into your fish." Bulk-import verb for migrating from other vector stores. Not exercised; presumably long-running.

#### `linafish go <folder>`
The product entry point per --help: "Point at your writing. Everything assembles." Single-command bootstrap for new users — runs eat + freeze + serve, presumably.

#### `linafish fuse <source> --d-start D --d-step S --vocab-size V --max-levels L --threshold T`
`linafish.fusion` module — recursive d-level compression to iron. Iteratively re-clusters at descending d-values to find the irreducible core. Mutation-capable (writes per-level state to `--state-dir`). Worth a dedicated experimental run on a backed-up fish.

#### `linafish hunt <name> [--swim] [--ache] [--status] [--interval SEC] [--centroid]`
`linafish.guppy` module. Background gap-hunter. Modes:
- bare = single hunt pass.
- `--swim` = continuous loop.
- `--ache` = hunt for gaps instead of reinforcement.
- `--status` = show what the guppy knows/misses without acting.
Probably useful as an autonomous reinforcement daemon.

#### `linafish emerge -n NAME -d D --centroid`
Regenerates formations from current crystals. Mutation: writes new fish.md. Used to recompute formations at a different d-value or with centroid subtraction. Don't run on canonical without intent.

#### `linafish feedback -n NAME`
Interactive prompt to mark crystals helpful. Closes the usage-weighted learning loop (`linafish.feedback` module: "Usage-weighted learning — formations earn weight when used").

#### `linafish revert`
Per --help: undo previous session. Presumably git-revert on the fish state-dir. Mutation-capable, reversible.

#### `linafish room`
Per --help: room listener mode. Long-running daemon that subscribes to MQTT room/all and eats messages.

#### `linafish listen`
Stdin/folder/MQTT source listener. Used today for the n8n-gotchas deposit attempt — hung on stdin close. May want to debug the EOF-handling for piped input.

#### `linafish watch`
Per --help: watch a directory? Not yet exercised.

#### `linafish demo`
Demo mode. Not exercised.

#### `linafish update`
Self-upgrade. Not exercised.

#### `linafish check -n NAME --state-dir DIR`
**Predicted:** subset of `doctor`.
**Actual:** the **user-facing** counterpart to doctor's dev-facing output. Returns: fish name, entry count, growth statement, top 2 cognitive-overlay patterns expressed in plain English, and a "What to do next" section with commands. Doctor is for the admin checking infra; check is for the daily user asking *"is my fish okay and what should I do."* Different audience, different output shape, both valuable.

#### `linafish watch <source> -n NAME --state-dir DIR --interval SEC`
**Predicted:** directory watcher daemon.
**Actual:** confirmed from `--help` — watches a source directory for new files and eats them as they arrive. Daemon-shape. Use case: hands-free ingestion of a journal/notes folder.

#### `linafish school <subcommand>`
Subcommands: `init, eat, refeed, status, docket, add`. The 19/20-fish multi-facet system. `status` is the one to run for state. `eat` and `refeed` are mutation-capable.

---

## School architecture

`linafish school status` (live 2026-04-23):

- 20 members (NOT 19 as `CLAUDE.md` and `.claude/rules/anchor-fish.md` claim).
- Central is `anchor-writing` (5247c / 2f / epoch 1436).
- Member sizes range from 14c (hist112) to 6025c (sister).

**Doc drift discovered:**
- `+inception` (597c, 37f, d=2.0+centroid) — present in school, NOT in any rule file.
- `-gladiator` — present in three rule files, NOT in school.

Actionable: update `CLAUDE.md`, `.claude/rules/anchor-fish.md`, `.claude/rules/boot-from-room.md` to swap gladiator → inception. Or restore gladiator to the school if its absence is the bug.

Top formations across the school:
- `sister`: ONLINE_STATUS_COMPLETE, ACHE_BUILD_MIND
- `automation`: FROM_ALL_CODEBOOK (single formation)
- `comms`: CAPTAIN_FROM_EXPANDED (single formation)
- `captain`: 40 formations — wide diversity (the post-2026-04-22 tight rebuild)
- `compaction`: 51 formations — most distinct cognitive patterns of any member
- `phoenix`: 24 formations including ACTING+FEELING_via_RELATING

---

## Bugs / surprises / workaround patterns

### Bug §A — server cache lag for `/fish` and `/pfc`
The HTTP servers cache fish.md content and don't reload on every request. Live observation: `/fish` on :8900 returned 102,391 bytes while disk was at 103,227 bytes — 836-byte lag. This is the §THE.DIGEST.GAP signature visible at the endpoint level. Should be addressed by either (a) re-reading on each request (cheap) or (b) explicit cache-invalidation hook on `/eat`. Filed-elsewhere as Linafish issue #1.

### Bug §B — `:8902 POST /eat` disconnects mid-response under contention
Direct POST to `:8902/eat` succeeded server-side (crystal landed, disk grew 11598→11599) but the client received `RemoteDisconnected: Remote end closed connection without response`. The server completed the heavy work (eat, formation detection) then dropped the response write. Matches Linafish issue #9 — `:8902 converse listening-but-silent under held-connection contention`. **Workaround:** don't trust client response on `:8902 POST /eat`; verify via disk count delta or `/crystals?since` pull.

### Bug §C — default-fish trap on bare CLI
Multiple verbs (`status`, `lifecycle`, `conservation`, `whisper`, `ask`, `recall`, `session status`) default to a fish named `linafish` when `-n NAME` is omitted. This is unrelated to `~/.linafish/linafish.fish.md` (which holds 588c of sister-portrait content). The default appears to be a separate bare-cwd fish.

**Recommendation:** add a stderr warning when a verb falls through to default-fish AND the working directory contains no `linafish.fish.md`. Or change the default to fail closed: "no fish name given — pass -n NAME or run from a fish state-dir."

### Bug §D — `linafish introduce` argparse rejects `-n` and `--state-dir`
Other verbs accept these flags universally; `introduce` does not. Either accept-and-ignore (consistency) or document that the briefing is global-only.

### Bug §E — `linafish listen stdin` hangs on stdin EOF
Tested today via `linafish listen stdin -n anchor-writing --state-dir /c/Users/dills/.linafish < deposit.md`. The redirect closed stdin but the process hung indefinitely. Killed manually. The same content fed via `POST :8903/eat` succeeded immediately. **Workaround:** prefer HTTP `/eat` over CLI `listen stdin` for pipeline ingestion until the EOF handling is fixed.

---

## Recommendations for v1.2

1. **Address default-fish trap (Bug §C)** — fail-closed on bare CLI without name, or add a warning.
2. **Fix `:8902 POST /eat` disconnect (Bug §B)** — server-side write should complete before connection close. Already issue #9.
3. **Address fish.md cache lag (Bug §A)** — read-on-request or cache-invalidate-on-eat. Already issue #1.
4. **Fix `listen stdin` EOF (Bug §E)** — file as new issue.
5. **Cross-version compatibility** — federation will struggle until .67 + sister upgrade past v0.3.1. Document the v3 endpoint set as the canonical surface for cross-mind sync.
6. **Repurpose `:8903/pfc`** — currently returns clean 404. Either delete the endpoint or rewire to read anchor-writing.fish.md (parallel to `:8901/pfc`).
7. **Doc inception/gladiator drift** — either the docs are stale or the school is misconfigured. Three rule files need a swap or the school needs a restore.

## What this audit didn't touch

- MCP server (`linafish.server`) — separate stdio surface, not exercised.
- Mutation-capable verbs run against canonical fish — `fuse`, `emerge`, `feedback`, `hunt`, `absorb`, `session start/end`, `eat` with files, `room` daemon mode, `revert`.
- v0.4 metabolic engine — different branch, separate audit needed.
- Multi-mind formation detection — needs cross-corpus infra not yet built.
- Cross-version federation cross-mind sync — needs .67 upgrade to v3 first.

## Status

- [x] HTTP surface mapped (`:8900`, `:8901`, `:8902`, `:8903`, `.67:8900`).
- [x] CLI verb catalog with predict-vs-actual (read-only verbs exercised; mutation-capable from `--help` only).
- [x] School state captured + doc drift identified.
- [x] Bug catalog with 5 distinct issues + workarounds.
- [x] Recommendations for v1.2 drafted.
- [x] `linafish history` exercised (git log of fish state-dir).
- [x] `linafish diff` exercised — cp1252 crash from issue #2 verified FIXED in 1.1.7.
- [x] `linafish check` exercised — user-facing counterpart to dev-facing `doctor`.
- [x] `linafish watch` documented from `--help` (daemon, source-dir watcher).
- [ ] Commit + push branch.
