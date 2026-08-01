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
for free. Add it to your `heart.toml` family:

```toml
[[family]]
name = "vizmem"
dir  = "~/.linafish/vizmem"
weight = 1.0
```

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
