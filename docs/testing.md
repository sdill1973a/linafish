# Testing

451 tests. All passing. Run time: a few seconds.

```bash
pip install pytest
python -m pytest tests/ -v
```

## Test Coverage

The suite covers the full pipeline — ingestion, crystallization, formations,
persistence, the HTTP/converse servers, and the CLI verbs. A sampling of the
larger groups (run `ls tests/` for the complete list):

### Chaincode Tests (`test_chaincode_marriage.py`) — 29 tests
Chain metadata on crystals: chain ids, ordinal proximity, parent-child links,
and the temporal coupling bonus they enable.

### Dedup Tests (`test_dedup_helpers.py`) — 27 tests
The `normalize_for_dedup` rule: how incoming text is normalized before
content-hash deduplication decides whether the fish has already eaten it.

### Lock Tests (`test_locks.py`, `test_re_eat_takes_the_writer_lock.py`) — 27 tests
Stale lockfile detection, and the writer lock `/re-eat` must hold while it
rebuilds state.

### Formation Tests (`test_formation_gardener.py`, `test_formation_address.py`) — 33 tests
Formation detection, gardening (merge/prune), and the addressed formation
index.

### Ingest Tests (`test_ingest.py`, `test_ingest_chunk_bound.py`) — 9 tests
The file ingestion pipeline — reading documents and extracting text chunks:
markdown, Python source, plain text, JSON, source attribution, and chunk-size
bounds.

### CLI `go` Tests (`test_go_idempotent.py`, `test_go_is_idempotent.py`, `test_go_chunks_and_forms.py`) — 15 tests
`linafish go` end to end: re-running on the same folder does not re-eat,
chunking produces passages, and formations actually form.

### Bare-Verb Tests (`test_bare_verbs_feed_the_fish.py`) — 6 tests
Bare `eat` / `ask` / `check` / `whisper` auto-discover the existing fish
instead of silently creating a new one.

### Server Tests (`test_http_threaded.py`, `test_http_boot_503.py`, `test_http_bind_before_engine.py`, `test_msg_endpoints.py`) — 25 tests
The HTTP server: threading, boot-time 503s, bind-before-engine ordering, and
the federation `/msg` endpoints.

### Heart and Vizmem Tests (`test_heart.py`, `test_vizmem_sketchpad.py`) — 22 tests
The heart beat (family config, gating, surfacing) and the visuospatial
sketchpad (bindings, minting, the read-only wall).

## What's Not Yet Covered

These areas have manual verification but no automated tests yet:

- **Crystallizer determinism** — The crystallizer produces the same crystals for the same input. Verified manually across runs but not in the test suite.
- **Shuffle invariance** — Same formations regardless of document order. Verified in the research study (7 trials) but not as an automated test.
- **Formation stability** — Formations don't change when new documents are added that don't introduce new patterns. Verified manually.
- **CLI smoke tests for `watch`, `serve`, and `listen`** — `linafish go` and the bare verbs are covered (`test_go_idempotent.py`, `test_go_is_idempotent.py`, `test_go_chunks_and_forms.py`, `test_bare_verbs_feed_the_fish.py`); the long-running daemon verbs are still tested manually.
- **Cross-platform** — Tested on Windows and Linux. Not tested on macOS.

## Running Specific Test Groups

```bash
python -m pytest tests/test_ingest.py -v                   # Ingest only
python -m pytest tests/test_go_idempotent.py -v            # `go` idempotency
python -m pytest tests/test_bare_verbs_feed_the_fish.py -v # Bare CLI verbs
python -m pytest tests/test_heart.py -v                    # Heart beat
```
