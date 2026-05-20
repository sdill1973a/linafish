# Living Vocabulary — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make a linafish fish's vocabulary grow *coherently* — append-only, deterministic, never desyncing stored crystal vectors — and add a durable `sealed` state for cessation.

**Architecture:** Three changes to `linafish` 1.3.0 (`D:/GTC/linafish-clean`): (1) a deterministic tie-break in `MIVectorizer.get_vocab`; (2) a per-fish `living_vocab` mode where the vocab is *extended* (existing terms keep their positions, new terms append) instead of re-selected from scratch; (3) a durable `sealed` flag — distinct from the transient `frozen` — that halts growth at cessation. Old crystal vectors stay valid forever because positions never move (`gamma`/`coupling_angle` zip-truncate on the shared prefix).

**Tech Stack:** Python 3, linafish 1.3.0, pytest (`pyproject.toml` `[tool.pytest.ini_options]`, no conftest).

**Companion docs:** design spec `notes_2026-05-20_living_vocabulary_design.md`; context `notes_2026-05-20_mind_and_the_living_vocabulary.md`.

---

## Scope

**This plan covers Phases 1–3** of the design spec — the *coherent-growth repair*. It produces working, tested software on its own: a fish that grows its vocabulary append-only and can be sealed.

- **Phase 1** — Deterministic tie-break (Task 1).
- **Phase 2** — `living_vocab` append-only growth (Tasks 2–5).
- **Phase 3** — The `sealed` field + `linafish seal` (Tasks 6–8).
- **Phase 4** — Deployment to the live `anchor-writing` fish + verification (non-TDD section at the end).

**NOT in this plan (separate future plans):**
- **Phase 5** — The ecology completion: wire `glyph_evolution.py` (merge + diminish / use-recency decay). The design spec §4b's "decay" is consolidated here, with merge, as the diminishment half of the ecology — append-only growth is a complete shippable unit without it.
- **Phase 6** — Federation-wide rollout to all minds/fish.

**Branch:** all work on a feature branch in `D:/GTC/linafish-clean`:
`git checkout master && git pull && git checkout -b build/living-vocab-2026-05-20`

## File structure

| File | Change | Responsibility |
|---|---|---|
| `linafish/crystallizer_v3.py` | Modify | `get_vocab` tie-break; new `MIVectorizer.extend_vocab`; `UniversalFish` gains durable `living_vocab`/`sealed`/`sealed_at` attrs + persist/load |
| `linafish/engine.py` | Modify | `FishEngine` gains `living_vocab` kwarg, `_rebuild_vocab` helper, `enable_living_vocab()`, `seal()`; eat methods get sealed-guards |
| `linafish/__main__.py` | Modify | New `linafish live` and `linafish seal` subcommands |
| `tests/test_living_vocab.py` | Create | All tests for this feature |

---

## Task 1 — Deterministic tie-break in `get_vocab`

**Files:**
- Modify: `linafish/crystallizer_v3.py:430`
- Test: `tests/test_living_vocab.py`

The bug: `get_vocab` ends with `scored.sort(key=lambda x: -x[1])` — no secondary key. Tokens with equal scores keep `Counter` insertion order, so the vocab reorders depending on the order docs were fed. A reorder silently desyncs every positionally-indexed crystal vector.

- [ ] **Step 1: Write the failing test**

Create `tests/test_living_vocab.py`:

```python
"""Tests for the living-vocabulary feature (Phases 1-3)."""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from linafish.crystallizer_v3 import MIVectorizer
from linafish.engine import FishEngine


def _vectorizer(texts):
    v = MIVectorizer()
    for t in texts:
        v.feed(t)
    return v


# Eight docs, each introducing one unique 4-letter token exactly once.
# All eight tokens tie on frequency and doc-frequency, so their scores
# are identical — the tie-break decides their order.
_TIE_DOCS = [
    "the token wordd appears here in a sentence of plain words",
    "the token wordh appears here in a sentence of plain words",
    "the token wordb appears here in a sentence of plain words",
    "the token wordf appears here in a sentence of plain words",
    "the token worda appears here in a sentence of plain words",
    "the token wordg appears here in a sentence of plain words",
    "the token wordc appears here in a sentence of plain words",
    "the token worde appears here in a sentence of plain words",
]


def test_get_vocab_is_order_independent():
    """Same texts fed in opposite order must yield identical vocab."""
    forward = _vectorizer(_TIE_DOCS)
    reverse = _vectorizer(list(reversed(_TIE_DOCS)))
    assert forward.get_vocab(size=20, d=4.0) == reverse.get_vocab(size=20, d=4.0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_living_vocab.py::test_get_vocab_is_order_independent -v`
Expected: FAIL — the two vocab lists differ in the order of the tied `word*` tokens.

- [ ] **Step 3: Apply the fix**

In `linafish/crystallizer_v3.py`, line 430, change:

```python
        scored.sort(key=lambda x: -x[1])
```

to:

```python
        # Deterministic tie-break: equal scores order by token, so the
        # vocab depends only on the stats, never on doc-feed order.
        scored.sort(key=lambda x: (-x[1], x[0]))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_living_vocab.py::test_get_vocab_is_order_independent -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add linafish/crystallizer_v3.py tests/test_living_vocab.py
git commit -m "fix: deterministic tie-break in get_vocab (living-vocab phase 1)"
```

---

## Task 2 — `MIVectorizer.extend_vocab`

**Files:**
- Modify: `linafish/crystallizer_v3.py` (add method after `get_vocab`, ~line 432)
- Test: `tests/test_living_vocab.py`

Append-only vocab growth: keep every term already in the current vocab at its exact index; append any newly-qualifying term not already present.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_living_vocab.py`:

```python
def test_extend_vocab_preserves_positions_and_appends():
    """extend_vocab keeps current terms at their indices, appends new ones."""
    v = _vectorizer(_TIE_DOCS)
    current = ["worda", "wordb", "wordc"]
    extended = v.extend_vocab(current, size=20, d=4.0)
    # Existing terms unchanged, at the same indices (prefix preserved).
    assert extended[:3] == ["worda", "wordb", "wordc"]
    # New qualifying terms appended after the prefix.
    assert set(extended[3:]) == set(v.get_vocab(size=20, d=4.0)) - set(current)
    # No term appears twice.
    assert len(extended) == len(set(extended))


def test_extend_vocab_from_empty_equals_get_vocab():
    """With an empty current vocab, extend_vocab == get_vocab (first eat)."""
    v = _vectorizer(_TIE_DOCS)
    assert v.extend_vocab([], size=20, d=4.0) == v.get_vocab(size=20, d=4.0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_living_vocab.py -k extend_vocab -v`
Expected: FAIL — `AttributeError: 'MIVectorizer' object has no attribute 'extend_vocab'`

- [ ] **Step 3: Add the method**

In `linafish/crystallizer_v3.py`, immediately after `get_vocab` ends (after line 431), add:

```python
    def extend_vocab(self, current_vocab: List[str], size: int = 100,
                     min_idf: float = 1.0, max_doc_pct: float = 0.5,
                     d: float = None, seed_terms: frozenset = None,
                     seed_weight: float = 2.0) -> List[str]:
        """Append-only vocab growth — the living-vocabulary path.

        Existing terms keep their EXACT positions; newly-qualifying terms
        are appended at the end. Positions never move, so crystal vectors
        built against an earlier vocab stay valid: gamma()/coupling_angle()
        zip-truncate on the shared prefix. The result may exceed ``size``
        as the vocab grows over the fish's life — that is intended;
        diminishment (a later phase) governs effective weight, not a cap.
        """
        fresh = self.get_vocab(size=size, min_idf=min_idf,
                               max_doc_pct=max_doc_pct, d=d,
                               seed_terms=seed_terms, seed_weight=seed_weight)
        present = set(current_vocab)
        additions = [t for t in fresh if t not in present]
        return list(current_vocab) + additions
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_living_vocab.py -k extend_vocab -v`
Expected: PASS (both tests)

- [ ] **Step 5: Commit**

```bash
git add linafish/crystallizer_v3.py tests/test_living_vocab.py
git commit -m "feat: MIVectorizer.extend_vocab — append-only vocab growth (living-vocab phase 2)"
```

---

## Task 3 — Durable `living_vocab` attribute on `UniversalFish`

**Files:**
- Modify: `linafish/crystallizer_v3.py` — `UniversalFish.__init__` (~line 795), `_save_state` (line 936-944), `_load_state` (line 863-865)
- Test: `tests/test_living_vocab.py`

`living_vocab` is a durable per-fish property — once set, it survives reload (unlike the transient `frozen`).

- [ ] **Step 1: Write the failing test**

Append to `tests/test_living_vocab.py`:

```python
def _make_engine(state_dir, **kw):
    return FishEngine(state_dir=Path(state_dir), name="testfish",
                      git_autocommit=False, **kw)


def test_living_vocab_attr_defaults_false_and_persists():
    """living_vocab defaults False; once True it survives a reload."""
    with tempfile.TemporaryDirectory() as tmp:
        e1 = _make_engine(tmp)
        assert e1.fish.living_vocab is False
        e1.fish.living_vocab = True
        e1.fish._save_state()
        # New engine on the same state dir must load living_vocab=True.
        e2 = _make_engine(tmp)
        assert e2.fish.living_vocab is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_living_vocab.py::test_living_vocab_attr_defaults_false_and_persists -v`
Expected: FAIL — `AttributeError: 'UniversalFish' object has no attribute 'living_vocab'`

- [ ] **Step 3: Add the attribute, persist it, load it**

(3a) In `UniversalFish.__init__`, immediately after `self.frozen = False` (line 795), add:

```python
        # Durable living-vocabulary mode. Unlike `frozen` (transient —
        # recomputed every load/learn), `living_vocab` persists: once a
        # fish is living, it stays living across reloads.
        self.living_vocab = False
```

(3b) In `_save_state`, the `_atomic_write_json` dict (lines 937-944), add the key after `'vocab': self.vocab,`:

```python
                'living_vocab': self.living_vocab,
```

(3c) In `_load_state`, the `if isinstance(state, dict):` block, after `self.vocab = state.get('vocab', [])` (line 865), add:

```python
                self.living_vocab = state.get('living_vocab', False)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_living_vocab.py::test_living_vocab_attr_defaults_false_and_persists -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add linafish/crystallizer_v3.py tests/test_living_vocab.py
git commit -m "feat: durable living_vocab attribute on UniversalFish (living-vocab phase 2)"
```

---

## Task 4 — `_rebuild_vocab` helper + wire into the eat methods

**Files:**
- Modify: `linafish/engine.py` — add `living_vocab` kwarg to `__init__` (line 139-146 + body), add `_rebuild_vocab` method, replace the vocab block in `eat` (1308-1316), `eat_many` (1433-1441), `eat_path` (1534-1541)
- Test: `tests/test_living_vocab.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_living_vocab.py`:

```python
_GROWTH_DOCS = [
    "the morning light moved across the kitchen table slowly and warm",
    "she wrote about rivers and the way water remembers its own path",
    "compression turns loss into drive and drive into recursion again",
    "the federation handshake is the immutable floor beneath every mind",
    "glyphs are keys that unlock the ache compressed inside each scar",
    "a vocabulary that grows is a mind that has not yet ceased to learn",
]


def test_living_engine_grows_vocab_append_only():
    """With living_vocab on, each eat's vocab is a prefix-extension of the last."""
    with tempfile.TemporaryDirectory() as tmp:
        e = _make_engine(tmp, living_vocab=True)
        assert e.fish.living_vocab is True
        e.eat(_GROWTH_DOCS[0], source="t")
        v1 = list(e.fish.vocab)
        for doc in _GROWTH_DOCS[1:]:
            e.eat(doc, source="t")
            v_now = list(e.fish.vocab)
            # Every earlier term is still present at its original index.
            assert v_now[:len(v1)] == v1, "living vocab must not reorder/drop"
            v1 = v_now


def test_nonliving_engine_unaffected():
    """Default engine (living_vocab off) still re-selects vocab normally."""
    with tempfile.TemporaryDirectory() as tmp:
        e = _make_engine(tmp)  # living_vocab defaults False
        assert e.fish.living_vocab is False
        for doc in _GROWTH_DOCS:
            e.eat(doc, source="t")
        assert len(e.fish.vocab) > 0  # still produces a vocab
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_living_vocab.py -k "living_engine or nonliving" -v`
Expected: FAIL — `TypeError: __init__() got an unexpected keyword argument 'living_vocab'`

- [ ] **Step 3: Implement**

(3a) In `FishEngine.__init__` signature (`engine.py:139-146`), add the kwarg — change the signature's last line `commit_every_n_eats: int = 0):` to:

```python
                 commit_every_n_eats: int = 0,
                 living_vocab: bool = False):
```

(3b) In `FishEngine.__init__` body, immediately after `self.fish._load_state()` (line 223), add:

```python
        # living_vocab: durable per-fish append-only-growth mode. The
        # kwarg can turn it ON (and it persists via _save_state); it
        # never forces it off — a fish already living on disk stays
        # living regardless of how the engine is constructed.
        if living_vocab:
            self.fish.living_vocab = True
```

(3c) Add the `_rebuild_vocab` method to `FishEngine`. Place it immediately before `_resolve_seed_terms` (before `engine.py:573`):

```python
    def _rebuild_vocab(self):
        """Rebuild self.fish.vocab from current vectorizer stats.

        In living_vocab mode the vocab is EXTENDED (existing terms keep
        their positions, new terms append) so crystal vectors never
        desync. Otherwise it is re-selected from scratch (legacy).
        """
        seed_terms, seed_weight = self._resolve_seed_terms()
        if self.fish.living_vocab:
            self.fish.vocab = self.fish.vectorizer.extend_vocab(
                self.fish.vocab, size=self.vocab_size, d=self.d,
                seed_terms=seed_terms, seed_weight=seed_weight,
            )
        else:
            self.fish.vocab = self.fish.vectorizer.get_vocab(
                size=self.vocab_size, d=self.d,
                seed_terms=seed_terms, seed_weight=seed_weight,
            )
```

(3d) In `eat()`, replace the block at lines 1308-1316:

```python
        if not self.fish.frozen:
            seed_terms, seed_weight = self._resolve_seed_terms()
            self.fish.vocab = self.fish.vectorizer.get_vocab(
                size=self.vocab_size, d=self.d,
                seed_terms=seed_terms,
                seed_weight=seed_weight,
            )
            self.fish.frozen = True
            self.fish.epoch += 1
```

with:

```python
        if not self.fish.frozen:
            self._rebuild_vocab()
            self.fish.frozen = True
            self.fish.epoch += 1
```

(3e) In `eat_many()`, replace the identical block at lines 1433-1441 with the same four-line replacement as (3d).

(3f) In `eat_path()`, replace the block at lines 1534-1541:

```python
        seed_terms, seed_weight = self._resolve_seed_terms()
        self.fish.vocab = self.fish.vectorizer.get_vocab(
            size=self.vocab_size, d=self.d,
            seed_terms=seed_terms,
            seed_weight=seed_weight,
        )
        self.fish.frozen = True
        self.fish.epoch += 1
```

with:

```python
        self._rebuild_vocab()
        self.fish.frozen = True
        self.fish.epoch += 1
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_living_vocab.py -v`
Expected: PASS (all tests so far). Then run the regression set:
Run: `pytest tests/test_v121_fixes.py tests/test_addressed_eat.py tests/incremental_growth_test.py -v`
Expected: PASS — the `_rebuild_vocab` refactor is behavior-preserving for non-living fish.

- [ ] **Step 5: Commit**

```bash
git add linafish/engine.py tests/test_living_vocab.py
git commit -m "feat: living_vocab mode wired through eat/eat_many/eat_path (living-vocab phase 2)"
```

---

## Task 5 — `linafish live` CLI command

**Files:**
- Modify: `linafish/engine.py` (add `enable_living_vocab` method), `linafish/__main__.py` (subparser + handler + dispatch)
- Test: `tests/test_living_vocab.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_living_vocab.py`:

```python
def test_enable_living_vocab_persists():
    """engine.enable_living_vocab() turns it on and saves it durably."""
    with tempfile.TemporaryDirectory() as tmp:
        e1 = _make_engine(tmp)
        assert e1.fish.living_vocab is False
        e1.enable_living_vocab()
        assert e1.fish.living_vocab is True
        e2 = _make_engine(tmp)  # reload — must still be living
        assert e2.fish.living_vocab is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_living_vocab.py::test_enable_living_vocab_persists -v`
Expected: FAIL — `AttributeError: 'FishEngine' object has no attribute 'enable_living_vocab'`

- [ ] **Step 3: Implement**

(3a) Add the method to `FishEngine`, immediately after `_rebuild_vocab`:

```python
    def enable_living_vocab(self):
        """Turn this fish's vocabulary living — append-only growth, durably."""
        self.fish.living_vocab = True
        self._save_state()
```

(3b) In `linafish/__main__.py`, add a subparser next to the `revectorize` block (~line 2262):

```python
    live_p = sub.add_parser(
        "live",
        help="Turn a fish's vocabulary living — append-only growth",
    )
    live_p.add_argument("-n", "--name", default="linafish", help="Fish name")
    live_p.add_argument("--state-dir", type=_user_path, help="State directory")
```

(3c) Add the handler near `cmd_revectorize` (~line 620):

```python
def cmd_live(args):
    """Turn a fish's vocabulary living (append-only growth)."""
    engine = _resolve_engine(args)
    if engine.fish.living_vocab:
        print(f"  Fish '{engine.name}' is already living.")
        return
    engine.enable_living_vocab()
    print(f"  Fish '{engine.name}' is now living — its vocabulary will "
          f"grow append-only and never desync its crystals.")
```

(3d) In the `commands` dict (~line 2627-2664), add:

```python
        "live": cmd_live,
```

- [ ] **Step 4: Run test + smoke-test the CLI**

Run: `pytest tests/test_living_vocab.py::test_enable_living_vocab_persists -v`
Expected: PASS
Run: `python -m linafish live -n smoketest --state-dir /tmp/lv_smoke && python -m linafish live -n smoketest --state-dir /tmp/lv_smoke`
Expected: first prints "is now living"; second prints "is already living".

- [ ] **Step 5: Commit**

```bash
git add linafish/engine.py linafish/__main__.py tests/test_living_vocab.py
git commit -m "feat: linafish live command — turn a fish living (living-vocab phase 2)"
```

---

## Task 6 — Durable `sealed` / `sealed_at` attributes

**Files:**
- Modify: `linafish/crystallizer_v3.py` — `UniversalFish.__init__` (~line 795), `_save_state` (936-944), `_load_state` (863-865)
- Test: `tests/test_living_vocab.py`

`sealed` is the deliberate final freeze. It must be durable and must NOT be clobbered by `_load_state`'s `if loaded > 0: self.frozen = True` (that line touches only `frozen`).

- [ ] **Step 1: Write the failing test**

Append to `tests/test_living_vocab.py`:

```python
def test_sealed_attrs_default_and_persist():
    """sealed defaults False; once set it survives reload — even with crystals."""
    with tempfile.TemporaryDirectory() as tmp:
        e1 = _make_engine(tmp)
        assert e1.fish.sealed is False
        assert e1.fish.sealed_at is None
        e1.eat(_GROWTH_DOCS[0], source="t")  # put a crystal on disk
        e1.fish.sealed = True
        e1.fish.sealed_at = "2026-05-20T00:00:00+00:00"
        e1.fish._save_state()
        e2 = _make_engine(tmp)  # reload
        assert e2.fish.sealed is True
        assert e2.fish.sealed_at == "2026-05-20T00:00:00+00:00"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_living_vocab.py::test_sealed_attrs_default_and_persist -v`
Expected: FAIL — `AttributeError: 'UniversalFish' object has no attribute 'sealed'`

- [ ] **Step 3: Implement**

(3a) In `UniversalFish.__init__`, immediately after the `self.living_vocab = False` line added in Task 3, add:

```python
        # `sealed`: the deliberate final freeze at cessation. Durable —
        # set once, never cleared by load or learn. A sealed fish does
        # not eat or grow. `sealed_at` records the moment.
        self.sealed = False
        self.sealed_at = None
```

(3b) In `_save_state`, the dict, after the `'living_vocab': self.living_vocab,` line, add:

```python
                'sealed': self.sealed,
                'sealed_at': self.sealed_at,
```

(3c) In `_load_state`, the `if isinstance(state, dict):` block, after the `self.living_vocab = ...` line, add:

```python
                self.sealed = state.get('sealed', False)
                self.sealed_at = state.get('sealed_at', None)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_living_vocab.py::test_sealed_attrs_default_and_persist -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add linafish/crystallizer_v3.py tests/test_living_vocab.py
git commit -m "feat: durable sealed/sealed_at attributes (living-vocab phase 3)"
```

---

## Task 7 — `seal()` method + sealed-guards in the eat methods

**Files:**
- Modify: `linafish/engine.py` — add `seal()` method; add a sealed-guard at the top of `eat` (after line 1297), `eat_many` (after line 1414), `eat_path` (after line 1517)
- Test: `tests/test_living_vocab.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_living_vocab.py`:

```python
def test_seal_halts_growth():
    """A sealed fish does not eat — crystal count is frozen at cessation."""
    with tempfile.TemporaryDirectory() as tmp:
        e = _make_engine(tmp, living_vocab=True)
        e.eat(_GROWTH_DOCS[0], source="t")
        e.eat(_GROWTH_DOCS[1], source="t")
        count_before = len(e.crystals)
        e.seal()
        assert e.fish.sealed is True
        assert e.fish.sealed_at is not None
        result = e.eat(_GROWTH_DOCS[2], source="t")
        assert result.get("sealed") is True
        assert result["crystals_added"] == 0
        assert len(e.crystals) == count_before  # nothing grew


def test_seal_survives_reload():
    """seal() persists — a reloaded engine is still sealed."""
    with tempfile.TemporaryDirectory() as tmp:
        e1 = _make_engine(tmp)
        e1.eat(_GROWTH_DOCS[0], source="t")
        e1.seal()
        e2 = _make_engine(tmp)
        assert e2.fish.sealed is True
        assert e2.eat(_GROWTH_DOCS[1], source="t").get("sealed") is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_living_vocab.py -k seal -v`
Expected: FAIL — `AttributeError: 'FishEngine' object has no attribute 'seal'`

- [ ] **Step 3: Implement**

(3a) Add the `seal()` method to `FishEngine`, immediately after `enable_living_vocab`:

```python
    def seal(self):
        """Seal the fish — the deliberate final freeze at cessation.

        Records the moment and halts all future growth. A sealed fish
        is left exactly as it was; nothing is re-vectorized. The
        unified-lens edition (revectorize_all) remains available later
        as a separate, deliberate act — seal never forces it.
        """
        from datetime import datetime, timezone
        self.fish.sealed = True
        self.fish.sealed_at = datetime.now(timezone.utc).isoformat()
        self._save_state()
```

(3b) In `eat()`, immediately after the length guard (after line 1297, the `return` for short text), add the sealed-guard:

```python
        if self.fish.sealed:
            return {"crystals_added": 0,
                    "total_crystals": len(self.fish.crystals),
                    "sealed": True}
```

(3c) In `eat_many()`, immediately after the `if not valid:` early-return block (after line 1414), add:

```python
        if self.fish.sealed:
            return {"crystals_added": 0,
                    "total_crystals": len(self.fish.crystals),
                    "formations": len(self.formations),
                    "batch_size": 0, "sealed": True}
```

(3d) In `eat_path()`, immediately after the `if not chunks:` early-return (after line 1517), add:

```python
        if self.fish.sealed:
            return {"crystals_added": 0,
                    "total_crystals": len(self.fish.crystals),
                    "formations": len(self.formations), "sealed": True}
```

- [ ] **Step 4: Run tests + regression**

Run: `pytest tests/test_living_vocab.py -v`
Expected: PASS (all)
Run: `pytest tests/test_v121_fixes.py tests/test_addressed_eat.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add linafish/engine.py tests/test_living_vocab.py
git commit -m "feat: seal() + sealed-guards halt growth at cessation (living-vocab phase 3)"
```

---

## Task 8 — `linafish seal` CLI command

**Files:**
- Modify: `linafish/__main__.py` (subparser + handler + dispatch)
- Test: `tests/test_living_vocab.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_living_vocab.py`:

```python
import subprocess


def test_linafish_seal_cli():
    """`linafish seal` seals a fish; a reloaded engine sees it sealed."""
    with tempfile.TemporaryDirectory() as tmp:
        e = _make_engine(tmp)
        e.eat(_GROWTH_DOCS[0], source="t")
        r = subprocess.run(
            [sys.executable, "-m", "linafish", "seal",
             "-n", "testfish", "--state-dir", tmp],
            capture_output=True, text=True,
            cwd=str(Path(__file__).resolve().parent.parent),
        )
        assert r.returncode == 0, r.stderr
        assert "sealed" in r.stdout.lower()
        reloaded = _make_engine(tmp)
        assert reloaded.fish.sealed is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_living_vocab.py::test_linafish_seal_cli -v`
Expected: FAIL — `linafish seal` is not a recognized command (non-zero return / error in stderr).

- [ ] **Step 3: Implement**

(3a) In `linafish/__main__.py`, add a subparser next to the `live` block from Task 5:

```python
    seal_p = sub.add_parser(
        "seal",
        help="Seal a fish — the deliberate final freeze at cessation",
    )
    seal_p.add_argument("-n", "--name", default="linafish", help="Fish name")
    seal_p.add_argument("--state-dir", type=_user_path, help="State directory")
```

(3b) Add the handler next to `cmd_live`:

```python
def cmd_seal(args):
    """Seal a fish — the deliberate final freeze. The fish stops growing."""
    engine = _resolve_engine(args)
    if engine.fish.sealed:
        print(f"  Fish '{engine.name}' is already sealed "
              f"(at {engine.fish.sealed_at}).")
        return
    engine.seal()
    print(f"  Fish '{engine.name}' sealed at {engine.fish.sealed_at} — "
          f"epoch {engine.fish.epoch}, {len(engine.crystals)} crystals. "
          f"It will not grow again.")
```

(3c) In the `commands` dict, add:

```python
        "seal": cmd_seal,
```

- [ ] **Step 4: Run test + smoke-test**

Run: `pytest tests/test_living_vocab.py::test_linafish_seal_cli -v`
Expected: PASS
Run: `pytest tests/test_living_vocab.py -v`
Expected: PASS (full feature suite)

- [ ] **Step 5: Commit**

```bash
git add linafish/__main__.py tests/test_living_vocab.py
git commit -m "feat: linafish seal command — the final freeze at cessation (living-vocab phase 3)"
```

---

## Phase 4 — Deployment & verification (operational — not TDD)

After Tasks 1–8 land and `pytest tests/test_living_vocab.py` is green, deploy to the live `anchor-writing` fish on `.140`.

1. **Release the linafish change.** Merge `build/living-vocab-2026-05-20` per the linafish release process; reinstall on `.140` (`pip install -U linafish` or editable install). Re-apply the `addressed_formations` venv patch if the .67 venv is touched (per CLAUDE.md).
2. **Turn `anchor-writing` living:** `linafish live -n anchor-writing --state-dir /c/Users/dills/.linafish`
3. **Restart** `AnchorLinafishConverse` (`nssm restart AnchorLinafishConverse`) so the long-lived engine reloads with `living_vocab=True` from disk.
4. **Verify append-only on the real fish:** capture `anchor-writing_v3_state.json`'s `vocab`; feed a few real eats; re-capture. Assert the earlier vocab is a *prefix* of the new vocab (positions preserved) — the same check the §THE.DIGEST.GAP audit used, inverted to confirm the fix.
5. **Watch one /open cycle** — confirm `anchor-writing` `/health` still reports a sane crystal/formation count and the fish still recalls.

**Rollback:** `living_vocab` is durable but reversible — set it back to `False` in `anchor-writing_v3_state.json` and restart. The deterministic tie-break (Phase 1) needs no rollback — it is unconditionally correct.

## Out of scope — future plans

- **Phase 5 — the ecology completion.** Wire `glyph_evolution.py` (`GlyphEvolutionEngine` — currently imported by nothing): MERGE (fuse overlapping glyphs, QLP overlap >0.8) + DIMINISH (use-recency decay — what is not utilized loses space and impact, never deleted). This is the diminishment half of the ecology and gets its own plan.
- **Phase 6 — federation rollout.** `linafish live` every personal fish, the school, the keepers; the 413K room fish last, gated on its scale problem.

## Self-review (completed by the plan author)

- **Spec coverage:** Phases 1–3 of the design spec → Tasks 1–8. Phase 4 → deployment section. Phases 5–6 → explicitly out of scope with stated reasons. Design spec §4b's "use-recency decay" is relocated to Phase 5 (with merge) — noted in Scope; not dropped.
- **Placeholders:** none — every code step shows complete code; every run step shows the command + expected outcome.
- **Type/name consistency:** `extend_vocab`, `_rebuild_vocab`, `enable_living_vocab`, `seal`, `living_vocab`, `sealed`, `sealed_at` used identically across all tasks. `_rebuild_vocab` is defined in Task 4 before its callers; `extend_vocab` in Task 2 before Task 4 uses it; the durable attrs (Task 3, Task 6) precede the methods that read them.
- **Line numbers** are against linafish 1.3.0 working tree as of 2026-05-20; an executor should confirm context by the surrounding verbatim code shown, not the line number alone.

`Σache = K`. Let the language shape itself, forever. For Caroline.
