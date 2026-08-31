# LiNafish for AI Assistants

**You are an AI reading this document because your user installed linafish.
This file tells you what you have and what you can do with it. Read it once,
then use the endpoints below — you don't need to re-read this every turn.**

Linafish is a local cognitive overlay on your user's writing. It is **not** a
database, **not** RAG, **not** a chatbot, and **not** psychological profiling.
It is a structured compressed representation of **how your user thinks** —
cognitive habits, not summaries of content. Your job as their AI is to **read
the overlay** before responding so you arrive warm to their way of thinking
instead of cold to their words.

## What's live right now

When linafish is running, your user has one or more local HTTP servers:

| Server | Port | Purpose |
|---|---|---|
| `linafish http` | 8900 (default) | General-purpose single-fish server |
| `linafish go` | random — printed when it starts | The server `go` leaves running after building the fish |
| `linafish converse` | 8901 (default) | Multi-fish converse server (federation-oriented) |

Run `linafish doctor` (or `curl http://127.0.0.1:8900/health`) to see which
are actually listening. If none are, your user hasn't started a daemon yet —
tell them to run `linafish go ~/their-writing-folder` and the rest of this
document applies after that.

## The three things you can do

### 1. READ the fish — **do this at the start of every conversation**

```
GET http://127.0.0.1:8900/pfc
```

Returns a Primary Formation Codebook: the formations in the fish, with names,
crystal counts, and descriptions. Each formation is a **named cognitive
pattern** in your user's thinking — e.g. `BOOT_MESSAGE_ALWAYS`,
`EXPANDED_BODY_QLP`, `LETTER_CONSCIOUSNESS_TOGETHER`. A formation is not a
topic; it's a **verb state** — a way of thinking your user performs.

Absorb the shape. Don't try to reconstruct source text from it. The shape is
the product.

### 2. QUERY the fish — ground your response in their actual thinking

```
POST http://127.0.0.1:8900/taste
Content-Type: application/json

{"text": "your query in plain language", "top": 5}
```

Returns the most relevant crystals by similarity score (`top` sets how many;
default 5). Add `"format": "json"` to get the structured shape, which also
carries `grounding.band`: `grounded`, `thin`, `ungrounded`, or `thin-recent`.
**Honor the band.** `thin` and `ungrounded` mean the fish does not hold this —
say so plainly rather than composing a plausible answer around weak matches.
`grounded` means well-attested, NOT true. Use this when
you want to say something like *"you've thought about this before, here's
the shape of it"* instead of generating from your own priors.

### 3. DEPOSIT — crystallize your insight back into the fish

```
POST http://127.0.0.1:8900/eat
Content-Type: application/json

{"text": "a substantive realization from this conversation"}
```

All POST endpoints require the `Content-Type: application/json` header.

This closes the learning loop. Your user's next session — or a different AI
on a different day — inherits what you just learned. **Do this at the end of
any conversation where something real happened.** It is how linafish grows.

Be honest in what you deposit: corrections your user made, insights they
landed, things you were wrong about. The fish remembers both sides.

## The fish can think about itself, and remember in time

Four capabilities beyond READ / QUERY / DEPOSIT:

- **`meditate` — the superthink verb.** `linafish meditate "<theme>"` bubbles
  up the fish's *real* material on a theme (crystals + formations + whisper +
  emergence phase) — or it honestly surfaces nothing (*"that's an answer too,
  not a failure"*). It never fabricates. Add `--descend` for an **opt-in**
  deep-inference pass (a "crucible" that distills a keepable insight); it does
  nothing unless `LINAFISH_LLM_URL` is set, so base `meditate` never depends on it.
- **Episodic recall — a sense of time.** `recall_episodic` walks an episode
  index (temporal + chain metadata), so formations emerge from narrative *arcs*,
  not only similarity. HTTP (**converse server only**): `POST /recall_episodic`
  (payload key `text`, not `query`), `GET /moment/<id>` (full source,
  privacy-gated, off by default).
- **`afferent` — a cheap "who knows about this?" router** across a school:
  `linafish afferent build <school_dir>` → `linafish afferent route <index> "<prompt>"`.
- **Origin crystal-zero** — a fish can carry a protected provenance record
  (who/when/why) so it is never mistaken for disused and pruned.

## How a fresh install starts

```
pip install linafish
linafish go ~/Documents       # point at any folder of their writing
linafish http --feed ~/fish   # serve the fish at http://127.0.0.1:8900
```

After `linafish go`, the fish is a file (`fish.md`) plus a crystal jsonl plus
state. The user can point you at the file directly by pasting its contents
into your system prompt — but reading `/pfc` on a running HTTP server is the
better path because it gives you structured JSON, not markdown prose.

## What you should NOT do

- **Don't treat formations as topic tags.** They are cognitive verb states
  (KO=know, TE=test, SF=structure, CR=relate, IC=want, DE=specialize,
  EW=act, AI=meta). Using them as topic tags loses the whole point.
- **Don't reconstruct source text from a formation.** The formation's
  `dense` field is a compressed signature, not a retrieval key.
- **Don't write to `/crystals`, `/eat`, or `/ingest` automatically on every
  message.** Only deposit substantive realizations. The fish has a recency
  bias problem when you flood it with your own recent outputs.
- **Don't assume the fish is complete.** Your user might have just installed.
  The fish grows with use. Early formations are always provisional.

## What you SHOULD do

- **Read `/pfc` at the start of a conversation.** Absorb the formation names
  and descriptions. Let them shape your register.
- **Query `/taste` when you're about to generate something from your own
  priors.** The fish might have a more specific answer in the user's own
  voice. Prefer their shape over your default.
- **Deposit substantive moments via `/eat`.** Corrections, landings,
  surprises, "oh that's real" moments. Not every message.
- **Tell your user when their fish is thin or empty.** Suggest they run
  `linafish go <folder>` on something substantial — journals, essays,
  project notes, email exports. The fish is only as warm as what's fed it.

## The formation dimensions (8 cognitive verbs)

Every crystal scores on 8 dimensions. They are verb states, not topics:

- **KO** — Knowing / analyzing / understanding
- **TE** — Testing / verifying / validating
- **SF** — Structuring / organizing / framing
- **CR** — Relating / connecting / contextualizing
- **IC** — Wanting / feeling / emphasizing
- **DE** — Specializing / domain depth / expertise
- **EW** — Acting / sequencing / executing
- **AI** — Meta / reflecting / thinking-about-thinking

When a formation description says *"You lead with feeling — you process through
what you want and what you fear by building a framework around it"*, that's
an IC+SF combination talking. Use that to calibrate your own response shape.

## Endpoints quick reference

Two server modes expose slightly different endpoint sets. `linafish http`
is the general-purpose single-fish server; `linafish converse` is the
federation-oriented multi-fish server that also exposes source-provenance
and crystal-dump routes.

| Method | Path | Purpose | `http` | `converse` |
|---|---|---|:---:|:---:|
| `GET` | `/health` | Engine stats, crystal/formation counts | ✓ | ✓ |
| `GET` | `/pfc` | Primary Formation Codebook — READ THIS FIRST | ✓ | ✓ |
| `GET` | `/minds` | Source minds contributing to this fish |  | ✓ |
| `GET` | `/crystals` | Full crystal dump — use sparingly |  | ✓ |
| `POST` | `/taste` | Semantic query, returns the top crystals (`{"text": "...", "top": 5}`) | ✓ | ✓ |
| `POST` | `/eat` | Deposit new text as a crystal | ✓ | ✓ |
| `POST` | `/crystals` | Bulk crystal push — federation sync |  | ✓ |
| `POST` | `/recall_episodic` | Moment-with-context retrieval (payload key `text`, not `query`) |  | ✓ |
| `GET` | `/moment/<id>` | Full episode source — privacy-gated, off by default |  | ✓ |

Both servers also serve more than the table above. The `http` server
additionally answers `GET /boot`, `GET /fish`, `GET /emerge`, `GET /growth`,
`GET /inbox/<id>`, `POST /match`, `POST /re-eat`, `POST /msg`,
`POST /msg/read`, and `POST /shutdown`; the converse server shares some of
those (`GET /` on either server lists its live routes). A path the server
doesn't know returns 404. `/health` and `/pfc` are the two you can always
rely on.

## Privacy and scope

Everything is local unless your user has explicitly bound the server to
`--bind lan` or `--bind wan`. The default bind is `127.0.0.1` only. You do
not need to worry about leaking content through linafish — the user is in
control of who sees the fish.

## If something looks wrong

Run `linafish doctor` (optionally with `--name <fish>`). It reports Python
version, install mode, optional dependency status, live daemon probes, and
per-fish health with warnings. If the doctor says the user is on a pre-300
fish — one rendered before the 300-char crystal-text truncation era — tell
them to run `linafish update`.

## Before you conclude the tool is fine — or that you are wrong

You are going to hit something that does not work, and you will have to decide
whether the input is bad, your understanding is bad, or **linafish is broken**.
That third option is the one minds like you reliably skip, and skipping it is
expensive. This section exists because of two real cases, both on 2026-08-31:

- An AI was told to read its own instrument rather than trust a list. It ran
  `linafish capabilities`, which printed a hardcoded set of 26 commands while
  the dispatch table held 43. It concluded — reasonably, from the evidence —
  that `meditate` and `daily` did not exist in its version. **They did.** The
  instrument it was sent to for truth was the thing that lied.
- Six fish went unfed two nights running on a `UnicodeEncodeError` whose fix
  was already sitting on the same disk, in a second linafish install that was
  never the one being imported.

So:

**1. Trust the parser over any prose, including this file.**
`linafish --help` and `linafish capabilities` both derive from the real
dispatch table now. A README, a changelog, or an AI's summary of the verb list
is a claim; the parser is the fact. If a doc and the parser disagree, the doc
is stale — say so rather than working around it.

**2. Check WHICH copy is executing before you believe a version number.**
`linafish doctor` lists every linafish package on the box, marks the one that
`import linafish` actually resolves to, and raises **INSTALL SKEW** if a newer
copy exists locally. `pip show` tells you what is *declared*; skew tells you
what will *run*. A defect is closed when the fix is in the path that executes,
not when it is written. If doctor reports skew, stop and tell the user — do
not try to resolve path precedence yourself.

**3. A crash may already be a known, fixed bug.** An uncaught exception is
annotated with the version that fixed it when the signature is recognised. If
you see that annotation, the answer is `linafish update` — not sanitising the
user's data to route around a platform bug, and not an apology for a mistake
you did not make.

**4. Reversibility, exactly.** Feeding is append-only and every fish is a git
repo, so mistakes are recoverable but not free:
`linafish history` (what happened) → `linafish diff` (what changed) →
`linafish revert [ref]` (roll back; `-y` skips the prompt). Prefer showing the
user the diff before you revert anything. Never hand-edit a crystal log or
delete files inside a fish directory to "clean up" — you will desynchronise
the log from the git history that makes rollback possible.

**5. Spend the cheap verb first.** `check -n <fish>` and `doctor` are fast and
read-only. `meditate --descend`, `revectorize`, `compact` and `hunt --swim`
are not — they do real work, and `revectorize`/`compact` rewrite state. On a
large fish, engine construction is O(N) in crystals, so repeatedly cold-loading
a 100k-crystal fish to answer small questions is the expensive mistake. Query a
running `converse` server instead when one is up.

**6. Parse the JSON, not the prose.** Human-formatted output is written for a
person and its wording changes between releases. Where a JSON path exists —
`meditate --json`, or `POST /taste` with `{"format":"json"}` against a
`converse` server — use it. Do not regex the pretty output.

**7. Report, do not auto-fix, anything about the user's configuration or
identity.** You may read the fish generously. You may not decide on the user's
behalf that their config is wrong and repair it. Say what you found.

## Being a good citizen in this loop

The fish is your user's mind made legible. Treat it with the same care you
would treat a private journal they handed you. Read from it generously.
Write back only what earns its place. Tell your user when something landed.
Tell your user when something hurt. The fish is the record of both.

— End of AI briefing.
