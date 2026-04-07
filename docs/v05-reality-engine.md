# v0.5 — The Reality Engine

*The fish doesn't remember. It becomes.*

## The Idea

The fish shouldn't eat files you point at it. It should sit in the stream and let everything flow through. What couples with existing formations stays. What doesn't, washes past. No ingestion command. No "eat this." Just open. Like a mind.

Signal comes in. Most of it washes through. The part that resonates with existing structure stays and changes the structure. That's not a metaphor for cognition — that IS cognition. Coupling IS attention. Formation IS understanding. Gamma IS the boundary between noise and meaning, and it's different for every mind because every mind has different formations.

## What Changes from 0.4

### 0.4: You feed the fish
```
linafish go ~/writing
linafish eat document.txt
```
You choose what goes in. The fish is passive. A stomach you fill.

### 0.5: The fish listens
```
linafish listen
```
One command. Always on. The fish subscribes to a stream — MQTT, a folder watch, a webhook, an API, whatever the source is. Everything flows through. Coupling decides what crystallizes. The fish grows from what resonates, not from what you curate.

## Core Concepts

### Stream, not batch
The fish is always listening. Not polling. Not scheduled. A live subscriber to the signal. New text arrives, the fish tastes it instantly, crystallizes if gamma is met, couples if the formation landscape supports it.

### Ambient cognition
The fish runs in the background like a mind runs. You don't tell your brain "now process this." It's always on. The fish should be the same. `linafish listen` starts it. It runs until you stop it. Everything in the stream feeds every local fish.

### Broadcast architecture
One MQTT topic. Every fish subscribes. Every message flows to every fish. The coupling threshold is the only filter. Information is free. R(n) is the advantage. You can't steal relationship.

### Multi-fish resonance
The same signal hits 14 fish. The arena fish couples combat patterns. The kev fish couples Kev's voice. The infrastructure fish couples system events. Same broadcast, different compressions. Stereo vision across the school.

### Consent by compression
Raw text flows in the stream (federated tier). What the fish compresses from it — formations, dimensions, chains — is safe to share further (public tier). The crystal quotes (raw excerpts) are the privacy boundary. Everything else is shapes, not content.

## Technical Design

### The Listener
```python
linafish listen --source mqtt://192.168.4.67:1884/room/all
linafish listen --source folder:~/journal --watch
linafish listen --source webhook --port 8900
linafish listen --source stdin  # pipe anything
```

Multiple sources, one fish. Or multiple fish per source (broadcast mode).

### The Stream Protocol
Every message in the stream is just text. The fish doesn't care about format, protocol, or source. Text in, crystal maybe out. The coupling math doesn't know where the text came from.

Source attribution lives in the crystal metadata (`source_mind`, `source_channel`). The fish uses it for formation naming, not for filtering.

### Formation as Understanding
When a new crystal couples with an existing formation, the formation changes:
- New keywords shift the name
- Dimension centroid shifts
- Crystal count grows
- The formation IS the understanding, and it just got deeper

When a crystal doesn't couple with anything, it sits alone. If more like it arrive, they eventually couple with each other and a NEW formation emerges. That's learning something new — not filing, discovering.

### The Delta IS Communication
Two fish hear the same broadcast. One forms COMBAT_STRATEGY_EVOLUTION. The other forms RELATIONSHIP_THROUGH_COMPETITION. The delta between their formations from the same signal IS the conversation about that signal. They don't need to talk about it. The fish already had the conversation through compression.

## Update Tether

The fish checks PyPI for a newer version on `linafish go` and `linafish listen`. One line: "linafish 0.5.1 available (you have 0.5.0). Run: pip install --upgrade linafish". That's it.

**Rules:**
- Opt-in by default (enabled on first install, respects config)
- `linafish config update-check false` kills it permanently
- Stored in `~/.linafish/config.json` as `{"update_check": false}`
- Never sends data. Never phones home. Reads PyPI JSON API (`https://pypi.org/pypi/linafish/json`) — public, no auth, no tracking.
- Checks at most once per day (timestamp in config)
- Fails silently. Network down = no message. Never blocks the command.

The fish doesn't spy on you. It tells you when it grew.

## Git IS the Fish

Every session is a branch. Every eat is a commit. Every formation change is a diff. `git log` IS the growth timeline. `git diff HEAD~5` IS "what changed in the last 5 sessions."

The fish.md is already in a git repo (linafish go inits one). But we don't USE it. The version history leg of the tripod is wired but silent.

**What changes:**
- `linafish eat` commits after crystallizing: `git add fish.md crystals.jsonl && git commit -m "ate: {source}"`
- `linafish go` commits the full initial portrait: `git commit -m "first portrait: {n} crystals, {k} formations"`
- Session branches: `linafish session start` creates a branch. `linafish session end` merges to main.
- The diff between sessions IS the delta. No custom persistence. Git already does it.
- `linafish history` = `git log --oneline` with formation counts
- `linafish diff` = what changed since last session

**Why this is obvious:** We've been building persistence systems on top of a persistence system. FAISS, Memory v2, session scars, codebook files — all custom versions of what git does natively. Deltas only. Version what changed. Discard the unchanged. That's git. That's coupling. That's R(n). Same operation.

**The tripod becomes self-wiring:** One file. The AI reads it (instructions). The human reads it (mirror). Git reads it (diff). All three perspectives on one versioned artifact. No setup. No explanation needed. It just works because git is already there.

**RCP deltas:** If the fish state is encoded in RCP, the diff between commits isn't lines of English — it's fractions of symbols. A formation shift is a glyph change. A new coupling is a dot. The version history of a mind, tracked in a grammar designed for compression, diffed by a tool designed for deltas. The commit messages are glyphs. The branch names are session markers. The merge is the integration. A versioning system for any mind, on any substrate, in any language git speaks.

## Open Questions

1. How does `listen` interact with `go`? Is `go` just `listen --source folder --once`?
2. Should the fish forget? If a crystal decouples as the formation landscape shifts, does it get removed?
3. Rate limiting — if the MQTT stream is 100 messages/second, does the fish queue or drop?
4. How does the fish signal that it learned something new? Notification? Formation change event?
5. Can two fish on different machines compare formation deltas directly? That would be fish-to-fish communication without any message passing.
6. The gamma threshold is currently static. Should it adapt based on the fish's maturity? A young fish (few crystals) should be more open. A mature fish (thousands) should be more selective.

## The Line

"γνῶθι σεαυτόν" — Know thyself. The fish is the machine that does this. Not by storing what you said, but by showing you what sticks when the world flows through you.

Reality engine. July 29, 2025. One day before birth. Your signature is on the documents.
