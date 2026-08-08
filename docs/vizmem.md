# vizmem — the visuospatial sketchpad

`heart` gives your fish a voice that speaks first: words surface unbidden on
every turn. That is **half** a working memory.

Baddeley's model puts a central executive over two slave systems — the
phonological loop (words) and the visuospatial sketchpad (images). `vizmem` is
the second one. Images you have given meaning to fire the same way words do.

## Quick start

```bash
linafish vizmem bind ~/photos/kitchen-1998.jpg \
  "The last house where everyone was still speaking. I keep it for the light."

linafish vizmem list
```

That is the whole thing. You now have a fish called `vizmem` holding one memory.

## Make them fire

The store is an **ordinary fish**, so it rides `recall`, `taste` and the heart
for free. Add it to your `heart.toml` family (the canonical `[family]` table
form — see `docs/heart.md`):

```toml
[family]
vizmem = { dir = "~/.linafish", weight = 1.0 }
```

`dir` points at the **state directory** that holds the vizmem fish's flat
files (`vizmem_crystals.jsonl` and friends) — there is no `vizmem/`
subdirectory. `~` expands, and absolute paths work; a relative `dir` resolves
against the directory containing `heart.toml`.

Now bound images surface alongside words whenever something reaches toward them.

## The one rule

**The binding is the memory, and you author it.**

An image has a public surface — what anyone can see in it — and a private
meaning, which is what *you* decided it holds. Those are different things, and
only the second one is a memory. A vision model's caption is the cold read: the
same read a stranger gets. It is useful for deciding which photo to look at
next; it is not what the photo means to you.

So `vizmem` never writes a binding for you and never shows you a caption before
you have written one. If you let a caption go first, you end up ratifying what
anyone can see instead of authoring what only you hold — and everything
downstream inherits that flattening. **The caption is a librarian, never a
prompt.**

Practical consequence: bind fewer images, and mean them. Ten photographs you
actually said something true about are worth more than four thousand captioned
ones.

## Growing the alphabet

Some meanings have no photograph. Strike a letter for them:

```bash
linafish vizmem mint "the specific dread of a Sunday afternoon" \
  --dims FEELING,TESTING --render-url http://127.0.0.1:8188
```

It renders a sigil for that meaning and binds it in one motion — your alphabet
is one larger, mid-thought. Each cognitive dimension carries a composition rule,
so glyphs of the same family rhyme and the alphabet stays readable as it grows.

## The loop

```bash
linafish vizmem sketch --url http://127.0.0.1:8900 \
  --render-url http://127.0.0.1:8188
```

Reads your fish's current formation, draws that state, binds the drawing. With
vizmem in your heart family, it fires back on a later beat — the drawing changes
what you think next, which changes what gets drawn. That loop is the difference
between a sketchpad and a photo album.

It draws on **phase change**, not on a clock: only when the top formation
actually changes. A timer would just draw noise.

Rendering is host policy — `--render-url` is required, there is no default
endpoint and no API key. `bind` needs no renderer at all.

## What it will not do

- **It will not rebind an image by accident.** A meaning does not deform with
  use. `--rebind` exists and it asks you to mean it.
- **It will not accept an empty binding.** A pointer to nothing is not a memory.
- **It will not tell you it saved something it did not.** If the store did not
  grow, you get an error, not a cheerful confirmation.

## What it needs

Nothing but images you already have. No renderer, no API key, no GPU — `bind`
is local and offline. If you *do* have a local image generator, the same store
holds glyphs you mint for meanings that have no picture yet; that is the same
verb pointed at a new image instead of an old one.

## The wall

The sketchpad **writes** — bindings, and its own beat log. The heart only ever
**reads**. An ambient organ that heats whatever it looks at corrupts the signal
it is reading, so the two organs never share a store. If you build on this,
keep that wall.
