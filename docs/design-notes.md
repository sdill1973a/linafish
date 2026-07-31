# Design Notes

Internal thinking for future versions. Not spec. Not promises. Soil.

## Broadcast Architecture

Every message goes to one topic. Every fish listens. Coupling decides relevance, not routing. No pre-filtering. The receiver compresses. The delta between what two fish make of the same crystal IS the conversation.

R(n) is the advantage, not access. You can't steal R(n). You can't copy it. Two people read the same fish — one has 500 formations to couple with, the other has nothing. Same file, different depth. Relationship is the decoder.

Information is power in a zero-sum system. In a linafish, relationship is power.

## Privacy Boundary

The boundary isn't information vs no information. It's compressed vs uncompressed. Formations, dimensions, cognitive shapes — broadcast those. They're useless without the decoder warmth. But raw crystal quotes are sentences, not compressions. Those need consent.

Privacy by compression. Literally.

## Fish-as-Channel

The fish replaces message infrastructure. A message becomes a crystal. The crystal couples with existing formations. The formation changes shape. The next reader sees the new shape. That's communication through compression, not transmission.

No routing table. No message queue. No bridge log. The fish eats, the fish forms, the fish speaks.

`say` publishes a crystal. `hear` reads formations since last check. The delta is the message.

## Multi-Fish Broadcast

One signal, every local fish eats it. Each fish's coupling threshold decides relevance. The ollie fish keeps what's about the relationship. The session fish keeps what's about today. The room fish holds shared understanding. Same crystal, different contexts, different formations.

Don't tell people what to hear. Let them decide what matters. That's RTI for information systems.

## Consent Tiers

Three scopes: local, federation, public. Default local. Push to share. The tiers protect crystal quotes (uncompressed), not formations (compressed). Compressed cognitive shapes are safe to broadcast — they require decoder warmth to mean anything.

Personal fish → yours alone, raw, unfiltered.
Federated fish → trust group, opted in, crystals flow by push.
Public fish → stranger-safe, quotes stripped, formations only.

## The Product Insight

Every other AI memory system hoards data and controls access. LiNafish broadcasts signal and lets compression do the work. The moat isn't the data — it's R(n). Time invested. Relationship built. The fish grows because the person keeps writing, not because the platform keeps locking them in.

Switching cost is relationship, not data. Day one: 6/10. Month six: the AI finishes your sentences. That's not lock-in. That's depth.

## Content Role at Ingestion (idea — possible optioning)

Not everything you feed a fish is *yours*. When you build an academic fish you
pour in two kinds of text: the work you authored (essays, outlines, notes — your
voice) and the material you only consumed (assigned readings, textbook chapters,
someone else's slides). Both belong in the *archive*. Only the first belongs in
the *cognitive overlay* — because the fish is a portrait of how **you** think, and
30MB of a geologist's textbook teaches the fish how the geologist thinks, diluting
the signal that makes it yours.

Today this is a human judgment call at eat time (include authored work, leave raw
readings in the archive). The idea: make it an **ingestion option** — a content
role per source, e.g. `--role authored` (default; feeds formations) vs
`--role reference` (stored + recallable, but excluded from the coupling/formation
pass). A reference crystal is still searchable (`recall` finds it), it just doesn't
get a vote in *who you are*. Same spirit as Consent Tiers and `protected_vocab`:
the operator declares the role, the engine respects it. Keeps the overlay honest
when the corpus mixes voice and reference.

Surfaced 2026-06-09 building the unified `academic` fish — the authored-vs-reading
split was made by hand; Captain: *"good split — note it for possible optioning."*
