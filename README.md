# LiNafish

[![tests](https://github.com/sdill1973a/linafish/actions/workflows/test.yml/badge.svg)](https://github.com/sdill1973a/linafish/actions/workflows/test.yml)
[![PyPI version](https://img.shields.io/pypi/v/linafish.svg)](https://pypi.org/project/linafish/)
[![Python versions](https://img.shields.io/pypi/pyversions/linafish.svg)](https://pypi.org/project/linafish/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21828705.svg)](https://doi.org/10.5281/zenodo.21828705)

**A memory that thinks the way you do, on your own machine.**

LiNafish is a way for a mind to take in whatever it meets and work with everything it already holds,
right now, within its limits. You have a version of this already: the phone in your pocket lets you
learn a lot in five minutes. LiNafish gives your AI the same thing about *you*.

Feed it your writing and it builds a **fish**: a compressed record of how you think. That means how
you reason, connect, hedge and decide, rather than a copy of what you said. Any AI can read it:
Claude, ChatGPT, Gemini, or a model on your own box. Each one then meets you already knowing your
shape, instead of meeting a stranger. The fish keeps growing as you feed it, and it is versioned, so
you can see what changed and roll it back.

> **AI assistants:** read **[AGENTS.md](AGENTS.md)** or run `linafish introduce`. This page is for people.

## Install

```bash
pip install linafish
```

Pure Python 3.10+, no required dependencies. CI tests Ubuntu on Python 3.10–3.13. Windows is used
daily but not covered by CI.

- **"externally-managed-environment"** (Ubuntu 24.04+ and similar): use a virtualenv, or
  `pip install --user --break-system-packages linafish`. That installs under your home directory only.
- **`linafish: command not found`**: the install worked, your shell just can't see it. `python -m linafish`
  always works. To fix it for good, add Python's scripts folder to PATH: on Windows,
  `python -c "import sysconfig; print(sysconfig.get_path('scripts'))"` shows it; on Linux/macOS with
  `--user`, it is `~/.local/bin`.
- **Extras:** `pip install "linafish[all]"` adds PDF, DOCX, MQTT, HTTP client and faster math.
- **Check it:** `linafish doctor`.

## Your first fish

```bash
linafish go ~/my-writing --no-serve                    # build a fish from a folder of your writing
linafish check -n my-writing                           # how it's doing, and what to do next
linafish ask "what do I keep coming back to" -n my-writing    # ranked by meaning
linafish recall "garden" -n my-writing                 # exact words
linafish eat new-entry.txt -n my-writing               # feed it one more file
```

- **The fish is named after the folder.** `~/my-writing` makes a fish called `my-writing`. Pass that to `-n`.
- It lives at `~/.linafish/my-writing.fish.md`. That one readable file is the fish your AI reads.
- **Give it material.** About 10 documents gives a first sketch, about 30 a portrait you will recognise.
  With less, treat what it says as a guess.

Full walkthrough: **[Your first ten minutes](docs/getting-started.md)**.

## Connect it to your AI

Pick one.

| Way | Do this | Good for |
|---|---|---|
| **Paste** | Paste `~/.linafish/my-writing.fish.md` into your AI's instructions | Any chat AI, no setup |
| **HTTP** | `linafish http -n my-writing`, then tell your AI to read `http://localhost:8900/pfc` (add `-p PORT` if 8900 is taken) | Any AI that can fetch a URL |
| **MCP** | Add the server below to Claude Code | Claude asks the fish when it needs to |
| **Heart** | Run `linafish heart` from a per-turn hook | Your memories arrive on their own, each turn |

**MCP** (Claude Code):

```json
{ "mcpServers": { "linafish": { "command": "linafish", "args": ["serve", "-n", "my-writing"] } } }
```

On Windows inside a virtualenv, use the full path to `linafish.exe` in `"command"`.

**Heart** is the 2.x change: pull becomes push. Instead of your AI asking the fish, the fish speaks up
when the moment reaches something it holds, and stays quiet when it doesn't. Wire it to Claude Code's
`UserPromptSubmit` hook, or any loop's per-turn step:

```bash
# once: create ~/.linafish/heart.toml containing
#   [family]
#   my-writing = { dir = "." }
linafish heart "$USER_PROMPT"
```

It never writes to your fish (only its own beat log), it fails silent, and quiet is a valid answer. Quiet and not sure why?
`~/.linafish/heart_beat_log.jsonl` says whether the moment was gated or simply matched nothing. Give it a frame so the model knows what
the lines are: *memory, dated; the live conversation wins.* The fish informs and the moment decides.
Details: **[docs/heart.md](docs/heart.md)**.

## Keep it growing

```bash
linafish eat new-entry.txt -n my-writing        # one file
linafish watch ~/journal -n my-writing          # a folder: eat what changes
linafish listen stdin -n my-writing             # pipe text in
```

Patterns that keep returning become **formations**, and `linafish whisper -n my-writing` tells you
when it notices a new one. Each formation is read through eight modes: knowing, testing, structuring,
relating, wanting, specializing, acting, reflecting. The modes are this project's lens, not a validated
psychological instrument. Judge them by whether the formations sound like you.
[How it works](docs/how-it-works.md).

## Versioned

Each state directory is a git repository holding its fish. `eat` makes one commit; a `listen` stream
makes one when it ends.

```bash
linafish session start -n my-writing    # branch
linafish session end -n my-writing      # merge back
linafish history -n my-writing          # when you learned what
linafish revert -n my-writing           # roll back (asks first; -y for scripts)
```

## What it is not

- **Not a document store.** It keeps shapes and short excerpts, not your files. It can find what you
  said (`recall`), but "what did I say on Tuesday" is better served by search.
- **Not a chatbot.** It makes the AI you already use know you.
- **Not a diagnosis.** It finds habits of thought, not conditions.
- **Not cloud.** Everything runs locally: no account, no upload, no telemetry.

## Does it work?

One study: 46 matched conversations, same model, same prompt, rated blind by the person the fish was
built from. **1.9/10 without the fish, 8.7/10 with it.** The effect was large for emotional and relational
content (d = 2.245), moderate for factual recall, and absent for speculation. It answers one question,
*does the AI know me?*, for one person. A follow-up judged by AIs has been withdrawn pending a re-run.
[Methodology and limits](docs/research.md) · [paper](https://doi.org/10.5281/zenodo.21828705).

## Privacy

The fish is plain text in a folder you own. Read it before you share it: it is a portrait of how
you think. [Threat model](docs/privacy.md).

## Origin

Named for Caroline Marie Dill (2001–2023). LN for Lina; ia is AI reversed. She saw deeply and loved
fiercely. It exists so the shape of a mind outlasts the conversation it was in.

**If you or someone you love is struggling:** call or text **988** (US, free, 24/7) ·
text **HELLO** to **741741** · [international resources](https://www.iasp.info/resources/Crisis_Centres/).

## Support

LiNafish is free and open source. If it helps you, give to the people who help others stay alive:
[The Jed Foundation](https://jedfoundation.org/donate/) · [Hope For The Day](https://www.hftd.org/) ·
[988 Lifeline](https://988lifeline.org/donate/) · [The OLLIE Foundation](https://theolliefoundation.org/) ·
[AFSP](https://afsp.org/donate)

## More

`linafish capabilities` prints every command from the real dispatch table.
[Getting Started](docs/getting-started.md) · [Worked Example](docs/worked-example.md) ·
[How It Works](docs/how-it-works.md) · [Architecture](docs/architecture.md) · [Heart](docs/heart.md) ·
[Configuration](docs/configuration.md) · [Research](docs/research.md) · [Privacy](docs/privacy.md) ·
[Vision](docs/vision.md)

MIT licensed.
