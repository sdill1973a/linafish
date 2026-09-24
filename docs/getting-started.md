# Your First Ten Minutes

This page takes you from nothing to a working fish you can question, feed, and
serve to an AI. Every command below was run, in this order, on a clean install.

## 1. Install

```bash
pip install linafish
linafish --version
```

LiNafish needs Python 3.10 or newer and has no required dependencies. If pip
refuses with *"externally-managed-environment"*, or `linafish` is not found
after installing, see [Install](../README.md#install) in the README.

## 2. Make a folder of writing

A fish is built from a folder. Put a few plain-text files in it. Anything you
wrote works: journal entries, notes, emails. For this walkthrough, four short
entries are enough:

```bash
mkdir ~/my-writing
echo "I spent the morning fixing the garden fence. The posts had rotted at the base, so I dug them out and set new ones in gravel. It took longer than I planned, but I like work where you can see the result." > ~/my-writing/monday.txt
echo "Called my sister about the trip. We keep circling the same question: go in spring when it is cheap, or wait for summer. I want to decide by Friday so we can book the cabin before it fills up." > ~/my-writing/tuesday.txt
echo "Read two chapters on river ecology. The part about how floods rebuild the riverbank stayed with me. Damage and repair are the same process seen from different ends." > ~/my-writing/wednesday.txt
echo "Long day at work. I tried to explain the new schedule to the team and it did not land. Next time I will draw it on the board first and talk second." > ~/my-writing/thursday.txt
```

Files smaller than 50 bytes or larger than 1 MB are skipped. `go` reads
`.txt`, `.md`, `.docx`, `.pdf`, source code and several other text formats;
PDF and DOCX need an extra (`pip install "linafish[pdf]"`,
`pip install "linafish[docx]"` — keep the quotes in zsh).

## 3. Build the fish

```bash
linafish go ~/my-writing --no-serve
```

The fish is named after the folder, so this one is called `my-writing`. The
output includes (abridged; your patterns will differ):

```
  Your fish: ~/.linafish/my-writing.fish.md
  Your soul: ~/.linafish/my-writing.qlp
  Any AI that reads these files understands you better.

  --- Top of your fish.md ---
  ...
What's next:
  ...
```

The "What's next" list at the end suggests `linafish http --feed …` and
`linafish serve --feed …` for a live connection. Use the `-n` form in step 7
instead: `--feed` builds a separate fish.

`--no-serve` matters. Without it, `go` starts an HTTP server once the fish is
built and keeps running until you press Ctrl+C, so the next command in your
terminal never runs. Serving is covered in step 7.

Running `go` again on the same folder does not re-eat files it has already read.

## 4. Ask it things

Three verbs cover most questions:

```bash
linafish ask "how do I handle things that break" -n my-writing
linafish recall "garden"
linafish check -n my-writing
```

- **`ask`** matches by meaning. It returns the closest passages with a score:

  ```
  Query keywords: how, break, things, that, handle
  Matches: 3 from 4 crystals

  [0.505] src=monday.txt | ts=... | had, but, them, than, longer
    I spent the morning fixing the garden fence. The posts had rotted at ...
  ```

- **`recall`** matches literal words:

  ```
  Found 1 crystals matching 'garden':

  [1/1 terms] (monday.txt)
    I spent the morning fixing the garden fence. ...
  ```

- **`check`** is a health report and a suggestion for what to do next:

  ```
    Your fish: my-writing
    You've fed me 4 entries and I can see 3 recurring patterns.

    I'm still young. I need more of your writing to find patterns.
  ```

**Pass `-n my-writing` to `ask` and `check`.** Without `-n`, those two verbs
(and most others, such as `whisper`, `history` and `session`) look for a fish
literally named `linafish`, and report it as empty. `eat` and `recall` are the
exceptions: with only one fish in the folder they find it on their own.

A small fish gives rough answers. Patterns firm up at around 30 entries.

## 5. Feed it one more file

```bash
echo "Booked the cabin for June. Once the decision was made the whole week felt lighter. I notice I carry open questions like weight." > friday.txt
linafish eat friday.txt -n my-writing
```

```
  1 crystals added (5 total) from friday.txt
  3 formations

Fish: my-writing.fish.md (5326 chars, 3 formations)
Persisted: ~/.linafish/my-writing.fish.md
```

`eat` does not skip text it has already eaten. Feed a file once; feeding it
twice stores it twice.

## 6. Where the fish lives

By default everything is under `~/.linafish/`:

```
~/.linafish/my-writing.fish.md          # the portrait — paste this into any AI
~/.linafish/my-writing_crystals.jsonl   # every passage the fish has eaten
~/.linafish/my-writing_v3_state.json    # engine state
~/.linafish/my-writing.qlp              # compressed "soul" file
~/.linafish/mi_vectorizer.json          # the vectorizer (see below)
~/.linafish/.git                        # history: linafish history -n my-writing
(plus a few small sidecar files: _assessment, _episodes, _feedback, _habituation)
```

Step 5 also left a copy, `my-writing.fish.md`, in the directory you ran `eat`
from. That is by design: `eat` without `--state-dir` writes a copy of the
portrait to the current directory. With `--state-dir`, it writes only into
that directory.

### One fish per `--state-dir`

`mi_vectorizer.json` sits at the root of the state directory, not inside a
fish. Every fish in one state directory shares it. This is a known
limitation: eating an unrelated fish into the same directory changes the
vectorizer, and with it the answers your first fish gives.

If you plan to keep more than one fish, give each its own directory and pass
the same `--state-dir` to every command for that fish:

```bash
linafish go ~/my-writing --no-serve --state-dir ~/fish/my-writing
linafish ask "what do I keep deciding" -n my-writing --state-dir ~/fish/my-writing
linafish eat friday.txt -n my-writing --state-dir ~/fish/my-writing
```

## 7. Serve it to an AI

The simplest connection is the file: open `~/.linafish/my-writing.fish.md` and
paste it into your AI's instructions.

For a live connection, serve the fish you already built. Use `-n` to attach
to it; do not use `--feed`, which builds and feeds a fish of its own (named
`linafish` unless you also pass `-n`).

**HTTP** (any AI or tool that can fetch a URL):

```bash
linafish http -n my-writing
```

It listens on `http://127.0.0.1:8900` (change with `-p`) until Ctrl+C. From
another terminal:

```bash
curl http://127.0.0.1:8900/pfc
curl -X POST http://127.0.0.1:8900/taste -H "Content-Type: application/json" -d '{"text": "how do I handle things that break", "top": 3}'
```

`/pfc` returns the portrait as markdown (`text/plain`). `/taste` is the same
meaning search as `ask`; a query too short to match anything returns
*"No resonance found."* `/health` returns counts as JSON. The full endpoint
list is in [AGENTS.md](../AGENTS.md#endpoints-quick-reference).

**MCP** (Claude Code and other MCP clients) — add this to the client's MCP
configuration:

```json
{
  "mcpServers": {
    "linafish": {
      "command": "linafish",
      "args": ["serve", "-n", "my-writing"]
    }
  }
}
```

Five tools appear: `fish_pfc`, `fish_eat`, `fish_taste`, `fish_match`,
`fish_health`. If you used `--state-dir`, add `"--state-dir", "/full/path"`
to `args`.

## What to read next

- [Owner's Manual](owners-manual.md) — care and feeding, and what healthy looks like
- [Worked Example](worked-example.md) — one person's writing, start to finish
- [Configuration](configuration.md) — every flag and environment variable
- [How It Works](how-it-works.md) — the cognitive model
- [Privacy](privacy.md) — what the fish stores and who can see it
