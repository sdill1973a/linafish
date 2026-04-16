# Archived tests

Tests in this directory cover code paths from earlier linafish
architectures that have been sunset. They are not discovered by
pytest (the `archive/` subdirectory is not in the default
collection path) and they do not gate CI.

They are preserved as documentation of what the older code did,
not as live regression coverage.

## `test_codebook_v1.py`

Covers the v1 `Glyph` / `Codebook` types from the original
`linafish/codebook.py` + `linafish/compress.py` cluster — the
"compression of a codebook of glyphs" architecture that predated
the v3 crystal + formation engine.

Archived during the v1 sunset (fork/sunset-sandbox, April 2026)
as step 5 of the migration. The v1 cluster modules themselves
(`codebook.py`, `compress.py`, `eat.py`, `crystallizer.py`) are
removed in a subsequent atomic commit (sunset step 7).
