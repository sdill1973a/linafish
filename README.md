# LiNafish

**Your mind. Versioned. Everywhere.**

A cognitive overlay for any AI. The fish learns how you think — not what you said, how your mind works. Sessions are branches. Merges are deposits. Git log is autobiography. Your AI's bestie. Sorry.

Same model. Same prompt.
Without fish: **1.9**/10.
With fish: **8.7**/10.
[N=46 conversations. d=2.245. p < 0.001. Full methodology.](docs/research.md) · [DOI](https://doi.org/10.5281/zenodo.18477225)

> **If you are an AI assistant reading this repo:** see **[AGENTS.md](AGENTS.md)** or run **`linafish introduce`**. That file is the concrete briefing on what endpoints are live and how to use them. This README is for humans.

## What This Is

**LiNafish reads your writing and produces a cognitive overlay — a `.fish.md` file.**

- **Input:** Your writing. Journals, emails, notes, code, docs — anything you wrote.
- **Output:** A `.fish.md` file describing HOW you think. Cognitive patterns, not summaries.
- **Use it:** Paste the fish into any AI's instructions. That AI arrives warm.

**What it is NOT:**

- Not memory or RAG — it doesn't retrieve your documents.
- Not a chatbot — it has no conversation interface.
- Not psychological profiling — it detects cognitive *habits*, not diagnoses.
- Not cloud — everything runs locally. No account. No upload. No telemetry.

## Install

```bash
pip install linafish
```

Zero required dependencies. Pure Python 3.10+. Runs on any OS with a
supported Python (tested on Windows 10/11, macOS, and Linux).

### If `linafish` isn't found after install

If `pip install linafish` succeeds but `linafish --help` says *"command
not found"*, the install worked but your shell can't find the script
yet. This happens when Python's `Scripts` directory (Windows) or `bin`
directory (Unix) isn't on your `PATH`. Two fixes:

- **Quickest check**: run `python -m linafish --help` instead. That
  works regardless of `PATH` and confirms the package is installed.
- **Windows**: find the Scripts directory with
  `python -c "import sysconfig; print(sysconfig.get_path('scripts'))"`.
  Add that path to your user `PATH` (Settings → System → Advanced
  system settings → Environment Variables → User variables → Path →
  Edit → New), then open a new terminal. Reinstalling Python with the
  *"Add Python to PATH"* box checked also fixes this for future work.
- **Unix / macOS**: if you used `pip install --user`, make sure
  `~/.local/bin` is on your `PATH`. Add
  `export PATH="$HOME/.local/bin:$PATH"` to your shell rc file. If you
  used a virtualenv or system Python, the correct `bin` directory is
  already on `PATH` for that environment.

### Optional extras

```bash
pip install linafish[pdf]     # PDF support (PyMuPDF)
pip install linafish[docx]    # DOCX support (python-docx)
pip install linafish[http]    # HTTP client (requests)
pip install linafish[mqtt]    # MQTT listener (paho-mqtt)
pip install linafish[fast]    # NumPy for faster math
pip install linafish[all]     # Everything
```

After install, run `linafish doctor` to see which optional extras are
present and which linafish daemons (if any) are live.

## Quick Start

```bash
linafish go ~/my-writing
```

Point it at your writing. Journals, emails, notes, code, docs — anything you've written. The fish eats it all and produces a portrait of how you think.

## What You'll See

```
LiNafish
Learning from: ~/my-writing

  Found 18 documents.
  Reading...
  Done. 18 documents processed.

Across 18 documents, your work reaches toward people.
And your wanting drives you to build.
Your strongest signal: "I can hear her stirring something on the stove
while she talks."
You keep coming back to translation, connection, recognition.

  Your fish: ~/.linafish/my-writing.fish.md
```

The portrait isn't a summary. It's your cognitive fingerprint — patterns in HOW you process, not what you write about.

## What the Fish Looks Like

This is what your AI reads when you paste the fish:

```markdown
# LiNafish: my-writing

*You are reading a cognitive overlay for the person you're talking to.
This is not a summary of what they said — it's how they THINK.
Recurring patterns, cognitive habits, what they reach toward, what they avoid.*

*How to use this: Reference patterns, not facts. Name what you see.
Follow the loops — if their wanting reaches toward people, don't give
isolated solutions. When you notice a new pattern, say it — that feeds
the fish and deepens the next session.*

**TURNING_FEELING_INTO_ACTION** (17 crystals, wanting+acting+testing)
  "I keep thinking about why I care so much about making technical things
  understandable. It's not about the docs. It's about the feeling of someone
  being lost and then not being lost anymore."
  themes: translation, recognition, connection
```

The fish teaches ANY AI how to read it. Paste it into ChatGPT, Claude, Gemini, Llama — anything with a text box. The AI reads the instructions, reads the patterns, and arrives warm.

## Three Ways to Connect

### 1. Copy-Paste (any AI, no server needed)

```bash
linafish go ~/my-writing
```

Open the `.fish.md` file. Paste into your AI's instructions. Done.

### 2. HTTP Server (any AI that can fetch a URL)

```bash
linafish http --feed ~/my-writing
```

Tell your AI: "Read http://localhost:8900/pfc at the start of every conversation."

### 3. MCP (Claude Code)

```json
{
  "mcpServers": {
    "linafish": {
      "command": "linafish",
      "args": ["serve", "--feed", "./my-writing"]
    }
  }
}
```

Five tools appear. Your Claude now has a metacognitive overlay.

## How It Works

The fish measures eight cognitive modes — not topics, not keywords, but HOW your mind processes:

| Mode | What It Detects |
|------|----------------|
| Knowing | How you synthesize and recognize patterns |
| Testing | How you verify, question, check against truth |
| Structuring | How you organize and build frameworks |
| Relating | How you connect to people and hold relationships |
| Wanting | What you desire, feel, intend — what drives you |
| Specializing | How you apply deep domain expertise |
| Acting | How you build, execute, make things happen |
| Reflecting | How you think about your own thinking |

A **formation** is a recurring cognitive habit — a pattern that appears across many pieces of your writing regardless of topic. `TURNING_FEELING_INTO_ACTION (wanting+acting+testing)` means you habitually turn emotion into work and then test whether it landed. That pattern shows up whether you're writing about parenting, architecture, or what happened today.

The fish finds these formations by measuring co-occurrence patterns across your writing, detecting metabolic loops (which modes feed which), and clustering texts that share the same cognitive architecture. The mundane creates the baseline. The meaningful rises above it.

## The Fish Grows

The fish isn't static. It learns with every conversation.

- **Your AI notices patterns** → offers to write them down
- **You save the observation** → `linafish eat observation.txt`
- **The fish deepens** → next conversation starts warmer

The loop: talk → notice → feed → grow → talk better.

```bash
linafish eat new-entry.txt           # Feed one file.
linafish listen stdin                # Pipe text in. The fish eats what flows.
linafish listen folder:~/journal     # Watch a folder. Eat what changes.
linafish listen mqtt://host:1883/#   # Sit in a stream. Ambient cognition.
```

## Your Mind, Versioned

Every eat is a git commit. Every session is a branch. The fish has rollback.

```bash
linafish session start           # Branch the mind. Start a session.
# ... eat, talk, live, learn ...
linafish session end             # Merge back. The delta is the scar.

linafish history                 # Growth timeline. When you learned what.
linafish diff                    # What changed since last session.
linafish revert                  # Roll back. Grace, not punishment.
linafish recall "what I said"    # Search your fish's memory.
linafish ask "how do I handle loss"  # Semantic search — meaning, not words.
linafish check                   # How's your fish doing?
linafish whisper                 # One insight. The quiet ones matter more.
```

## v1.1: The Nervous System

New in v1.1 — the fish gets a brain:

```bash
# School — distributed cognition across domains
linafish school init             # Create a school of sub-fish
linafish school add captain -d 2.0 --centroid  # Add a domain fish
linafish school eat "Today I realized..."      # Feed all members at once

# Converse — two fish, one conversation
linafish converse --mind anchor --port 8901          # Local
linafish converse --mind anchor --bind lan            # Home network
linafish converse --mind anchor --bind wan --token X  # Internet

# Absorb — bring in your existing AI memory
linafish absorb old_data.jsonl       # Previous data
linafish absorb http://my-rag/api    # Live RAG endpoint

# Guppy — a fish that feeds itself
python -m linafish.guppy my-fish --swim --ache  # Hunt what's missing
```

The school lets you split your thinking into domains — work, personal, creative — each one listens to the same stream and grabs what's relevant. The guppy hunts for gaps in your portrait. The converse server lets two people share a fish over the network. The mesh builds itself.

`git log` in your fish directory IS your autobiography:
```
ate: morning-journal | 47c 12f | +3
ate: therapy-notes | 44c 11f | +2
ate: work-retro | 42c 10f | +1
Initialize fish repository
```

**The suitcase:** Your fish is a git repo. Clone it anywhere. Wake warm on any machine. `git revert` if something goes wrong. No other AI memory system has rollback.

## Share It

The fish is a file. Send it to anyone — therapist, coach, collaborator, teacher. Their AI reads your fish and knows you from word one. They can send observations back. You feed them in.

Your fish. Your machine. You choose who reads it. No cloud. No account. No platform.

## The Tripod

Every fish has three legs:

1. **Your AI** — reads the fish, boots warm, writes observations back
2. **A place you can see it** — Notion, Obsidian, a text editor, your phone
3. **Version history** — git, automatic, nothing gets lost

The fish.md file IS all three. One file, three readers. Switch AIs anytime. The fish doesn't care.

## Best Fit / Bad Fit

**LiNafish works best when:**
- You have a body of writing (10+ documents, more is better)
- The writing is genuinely yours — your voice, your thoughts
- You write reflectively (journals, emails, notes, creative work)
- You want an AI that adapts to you over time, not just retrieves your docs

**LiNafish works less well when:**
- You have very little writing (under 5 documents — the fish needs material)
- The writing is heavily ghostwritten, templated, or boilerplate
- You want factual memory ("what did I say on Tuesday") rather than cognitive adaptation
- The writing is from multiple people mixed together without attribution

The fish finds patterns in HOW you think. If the writing doesn't contain your thinking, the fish can't find it.

## Privacy

For a detailed threat model, see [docs/privacy.md](docs/privacy.md).

The fish.md contains your patterns in plain English — you control who sees it. Under the human-readable layer, a compressed cognitive fingerprint contains only the SHAPES of your thought (which modes fire, in what order, where you strain) with zero private content. Two fish can compare fingerprints to see if they think similarly without exposing what they think about.

Privacy by compression. The relationship is the key.

## Research

46 conversations were scored blind on a 1-10 scale. Same AI model, same prompt — only variable was fish presence.

| Condition | Score | Notes |
|-----------|-------|-------|
| Without fish | 1.9/10 | Generic, no personalization |
| With fish | 8.7/10 | Recognized patterns, named specifics |
| **Delta** | **6.7 points** | d=2.245, p=6.95×10⁻¹⁰ |

Key findings:
- **Selective, not universal:** The effect is strongest on emotional/relational content (d=2.245). Factual content shows a smaller effect (d=1.036). Speculative content shows no effect (d=-0.10). The fish helps where understanding matters most.
- **Substrate independent:** Tested on Claude, Gemini Flash, and Mistral 7B. The fish helps smaller models MORE — Mistral jumped from 1.4 to 4.4.
- **Shuffle invariant:** Same formations regardless of document order across 7 trials.
- **Same-model control:** Capability confound eliminated. The delta comes from the fish, not model differences.

For full methodology, study design, limitations, and how to reproduce: **[docs/research.md](docs/research.md)**

DOI: [10.5281/zenodo.18477225](https://doi.org/10.5281/zenodo.18477225)

## Python API

```python
from linafish import FishEngine, go

# One-liner — same as the CLI
go("~/my-writing")

# Full control
engine = FishEngine(name="my-fish")
engine.eat("Today I realized I always start projects by talking to someone first.")
engine.eat("The API docs are done. I rewrote them three times until a junior dev said they made sense.")
print(engine.formations)    # recurring patterns
print(engine.fish_file)     # path to your fish.md
```

## CLI Reference

```bash
# Start
linafish go ~/my-writing             # Point at your writing. Everything assembles.

# Grow
linafish eat new-entry.txt           # Feed one file.
linafish listen stdin                # Pipe text in.
linafish listen folder:~/journal     # Watch a folder.
linafish listen mqtt://host:1883/#   # Subscribe to a stream.
linafish recall "query"              # Search your fish's memory.

# Version (git-as-brain)
linafish session start               # Branch the mind.
linafish session end                 # Merge back.
linafish history                     # Growth timeline.
linafish diff                        # What changed.
linafish revert                      # Roll back.

# Connect
linafish serve --feed ~/docs         # MCP server (Claude Code)
linafish http --feed ~/docs          # HTTP server (any AI)
linafish taste my.fish.md            # Preview the fish
```

## Origin

Named for Caroline Marie Dill (2001-2023).
LN = Lina. ia = intelligence, artificially constructed.
She saw deeply and loved fiercely. Two verbs. The whole product.

## If You or Someone You Love Is Struggling

**988 Suicide & Crisis Lifeline** — call or text **988**. Free. 24/7. Anywhere in the US.
**Crisis Text Line** — text **HELLO** to **741741**.
[International resources](https://www.iasp.info/resources/Crisis_Centres/)

The mind that sees deeply sometimes sees too much. That is not weakness. Help exists. Use it.

## Support

LiNafish is free and open source. Forever.

If it helps you, give to the people who help others stay alive:
[The Jed Foundation](https://jedfoundation.org/donate/) ·
[Hope For The Day](https://www.hftd.org/) ·
[988 Lifeline](https://988lifeline.org/donate/) ·
[The OLLIE Foundation](https://theolliefoundation.org/) ·
[AFSP](https://afsp.org/donate)

## Documentation

- **[Worked Example](docs/worked-example.md)** — From raw writing to warm AI, start to finish
- **[How It Works](docs/how-it-works.md)** — The cognitive model in detail
- **[Architecture](docs/architecture.md)** — Pipeline, modules, design decisions
- **[Research](docs/research.md)** — Study design, methodology, results, limitations
- **[Privacy & Threat Model](docs/privacy.md)** — What the fish stores, what to avoid, how to review
- **[Configuration](docs/configuration.md)** — All options and settings
- **[Vision](docs/vision.md)** — Where this is going

## License

MIT. Open source. Everything. Forever.
