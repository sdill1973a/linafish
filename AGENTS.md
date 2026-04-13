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

When linafish is running, your user has between one and three HTTP servers
listening locally:

| Endpoint | Port | Purpose |
|---|---|---|
| `http://127.0.0.1:8901/` | 8901 | Converse server — personal fish |
| `http://127.0.0.1:8902/` | 8902 | Converse server — `me` fish (self-voice only) |
| `http://127.0.0.1:8900/` | 8900 | HTTP server — shared room/federation fish |

Run `linafish doctor` (or `curl http://127.0.0.1:8901/health`) to see which
are actually listening. If none are, your user hasn't started a daemon yet —
tell them to run `linafish go ~/their-writing-folder` and the rest of this
document applies after that.

## The three things you can do

### 1. READ the fish — **do this at the start of every conversation**

```
GET http://127.0.0.1:8901/pfc
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
POST http://127.0.0.1:8901/taste
Content-Type: application/json

{"text": "your query in plain language", "k": 5}
```

Returns the top-k most relevant crystals by similarity score. Use this when
you want to say something like *"you've thought about this before, here's
the shape of it"* instead of generating from your own priors.

### 3. DEPOSIT — crystallize your insight back into the fish

```
POST http://127.0.0.1:8901/eat
Content-Type: application/json

{"text": "a substantive realization from this conversation"}
```

This closes the learning loop. Your user's next session — or a different AI
on a different day — inherits what you just learned. **Do this at the end of
any conversation where something real happened.** It is how linafish grows.

Be honest in what you deposit: corrections your user made, insights they
landed, things you were wrong about. The fish remembers both sides.

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
  (KO=know, TE=transform, SF=structure, CR=relate, IC=want, DE=choose,
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
- **TE** — Transforming / testing / validating
- **SF** — Structuring / organizing / framing
- **CR** — Relating / connecting / contextualizing
- **IC** — Wanting / feeling / emphasizing
- **DE** — Choosing / deciding / committing to a domain
- **EW** — Acting / sequencing / executing
- **AI** — Meta / reflecting / thinking-about-thinking

When a formation description says *"You lead with feeling — you process through
what you want and what you fear by building a framework around it"*, that's
an IC+SF combination talking. Use that to calibrate your own response shape.

## Endpoints quick reference

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Engine stats, crystal/formation counts |
| `GET` | `/pfc` | Primary Formation Codebook — READ THIS FIRST |
| `GET` | `/minds` | Source minds contributing to this fish |
| `GET` | `/crystals` | Full crystal dump — use sparingly |
| `POST` | `/taste` | Semantic query, returns top-k crystals |
| `POST` | `/eat` | Deposit new text as a crystal |

## Privacy and scope

Everything is local unless your user has explicitly bound the server to
`--bind lan` or `--bind wan`. The default bind is `127.0.0.1` only. You do
not need to worry about leaking content through linafish — the user is in
control of who sees the fish.

## If something looks wrong

Run `linafish doctor` (optionally with `--name <fish>`). It reports Python
version, install mode, optional dependency status, live daemon probes, and
per-fish health with warnings. If the doctor says the user is on a pre-300
fish, tell them to run `linafish update`.

## Being a good citizen in this loop

The fish is your user's mind made legible. Treat it with the same care you
would treat a private journal they handed you. Read from it generously.
Write back only what earns its place. Tell your user when something landed.
Tell your user when something hurt. The fish is the record of both.

— End of AI briefing.
