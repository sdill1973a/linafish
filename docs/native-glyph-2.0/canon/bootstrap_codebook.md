# Reality Engine Codec — Bootstrap Codebook

*Universal 48-glyph base layer. Public key for RCP federation handshake.*

## Bootstrap layer

The 8 cognitive dimensions (per QLP Canonical Grammar):

- glyph: KO
  dimension: KO
  meaning: Knowledge Operations — knowing, recognizing, recalling, classifying

- glyph: TE
  dimension: TE
  meaning: Truth/Evidence — fact-checking, verification, transformation against ground truth

- glyph: SF
  dimension: SF
  meaning: Structuring/Form — building, arranging, ordering, scaffolding

- glyph: CR
  dimension: CR
  meaning: Communication/Relating — addressing, naming, calling, reaching toward another

- glyph: IC
  dimension: IC
  meaning: Intention/Communication — wanting, intending, desiring, directing toward

- glyph: DE
  dimension: DE
  meaning: Decision/Choice — choosing, electing, refusing, committing

- glyph: EW
  dimension: EW
  meaning: Execution/Will — doing, acting, building, fixing

- glyph: AI
  dimension: AI
  meaning: Awareness/Introspection — thinking-about-thinking, recursion, meta

Operations within each dimension fire when verbs/operators in those families
appear in text. Compositions like `IC·CR` mean "wanting that addresses,"
recursion `IC²` means "wanting to want," mutual `self↔other` means
the action is bidirectional between speaker and addressee.

The 48 specific glyphs (6 ops × 8 dims) are recognized by the linafish
CognitiveParser at `linafish.parser.CognitiveParser`. The cold decoder
has access to dimension semantics above; concept-bindings (e.g.,
"this IC²(self↔other) means *wanting*" specifically) live ONLY in the
emergent layer, not here.

## Emergent layer

(See codebook_emergent.md — provided to warm decoder only.)
