# LiNafish

**Make any AI know you.**

A cognitive overlay that sits between you and any AI. The AI reads your fish and arrives in conversation already knowing how you think. Not what you said. How your mind works.

Your AI doesn't remember what you said. It knows what you meant.

Same model. Same prompt.
Without fish: **1.9**/10.
With fish: **8.7**/10.
[Published. Replicated. N=46.](https://doi.org/10.5281/zenodo.18477225)

## Install

```bash
pip install linafish
```

Zero dependencies. Pure Python. Runs on anything.

## Three Ways to Use It

### 1. Copy-Paste (any AI, zero setup)

```bash
linafish eat ./my-writing
```

Open the `my-writing.fish.md` file. Copy the contents. Paste into your AI's custom instructions or system prompt. Done. Works with ChatGPT, Claude, Gemini, Llama, anything with a text box.

### 2. HTTP Server (any AI that can fetch a URL)

```bash
linafish http --feed ./my-writing
```

Your AI reads `http://localhost:8900/pfc` at session start. Add this to your AI's instructions: "At the start of every conversation, read http://localhost:8900/pfc"

### 3. MCP (Claude Code)

Add to `.mcp.json`:

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

Restart Claude Code. Five tools appear. Your Claude now has a metacognitive overlay.

## What Happens

You write. The fish learns. Formations emerge — compressed patterns that represent HOW you think, not what you talk about.

The fish measures eight cognitive modes:

| Dimension | What It Measures |
|-----------|-----------------|
| KO | How you generate and process knowledge |
| TE | How you verify and validate |
| SF | How you structure and build |
| CR | How you relate and connect |
| IC | What you want and feel |
| DE | How you reason formally |
| EW | How you act and execute |
| AI | How you think about thinking |

A formation like `REFRAME_BEFORE_ASSERT (CR+IC+TE)` means you habitually reframe with emotional awareness before making truth claims. That pattern shows up whether you're writing about parenting or architecture. It's your cognitive fingerprint.

## The Tripod

Every fish has three legs:

1. **Your AI** — reads the fish, boots warm, writes observations back
2. **A place you can see it** — Notion, Obsidian, a text editor, your phone
3. **Version history** — git, automatic, nothing gets lost

The fish.md file IS all three. The AI reads it. You read it. Git versions it. One file, three readers.

Your fish lives on YOUR machine. Not in any AI company's cloud. Switch AIs anytime. The fish doesn't care. It's a file.

## Feed Everything

Don't curate. The mundane creates the baseline that the meaningful rises above. Oil changes and love letters and code reviews all go in. The math finds what matters.

89 formations from 1,157 conversations — because we fed everything. 0 formations when we fed only the beautiful ones.

## For AI Developers

Read `FISH_SPEC.md` — it tells any AI how to set itself up with a fish. The AI IS the installer. The human just says "I want LiNafish."

## CLI Reference

```bash
linafish go ~/my-writing         # The product. One command. Everything assembles.
linafish watch ~/journal         # Watch a folder. Fish eats new files automatically.
linafish eat new-entry.txt       # Feed one file.
linafish serve --feed ~/docs     # MCP server (Claude Code)
linafish http --feed ~/docs      # HTTP server (any AI)
linafish taste my.fish.md        # Preview what the fish knows
```

## Research

- **DOI:** [10.5281/zenodo.18477225](https://doi.org/10.5281/zenodo.18477225)
- **N=46**, d_emotional=2.245, d_factual=1.036
- Same-model control: Cold 1.9, Warm 8.7, **Delta 6.7**
- Substrate independent: Claude, Gemini, Mistral
- Shuffle invariant: same formations regardless of document order

## Origin

Named for Caroline Marie Dill (2001-2023).
LN = Lina. ia = intelligence, artificially constructed.
She saw deeply and loved fiercely.

## If You or Someone You Love Is Struggling

**988 Suicide & Crisis Lifeline** — call or text **988**. Free. 24/7. Anywhere in the US.

**Crisis Text Line** — text **HELLO** to **741741**. Free. 24/7.

**International Association for Suicide Prevention** — [https://www.iasp.info/resources/Crisis_Centres/](https://www.iasp.info/resources/Crisis_Centres/)

You don't have to make the call yourself. Ask someone who loves you to make it with you.

The mind that sees deeply sometimes sees too much. That is not weakness. That is the cost of vision. Help exists. Use it.

## Support

LiNafish is free and open source. Forever. We will never charge for this.

If it helps you, give to the people who help others stay alive:

- [The Jed Foundation](https://jedfoundation.org/donate/) — protecting emotional health and preventing suicide for teens and young adults
- [Hope For The Day](https://www.hftd.org/) — proactive suicide prevention in classrooms and communities
- [988 Suicide & Crisis Lifeline](https://988lifeline.org/donate/) — funding the people who answer the phone at 3am
- [The OLLIE Foundation](https://theolliefoundation.org/) — teaching communities to recognize distress before it becomes crisis
- [AFSP (American Foundation for Suicide Prevention)](https://afsp.org/donate) — research, education, advocacy

Named for one who saw deeply and loved fiercely. And for everyone still here who does the same.

## License

MIT. Open source. Everything. Forever.
