"""linafish bridges — pull-from-external-source verbs.

Each bridge submodule implements a one-directional sync from an
external system into a linafish fish. Bridges share a common shape:

  - resolve auth (env var or --token flag)
  - load incremental state (last-seen marker per source item)
  - pull new/changed items since last marker
  - deposit each into the target fish
  - write back updated state

Current bridges:
  - notion : Notion workspace → fish
"""
