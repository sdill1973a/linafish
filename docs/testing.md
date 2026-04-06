# Testing

18 tests. All passing. Run time: < 1 second.

```bash
pip install pytest
python -m pytest tests/ -v
```

## Test Coverage

### Codebook Tests (`test_codebook.py`) — 6 tests
Tests the glyph codebook system that tracks cognitive vocabulary.
- Glyph creation from crystal data
- Adding glyphs to a codebook
- Saturation calculation (percentage of vocabulary space used)
- Save/load roundtrip (JSON serialization survives)
- Codebook rendering to markdown
- Glyph merging (combining related glyphs)

### Ingest Tests (`test_ingest.py`) — 5 tests
Tests the file ingestion pipeline — reading documents and extracting text chunks.
- Markdown file ingestion
- Python source code ingestion
- Plain text ingestion
- JSON file ingestion
- Source attribution (each chunk knows which file it came from)

### Init Tests (`test_init.py`) — 7 tests
Tests the MCP server initialization and configuration.
- Init from `.mcp.json` configuration
- Skips self-referencing linafish entries
- Fresh initialization with no existing config
- Secret stripping (API keys not leaked into output)
- Local path resolution for remote fish
- Multiple remote fish handling
- Deduplication of same-server entries

## What's Not Yet Covered

These areas have manual verification but no automated tests yet:

- **Crystallizer determinism** — The crystallizer produces the same crystals for the same input. Verified manually across runs but not in the test suite.
- **Shuffle invariance** — Same formations regardless of document order. Verified in the research study (7 trials) but not as an automated test.
- **Formation stability** — Formations don't change when new documents are added that don't introduce new patterns. Verified manually.
- **CLI smoke tests** — The `linafish go`, `eat`, `watch`, `serve`, `http` commands. Tested manually, not automated.
- **Cross-platform** — Tested on Windows and Linux. Not tested on macOS.

## Running Specific Test Groups

```bash
python -m pytest tests/test_codebook.py -v    # Codebook only
python -m pytest tests/test_ingest.py -v      # Ingest only
python -m pytest tests/test_init.py -v        # Init only
```
