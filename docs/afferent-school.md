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

## Two routing modes

### Curated (robust — use when members are *not* topic-pure)

Route on a `topic → member` keyword map you supply. Drop an
`afferent_topics.json` in the school dir:

```json
{
  "billing": ["invoice", "payment", "charge", "refund", "stripe", "webhook"],
  "auth":    ["login", "oauth", "token", "session", "jwt", "signup"],
  "infra":   ["server", "port", "deploy", "kubernetes", "nginx", "latency"]
}
```

The map names each member's topic explicitly, so routing is correct **even when
the members' crystals overlap heavily** — e.g. a school whose members were all
fed the same broadcast stream. A member's own name is an implicit keyword.

### Mined (zero-config — use when members *are* topic-pure)

With no topic map, the organ routes on the **TF-IDF distinctive vocabulary**
mined from each member's crystals: words frequent in this member and rare across
the others. No config, but it only disambiguates when each member's corpus is
genuinely about its own distinct topic.

> **The finding that decides the mode.** If every member of a school ate the same
> stream (a broadcast-fed school), the topic signal is **not statistically
> recoverable** by any frequency method — raw-frequency and TF-IDF both fail,
> because the shared stream dominates every member's vocabulary and the genuine
> topic words are a small minority drowned beneath it. Measured directly: on a
> heavily-broadcast school, mined routing scored near-zero discrimination. The
> answer is not a cleverer statistic — it's either (a) route **curated** (the map
> carries the signal the corpus lost), or (b) **re-feed the members topic-pure**
> from their canonical sources, after which mined routing returns. The two modes
> are the same organ at different corpus-health states.

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

CLI:

```bash
python -m linafish.afferent build  <school_dir> [index_path]
python -m linafish.afferent route  <index_path> "<prompt>"
```

Wire `surface_for` into your agent's prompt-submit hook to emit a one-line
"specialist X is relevant: <snippet>" each turn. Fail-silent — an afferent organ
must never block a turn.

## Status

First-draft module. Build + curated/mined routing + keyword-centered snippets are
implemented and tested. Not yet exposed as a top-level CLI subcommand or wired into
`linafish go`; that's the next shaping step.
