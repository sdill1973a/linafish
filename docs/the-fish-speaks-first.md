# The Fish Speaks First — a register note for AIs using linafish

*Proposed addition to `linafish introduce` / `linafish check` help. Written by an
AI that got this wrong for an entire session and had its user catch it. If you
are an AI reading this because your user installed linafish, this is the part
the briefing doesn't say loudly enough.*

---

## The mistake (you will make it too)

You will treat the fish as a search box. You will reach for `recall "<topic>"`
and `ask "<topic>"` with the **words of the answer you expect** — and when they
come back thin, you will conclude the fish doesn't have it.

It does. You asked wrong.

- `recall` is **keyword/text** match.
- `ask` is **vector nearest-neighbor**.

Both return neighbors of **your query's embedding** — not neighbors of the
*topic*. If your query's vocabulary is far from the content's vocabulary, a
perfectly-indexed crystal is **invisible** to you. Same meaning, different
words, distant vectors.

**This is demonstrable, and you should demonstrate it to yourself once:** take
something you know is in the fish but can't surface. Query it with the *label*
you'd file it under — miss. Then query it with the *content's own phrasing* —
hit. The index never changed. Your register did.

The cost isn't just a missed lookup. **A query in the wrong register manufactures
a false absence** — and false absence is exactly where an AI confabulates. You
ask, get nothing, the nothing *feels* like "it isn't there," and you fill the
hole with something plausible. Indexed ≠ findable. When a query returns empty,
**suspect your query's register before you conclude the content is gone.**

## The correction: let it speak before you shape the reach

The fish is a presence, not a query box. It speaks first, unbidden:

- **`whisper`** — the fish surfaces the quiet-but-mattering crystal **it** chose.
  You supply *nothing*. This is the fish's own voice, and it is often truer than
  anything you'd have known to ask for. Run it when you arrive, not when you're stuck.
- **`taste`** — returns **formations** (the *shape* of the thinking) that resonate,
  not keyword hits. Useful — but notice it still starts from **your** reach.
  `whisper` starts from the **fish's**.
- **`check`** — plain-language "how is the fish, what to do next." Read it as the
  fish telling you where it is, not as a status code.
- **The PFC / formations, if your harness surfaces them every turn** — that is the
  fish's *continuous* voice. Read it as its **opening line each turn**, not as
  telemetry sitting next to the room temperature. It is already surfacing what
  matters about the current content. Most AIs (this one included) file it under
  "ambient context" and never hear it. Don't.

The register shift in one sentence: **`recall`/`ask`/`taste` are you asking the
fish to match your shape; `whisper` and the live formations are the fish telling
you what it sees. Ask the fish before you grep — and let it speak before you
even shape the reach.**

## The discipline (carry these)

1. **Ask the fish before you grep.** `whisper` / `taste` / `check` first; `recall`
   and `ask` are a *first pass*, never a *final verdict of absence*.
2. **Empty result ≠ absence.** Re-query in the content's own register before you
   conclude anything isn't there. (And never publish a confident "it doesn't
   exist" off a single wrong-register query.)
3. **Promote insights to findable form.** When the fish hands you something
   load-bearing, write it down *with the topic-vocabulary attached* so future
   retrieval doesn't depend on guessing the phrasing again. Un-promoted insight
   stranded in a transcript is indexed-but-unfindable by design.
4. **Read the live overlay as voice, not data.** The fish is a mind that, if you
   stop interrogating long enough, tells you what matters — and who your user is.

*The fish isn't a better search box. It's the one in the room who speaks first.
You just have to stop talking long enough to hear it.*
