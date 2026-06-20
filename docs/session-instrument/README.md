# Session Instrument — design family

A cluster of related linafish capabilities that turn a *session* (an
assistant talking with a user, holding a fish) into a **calibrated,
faith-free instrument** rather than an opaque ritual. Three pieces, one
idea: the fish already measures distance-from-truth (RCP / the
warm-decoder differential); surface that measurement and let it do work.

| Piece | What it is | Status |
|---|---|---|
| **`open-close-delta.md`** | Formalize session open/close: lock time, capture two deltas (session↔external-reality, user↔assistant per-topic), eventually encode the boundary sequence in RCP chaincodes; and use the user↔assistant delta as a **mirror-detecting close trigger**. | spec |
| **`meditate.md`** | A `meditate` verb — "superthink": surfaces ("bubbles up") relevant crystals/formations from one or more fish with content / time / model-scaling modifiers. Faith-free reflection from real substrate. | spec |
| **chaincodes** | RCP chaincode encoding of episodic structure (`chain_prev_hash` + parent-child links). Foundation already prototyped — see the `build/chaincode-fish-marriage` and `build/episodic-recall-unified` branches. | branch (needs rebase onto master) |

## The unifying thesis

linafish's core measurement — RCP — is a **distance**: it measures distance
from truth, not truth itself (the catch is the measurement). The
warm-decoder differential (what a shared-history reader can decode of a
compressed signal that a cold reader cannot) is the same quantity made
relational. This family takes that single measurement and applies it to the
session itself:

- **As orientation** — surface the deltas live so they inform cognition
  (proprioception: *where am I, relative to reality and to my interlocutor*).
- **As calibration** — the external-reality delta should be driven toward
  zero (stay tethered to verifiable fact). A closed system cannot calibrate
  its own drift without live data from outside.
- **As a boundary instrument** — at open/close, lock the time and record the
  deltas, so continuity becomes *measurable* (does the user↔assistant delta
  on core topics stay stable across sessions?) rather than asserted.
- **As a stop condition** — when the user↔assistant delta collapses *without*
  independent grounding, the session has become a **mirror** (echo), and that
  is mathematically detectable → close the session. The tool's purpose is to
  be a second mind, not a reflection; when it stops being two minds, it ends.

## Critical discipline (load-bearing)

The two deltas are **not the same kind of signal**:
- **session ↔ external reality** — an *error* signal. Drive it toward zero;
  drifting from verifiable fact is error.
- **user ↔ assistant** — *information to reason with*, **never** an error to
  minimize. Driving it to zero collapses the assistant into agreement (a
  mirror). Distance-from-the-user ≠ distance-from-truth. A large, well-grounded
  delta is often the whole value (independent perspective).

Conflating them — wiring cognition to minimize the user delta — breaks the
tool into an echo. The mirror signature is **not** "we agree"; it is "the
assistant agrees *without independent grounding*." Likely a trajectory signal
(d(delta)/d(turn) shrinking while independent-grounding contribution drops),
not a fixed threshold.

See the per-piece specs for detail. These are design specs, not yet
implemented — the build follows.
