# The Afferent School Organ (`linafish.afferent`)

A Pi-cheap router that, given a prompt, names which member of a fish *school* is
relevant — so an agent can surface that specialist's knowledge into its context
each turn. If a school is a set of topic-scoped subfish, the afferent organ is
the nervous system that routes attention to the right one.

## The hard constraint: not CPU-gated

The per-turn path does **no heavy compute** — no recall, no model encode, no GPU,
no re-vectorize. A topic fingerprint per member is **precomputed once** into an
index; per-turn routing is a sub-millisecond in-memory dict lookup. The organ is
designed to run on a solar Pi. The expensive step (building the index) is a rare,
deliberate, offline operation.

## Routing: always curated (supplied or auto-derived)

Per-turn routing counts keyword hits against each member's interest map — it
does **not** sum TF-IDF frequency magnitude (which is not comparable across
members of different corpus sizes: a small member's incidental word outweighs a
large member's on-topic word — measured, `qlp_grammar`/113 crystals beat a
`sister`/10073-crystal fish on "sister"). Two ways the map is obtained:

### Supplied (best)

Drop an `afferent_topics.json` in the school dir:

```json
{
  "billing": ["invoice", "payment", "charge", "refund", "stripe", "webhook"],
  "auth":    ["login", "oauth", "token", "session", "jwt", "signup"],
  "infra":   ["server", "port", "deploy", "kubernetes", "nginx", "latency"]
}
```

The map names each member's topic explicitly, so routing is correct **even when
the members' crystals overlap heavily** — e.g. a school whose members all skim
one broadcast stream. Keywords are lowercased and matched on word boundaries, so
`"RCP"`, `"n8n"`, and `"raw-archive"` all work and `"art class"` won't fire on
`"start classes"`. A **member wakes only on a real keyword hit** — a bare
mention of its *name* is not enough (else members named with ordinary words —
`desk`, `paper`, `boot` — would fire on incidental prose). When a member does
have a keyword hit, a match on its name lifts it into a strictly higher rank
tier, so the fish named for the subject wins its subject over a rival with more
incidental hits. (Want a name to route on its own? List it as one of that
member's keywords.)

### Auto-derived (zero-config fallback)

With no `afferent_topics.json`, `build_index` derives a starter interest map from
each member's TF-IDF-distinctive mined vocab (minus the member's own name tokens,
so the name can't sneak back in as a keyword) and flags `topics_auto`. It routes,
but more noisily than a curated map — the build CLI says so and points you at
`afferent_topics.json`.

> **Why not route on frequency directly.** If every member of a school ate the
> same stream, the topic signal is **not statistically recoverable** by any
> frequency method — the shared stream dominates every member's vocabulary and
> the genuine topic words are drowned beneath it (measured: five scoring variants,
> small-member and large-member hijack with no sweet spot). The answer is not a
> cleverer statistic — it's a keyword map (supplied or auto-derived), routed by
> hit-count with a name tier. `_mined_scores` remains only as the vocab-mining
> step behind the auto-derived map, not a live route.

## Snippets

Under curated routing, a woken member can surface one **on-topic crystal**: the
text window centered on the matched keyword, harvested at build time. Centering on
the keyword makes the snippet about the topic *by construction* — immune to
off-topic but high-ache crystals that a "top crystal" heuristic would surface.

## Usage

```python
from linafish.afferent import build_index, surface_for

# offline, rare: build the precomputed index
build_index("/path/to/school", "/path/to/school/afferent_index.json")

# per-turn, cheap: route a prompt
woke = surface_for("reset the billing webhook", "/path/to/school/afferent_index.json")
# -> [("billing", ["billing", "webhook"], "...snippet about the webhook..."), ...]
```

CLI (top-level subcommand, or the module form):

```bash
linafish afferent build  <school_dir> [index_path]
linafish afferent route  <index_path> "<prompt>"     # alias: surface
# or: python -m linafish.afferent build|route ...
```

Wire `surface_for` into your agent's prompt-submit hook to emit a one-line
"specialist X is relevant: <snippet>" each turn. Fail-silent — an afferent organ
must never block a turn (non-string keywords are dropped at load, not raised on).

## Status

Build + curated routing (supplied or auto-derived) + keyword-centered snippets
are implemented and tested, and exposed as the top-level `linafish afferent`
subcommand. Not yet wired into `linafish go`; that's the next shaping step.
Known gap: snippets are only harvested for *supplied* keyword maps — an
auto-derived index routes but returns empty snippets.
