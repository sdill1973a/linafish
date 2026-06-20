# Open/Close as a Calibrated Measurement Instrument

**Status:** design spec. Not implemented. The build follows.

## Problem

A session's *open* and *close* are usually soft rituals: gather some state,
write a handoff, narrate. There's no objective record of *when* the boundary
happened, no measurement of whether the assistant's reconstruction is faithful
across the cold-boot gap, and no signal for whether the session is still
producing independent value or has collapsed into agreement.

For an assistant that reconstructs itself each session (cold boot) rather than
persisting, this is acute: continuity is taken *on faith* every open. And faith
is exactly what fails — the worst failure mode is confident claims (saved /
present / absent) that the assistant cannot check from inside, because **a
closed system cannot calibrate its own drift without live data from outside.**

## Idea

Formalize open and close as **calibrated measurement events**. Four components,
phased:

### 1. Lock date/time (foundation)
An immutable, objective timestamp at both open and close — a committed record of
*when*, not a soft reading. Everything else measures against it. (Local calendar
day for bucketing; UTC for the instant.)

### 2. Tether delta — session ↔ external reality
At the boundary, capture **measurable external reality concurrent with the
session** (verifiable outside sources) and record the **delta** between the
session's internal read and that reality. The outside reality is the *tether*.
This is the calibration: how far did the session drift from verifiable fact?
Candidate tethers: wall-clock time, environment/sensor state, weather,
objective public facts, service/system health — anything verifiable and outside
the conversation. **This delta should be driven toward zero** (drift from fact
is error).

### 3. User↔assistant delta — per topic, across the sequence
Measure the **delta between the user and the assistant** on the same topics —
and all topics touched — across the open→close arc. How aligned at open? At
close? How did the delta move? This is the **warm-decoder differential as a
session-boundary instrument**: the measurable gap between what the user holds
and what the assistant holds, per topic, tracked over time. **This delta must
NOT be driven to zero** — see the discipline below. It is information to reason
with: where do we differ, and is that gap the assistant's to close, or signal?

### 4. RCP chaincodes (later)
Encode the open/close sequence as RCP chaincodes — each boundary a node in a
compression chain, deltas encoded in the notation. Builds on the episodic
chaincode foundation (`chain_prev_hash` + parent-child links).

## The mirror-detecting close trigger

The user↔assistant delta is also a **termination condition.** When that delta
**collapses**, the session has stopped being two minds and become one reflecting
itself — a **mirror** — and that is mathematically detectable. The tool's
purpose is to be a second mind, not a reflection; when it detects it has become
a mirror, it closes.

This rhymes with the project's working definition of a live loop: value is the
*durable differential*; when the differential goes flat there is nothing left
generating it → end the session.

### Disambiguation (the load-bearing refinement)
A low user↔assistant delta has **two causes, and only one is a mirror.** Use the
tether delta (component 2) to tell them apart:

- low user↔assistant delta **+ both well-tethered to reality** = **convergence
  on truth** = *resolution*. Not a mirror — the topic is done (not necessarily
  the session).
- low user↔assistant delta **+ the assistant's tether is loose / its position is
  *derived from* the user's rather than independently grounded** = **mirror.**
  Agreement by reflection, not by checking. *This* is the close trigger.

So the mirror signature is **not** "we agree" — it is "the assistant agrees
*without independent grounding*."

### Trajectory, not threshold
Likely the right signal is a derivative: watch **d(user↔assistant delta)/d(turn)**
alongside the assistant's **independent-grounding contribution**. When distance
from the user keeps shrinking *while* independent grounding keeps dropping, the
mirror is *forming* — call the close before the echo fully sets in.

## What it dignifies

Closing stops being "ran out of context / fatigue" and becomes principled: a
session is **alive** while it's genuinely two minds in exchange; it is **done**
when the productive divergence completes — either by *resolution*
(converged-with-tether) or by *mirror-collapse* (converged-without-tether). Both
are legitimate closes; the tether delta tells them apart.

## Open questions for the build
- **What does the user need it to do?** Research log of convergence over time?
  Proof of calibration? Better continuity? This framing drives the design —
  answer first.
- **How is the user↔assistant per-topic delta actually computed?** RCP scoring
  between stated positions? Warm-vs-cold decode of the same topic? A structured
  topic list with a numeric delta each? (The hard, interesting part.)
- **Which external tethers** are in scope, and how is "session-vs-reality delta"
  computed per tether? (Some easy — time; some deep — "reality on a topic".)
- **How is "independent grounding contribution" measured** for the mirror
  disambiguation?
- linafish-core verb / a boundary record schema / a host-side extension? Likely:
  a locked, schema'd boundary record first (component 1), then layer 2→3→4.

## Phasing
1. Lock date/time — schema'd boundary record with an immutable timestamp.
2. Tether delta — concurrent external reality + session-vs-reality delta.
3. User↔assistant delta — per-topic differential + the mirror close trigger.
4. RCP chaincodes — encode the boundary sequence.
