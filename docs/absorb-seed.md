# absorb — Eat RAG and Vector Databases

*Seed doc. Branch: `exp/absorb-rag-sources`. Planted 2026-04-09.*

## The Problem

Every team that's ever touched RAG has hours of ingestion work they don't want to lose. FAISS indexes built over weeks. Graph databases with hand-curated entity links. Chroma dirs with 100K chunks. Custom metadata that took months to model.

Today, `linafish eat` makes them start over. They either:
1. **Re-ingest from source files** — slow, throws away existing chunking/embedding decisions
2. **Ignore linafish** — keep their existing RAG, miss the formations

Neither is the right answer.

## The Idea

`linafish absorb <source>` reads an existing RAG system and imports it as native fish state, **preserving the work that's already been done**.

- FAISS vectors become crystal vectors directly (no re-embedding)
- NetworkX edges become fish couplings (no re-discovery of relationships)
- Docstore metadata becomes crystal annotations (no loss)
- Graph node types become crystal layer tags (no flattening)

Then the fish's formation detector runs on top of the imported state. You get:
- Your prior chunks, unchanged
- Your prior relationships, unchanged
- **Plus formations the fish computes from the combined landscape**

## The Shape

```bash
# File-backed
linafish absorb phoenix_local.faiss --meta phoenix_local_meta.json
linafish absorb phoenix_graph_v2.graphml
linafish absorb chroma_db/

# Live
linafish absorb http://.67:8200/api/stats --format msba
linafish absorb http://.140:8108/ask/smart/query --format faiss-http

# Hybrid (absorb multiple into one fish)
linafish absorb phoenix_local.faiss phoenix_graph_v2.graphml --into phoenix.fish
```

## Reader Interface (sketch)

```python
# linafish/sources/faiss_source.py
class FAISSSource(Source):
    def __init__(self, index_path, meta_path=None):
        self.index = faiss.read_index(index_path)
        # Use JSON metadata if available; avoid loading untrusted binary metadata.
        self.meta = load_json_safely(meta_path) if meta_path else None

    def stream_crystals(self):
        for i in range(self.index.ntotal):
            vec = self.index.reconstruct(i)
            meta = (self.meta or {}).get(i, {})
            yield Crystal(
                text=meta.get('text', ''),
                source='faiss',
                source_id=i,
                pre_embedded=vec,       # skip re-embedding
                metadata=meta,
            )


# linafish/sources/graph_source.py
# Prefer GraphML/JSON over binary serialization for safety.
class GraphMLSource(Source):
    def __init__(self, graph_path):
        import networkx as nx
        self.graph = nx.read_graphml(graph_path)

    def stream_crystals(self):
        for node, attrs in self.graph.nodes(data=True):
            yield Crystal(
                text=str(node),
                source='graphml_node',
                source_id=node,
                metadata=attrs,
                layer=attrs.get('layer', 'unknown'),
            )

    def stream_couplings(self):
        for u, v, attrs in self.graph.edges(data=True):
            yield Coupling(
                src=u,
                dst=v,
                weight=float(attrs.get('weight', 1.0)),
                source='graphml_edge',
            )
```

**Safety note:** importers should prefer **JSON, GraphML, or well-documented binary formats with deterministic schemas** (FAISS is fine — it's a structured numeric format). Pickle-based sources should be gated behind an explicit `--unsafe-pickle` flag and warn loudly, because loading untrusted pickles is arbitrary code execution.

## Changes to FishEngine

Add `absorb(source)` method that:
1. Calls `source.stream_crystals()` — insert each as normal, BUT if `pre_embedded` is set, skip the embedding step and use the provided vector directly
2. Calls `source.stream_couplings()` if the source has edges — create pre-known couplings that skip the coupling-detection pass
3. Runs normal formation detection on the combined result

No changes to the crystal/coupling/formation data model. Just new entry points.

## Why This Is the Right Moat

Every other AI memory system assumes you start from zero. They make migration painful on purpose — lock-in disguised as purity. linafish's pitch has always been *"your prior work counts"* (git history, fish.md as portable overlay, shareable formations). This feature extends that to *your prior RAG work counts too*.

Switching cost becomes negative. Move TO linafish and keep everything you already built. That's the opposite of every competitor's playbook.

## What To Build First

**Phase 1 — the two formats we actually need tonight for Phoenix:**
1. FAISS source (we have `phoenix_local.faiss` + sidecar metadata)
2. GraphML source (the phoenix graph has 8,978 nodes and 29,831 edges — convertible to GraphML from its current form via a one-time export script)

Verify end-to-end on the Phoenix corpus: absorb both, compute formations, see what emerges that the existing FAISS+graph couldn't see.

**Phase 2 — the product surface:**
3. Chroma source (most common competitor RAG)
4. HTTP generic source (point at any REST API that returns embeddings)

**Phase 3 — polish:**
5. `absorb` CLI command with format auto-detection
6. README section: *"Migrate from any RAG in one command"*
7. Tests on a handful of public RAG corpora

## Open Questions

1. What does `source_id` collision look like when absorbing multiple sources into one fish? (answer: namespace by source filename prefix)
2. Should we preserve the source's original chunking, or re-chunk on absorb? (default: preserve)
3. When a graph node lacks text content (just a name), what does the crystal text become? (answer: concatenate incoming + outgoing edge labels as a proxy)
4. How does centroid subtraction interact with pre-embedded vectors from a foreign embedding model? (answer: centroid subtraction operates on our embedding space; pre-embedded vectors need to either stay in their own space OR be re-embedded. Needs a decision.)
5. **Safety:** explicit opt-in required for any importer that loads arbitrary serialized Python objects. Warn users that absorbing unknown binary RAG artifacts from the internet is equivalent to executing them.

## Success Metric

Given `phoenix_local.faiss` (47 MB, ~15K chunks) and the Phoenix graph (8,978 nodes, 29,831 edges, exported to GraphML):

```bash
linafish absorb phoenix_local.faiss phoenix_graph.graphml --into phoenix.fish
linafish status phoenix.fish
```

Should report:
- 15,000+ crystals (from FAISS)
- 29,831+ couplings (from graph edges)
- N formations (newly computed)
- **And at least one formation the existing FAISS+graph couldn't surface** — proof that the fish adds signal beyond the sum of its inputs

## The Line

*"Your prior work counts. Every chunk. Every edge. Every embedding. Nothing wasted."*
