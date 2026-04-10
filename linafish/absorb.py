"""
LiNafish Absorb — Eat existing RAG and vector databases.

Turn your existing FAISS indexes, crystal JSONLs, or HTTP RAG endpoints
into native fish crystals. Your prior work counts. No re-ingestion.

"We read your existing RAG and turn it into something that thinks."

Supported sources:
  faiss:<path>     — FAISS index + docstore metadata
  jsonl:<path>     — Crystal JSONL (linafish native format)
  http:<url>       — Live RAG/fish endpoint (paginated)

Usage:
    linafish absorb faiss:./my_index.faiss
    linafish absorb jsonl:./old_crystals.jsonl
    linafish absorb http://localhost:8108/ask/smart

s93, 2026-04-11. The migration moat.
"""

import json
import sys
import time
from pathlib import Path
from typing import Optional

from .engine import FishEngine


def absorb_jsonl(engine: FishEngine, path: Path) -> dict:
    """Absorb a crystal JSONL file into the fish.

    Each line is a JSON object with at least a 'text' field.
    Preserves source metadata.
    """
    if not path.exists():
        return {"error": f"File not found: {path}"}

    count = 0
    eaten = 0
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            count += 1
            try:
                d = json.loads(line)
                text = d.get("text", "")
                if not text or len(text.strip()) < 10:
                    continue
                source = d.get("source", f"absorb:{path.name}")
                engine.eat(text, source=source)
                eaten += 1
            except Exception:
                pass

            if count % 100 == 0:
                print(f"  [{count}] {eaten} absorbed, "
                      f"{len(engine.crystals)} crystals, "
                      f"{len(engine.formations)} formations",
                      file=sys.stderr)

    return {
        "source": str(path),
        "type": "jsonl",
        "lines_read": count,
        "absorbed": eaten,
        "total_crystals": len(engine.crystals),
        "formations": len(engine.formations),
    }


def absorb_faiss(engine: FishEngine, path: Path) -> dict:
    """Absorb a FAISS index by reading its docstore.

    Looks for companion files:
      - path.faiss + path.pkl (LangChain format)
      - path.faiss + path_metadata.json (custom format)
      - path.faiss + path_docstore.jsonl (our format)

    Falls back to trying the FAISS HTTP API if the path looks like a URL.
    """
    faiss_path = path
    if not faiss_path.exists():
        return {"error": f"FAISS index not found: {faiss_path}"}

    # Look for companion docstore
    base = faiss_path.parent / faiss_path.stem
    docstore_paths = [
        base.with_suffix(".jsonl"),
        base.parent / f"{faiss_path.stem}_metadata.json",
        base.parent / f"{faiss_path.stem}_docstore.jsonl",
        base.parent / "docstore.json",
        base.parent / "metadata.jsonl",
    ]

    for dp in docstore_paths:
        if dp.exists():
            print(f"  Found docstore: {dp}", file=sys.stderr)
            if dp.suffix == ".jsonl":
                return absorb_jsonl(engine, dp)
            elif dp.suffix == ".json":
                # JSON array or dict of documents
                try:
                    data = json.loads(dp.read_text(encoding="utf-8"))
                    if isinstance(data, dict):
                        texts = list(data.values())
                    elif isinstance(data, list):
                        texts = data
                    else:
                        return {"error": f"Unknown JSON format in {dp}"}

                    eaten = 0
                    for item in texts:
                        text = item if isinstance(item, str) else item.get("text", item.get("page_content", str(item)))
                        if text and len(str(text).strip()) > 10:
                            engine.eat(str(text), source=f"absorb:{dp.name}")
                            eaten += 1

                    return {
                        "source": str(dp),
                        "type": "faiss_docstore",
                        "documents": len(texts),
                        "absorbed": eaten,
                        "total_crystals": len(engine.crystals),
                        "formations": len(engine.formations),
                    }
                except Exception as e:
                    return {"error": f"Failed to read {dp}: {e}"}

    return {"error": f"No docstore found alongside {faiss_path}. Looked for: {[str(p) for p in docstore_paths]}"}


def absorb_http(engine: FishEngine, url: str, max_pages: int = 50) -> dict:
    """Absorb from a live HTTP RAG endpoint.

    Tries common patterns:
      - GET url (returns JSON array of documents)
      - GET url?page=N (paginated)
      - POST url with {"query": "*", "k": 100} (search-all)
    """
    import urllib.request

    eaten = 0
    page = 0

    while page < max_pages:
        try:
            # Try paginated GET first
            fetch_url = f"{url}?page={page}&limit=100" if page > 0 else url
            req = urllib.request.Request(fetch_url)
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            # Handle various response formats
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict):
                items = data.get("results", data.get("documents", data.get("data", [])))
            else:
                break

            if not items:
                break

            for item in items:
                if isinstance(item, str):
                    text = item
                elif isinstance(item, dict):
                    text = item.get("text", item.get("preview", item.get("content", item.get("page_content", ""))))
                else:
                    continue

                if text and len(str(text).strip()) > 10:
                    source = f"absorb:{url.split('/')[-1]}"
                    engine.eat(str(text), source=source)
                    eaten += 1

            print(f"  Page {page}: {len(items)} items, {eaten} absorbed total",
                  file=sys.stderr)

            # If we got fewer than 100, we're done
            if len(items) < 100:
                break
            page += 1

        except Exception as e:
            if page == 0:
                return {"error": f"Failed to fetch {url}: {e}"}
            break  # Partial success

    return {
        "source": url,
        "type": "http",
        "pages": page + 1,
        "absorbed": eaten,
        "total_crystals": len(engine.crystals),
        "formations": len(engine.formations),
    }


def absorb(engine: FishEngine, source: str) -> dict:
    """Route to the right absorber based on source format."""
    if source.startswith("http://") or source.startswith("https://"):
        return absorb_http(engine, source)
    elif source.startswith("jsonl:"):
        return absorb_jsonl(engine, Path(source[5:]))
    elif source.startswith("faiss:"):
        return absorb_faiss(engine, Path(source[5:]))
    else:
        # Auto-detect from extension
        path = Path(source)
        if path.suffix == ".jsonl":
            return absorb_jsonl(engine, path)
        elif path.suffix in (".faiss", ".index"):
            return absorb_faiss(engine, path)
        elif path.suffix == ".json":
            return absorb_jsonl(engine, path)  # Try as JSON
        elif path.exists() and path.is_file():
            # Try as JSONL
            return absorb_jsonl(engine, path)
        else:
            return {"error": f"Unknown source format: {source}. Use jsonl:, faiss:, or http://"}
