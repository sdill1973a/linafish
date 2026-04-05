"""
Ingest — the mouth of the fish.

Reads files, extracts text, chunks by natural boundaries.
The fish eats everything: .md, .txt, .pdf, .docx, .json, .py.
Each file is an "exchange" — R(n) grows with each one ingested.

The chunking is semantic, not mechanical. A 512-token window
doesn't know where meaning lives. Headers, paragraphs, and
topic shifts do.
"""

from __future__ import annotations


import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Chunk:
    """A unit of ingested content."""
    text: str
    source: str           # file path
    section: str = ""     # header/section name if available
    chunk_type: str = ""  # "narrative", "data", "code", "metadata"
    position: int = 0     # order within source file


def read_markdown(path: Path) -> list[Chunk]:
    """Read a markdown file, chunk by headers."""
    text = path.read_text(encoding="utf-8", errors="replace")
    chunks = []
    current_section = ""
    current_lines = []
    position = 0

    for line in text.split("\n"):
        if line.startswith("#"):
            # Save previous section
            if current_lines:
                body = "\n".join(current_lines).strip()
                if body and len(body) > 20:
                    chunks.append(Chunk(
                        text=body,
                        source=str(path),
                        section=current_section,
                        chunk_type="narrative",
                        position=position,
                    ))
                    position += 1
            current_section = line.lstrip("#").strip()
            current_lines = [line]
        else:
            current_lines.append(line)

    # Last section
    if current_lines:
        body = "\n".join(current_lines).strip()
        if body and len(body) > 20:
            chunks.append(Chunk(
                text=body,
                source=str(path),
                section=current_section,
                chunk_type="narrative",
                position=position,
            ))

    # If no headers found, chunk by paragraphs
    if not chunks:
        chunks = chunk_by_paragraphs(text, str(path))

    return chunks


def read_text(path: Path) -> list[Chunk]:
    """Read a plain text file, chunk by paragraphs."""
    text = path.read_text(encoding="utf-8", errors="replace")
    return chunk_by_paragraphs(text, str(path))


def read_pdf(path: Path) -> list[Chunk]:
    """Read a PDF file. Uses PyMuPDF if available, falls back to basic extraction."""
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(str(path))
        chunks = []
        for page_num, page in enumerate(doc):
            text = page.get_text()
            if text.strip():
                # Try to split by apparent sections
                sections = re.split(r'\n(?=[A-Z][A-Z\s]{5,})', text)
                for i, section in enumerate(sections):
                    section = section.strip()
                    if section and len(section) > 30:
                        chunks.append(Chunk(
                            text=section,
                            source=str(path),
                            section=f"page_{page_num + 1}",
                            chunk_type="narrative",
                            position=page_num * 100 + i,
                        ))
        doc.close()
        return chunks
    except ImportError:
        # Fallback: try pdfplumber
        try:
            import pdfplumber
            chunks = []
            with pdfplumber.open(str(path)) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    text = page.extract_text()
                    if text and text.strip() and len(text.strip()) > 30:
                        chunks.append(Chunk(
                            text=text.strip(),
                            source=str(path),
                            section=f"page_{page_num + 1}",
                            chunk_type="narrative",
                            position=page_num,
                        ))
            return chunks
        except ImportError:
            print(f"  [skip] No PDF reader available for {path.name}")
            return []


def read_docx(path: Path) -> list[Chunk]:
    """Read a Word document."""
    try:
        from docx import Document
        doc = Document(str(path))
        chunks = []
        current_section = ""
        current_lines = []
        position = 0

        for para in doc.paragraphs:
            text = para.text.strip()
            if not text:
                continue

            # Detect headers by style
            if para.style and para.style.name and "Heading" in para.style.name:
                if current_lines:
                    body = "\n".join(current_lines)
                    if len(body) > 20:
                        chunks.append(Chunk(
                            text=body,
                            source=str(path),
                            section=current_section,
                            chunk_type="narrative",
                            position=position,
                        ))
                        position += 1
                current_section = text
                current_lines = []
            else:
                current_lines.append(text)

        if current_lines:
            body = "\n".join(current_lines)
            if len(body) > 20:
                chunks.append(Chunk(
                    text=body,
                    source=str(path),
                    section=current_section,
                    chunk_type="narrative",
                    position=position,
                ))

        if not chunks:
            # No structure found, dump as one chunk
            all_text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
            if all_text and len(all_text) > 20:
                chunks.append(Chunk(
                    text=all_text,
                    source=str(path),
                    section="",
                    chunk_type="narrative",
                    position=0,
                ))

        return chunks
    except ImportError:
        print(f"  [skip] python-docx not installed for {path.name}")
        return []


def read_json(path: Path) -> list[Chunk]:
    """Read a JSON file — tool definitions, configs, schemas."""
    import json
    text = path.read_text(encoding="utf-8", errors="replace")
    try:
        data = json.loads(text)
        # Pretty-print for readability
        formatted = json.dumps(data, indent=2)
        return [Chunk(
            text=formatted,
            source=str(path),
            section="",
            chunk_type="data",
            position=0,
        )]
    except json.JSONDecodeError:
        return [Chunk(text=text, source=str(path), chunk_type="data")]


def read_python(path: Path) -> list[Chunk]:
    """Read a Python file, chunk by class/function definitions."""
    text = path.read_text(encoding="utf-8", errors="replace")
    chunks = []
    current_block = []
    current_name = path.name
    position = 0

    for line in text.split("\n"):
        if re.match(r'^(class |def |async def )', line):
            if current_block:
                body = "\n".join(current_block)
                if len(body) > 30:
                    chunks.append(Chunk(
                        text=body,
                        source=str(path),
                        section=current_name,
                        chunk_type="code",
                        position=position,
                    ))
                    position += 1
            current_name = line.split("(")[0].replace("class ", "").replace("def ", "").replace("async def ", "").strip()
            current_block = [line]
        else:
            current_block.append(line)

    if current_block:
        body = "\n".join(current_block)
        if len(body) > 30:
            chunks.append(Chunk(
                text=body,
                source=str(path),
                section=current_name,
                chunk_type="code",
                position=position,
            ))

    return chunks


def chunk_by_paragraphs(text: str, source: str) -> list[Chunk]:
    """Split text into paragraph-level chunks."""
    paragraphs = re.split(r'\n\s*\n', text)
    chunks = []
    for i, para in enumerate(paragraphs):
        para = para.strip()
        if para and len(para) > 20:
            chunks.append(Chunk(
                text=para,
                source=source,
                section="",
                chunk_type="narrative",
                position=i,
            ))
    return chunks


# Reader dispatch
READERS = {
    ".md": read_markdown,
    ".txt": read_text,
    ".pdf": read_pdf,
    ".docx": read_docx,
    ".json": read_json,
    ".py": read_python,
}


def ingest_file(path: Path) -> list[Chunk]:
    """Ingest a single file."""
    suffix = path.suffix.lower()
    reader = READERS.get(suffix)
    if reader is None:
        # Try as plain text
        try:
            return read_text(path)
        except Exception:
            return []
    return reader(path)


def ingest_directory(
    directory: Path,
    extensions: Optional[set[str]] = None,
    recursive: bool = True,
) -> list[Chunk]:
    """Ingest all files in a directory.

    Each file is an exchange. R(n) grows.
    """
    if extensions is None:
        extensions = set(READERS.keys())

    all_chunks = []
    pattern = "**/*" if recursive else "*"

    files = sorted(directory.glob(pattern))
    files = [f for f in files if f.is_file() and f.suffix.lower() in extensions]

    print(f"Ingesting {len(files)} files from {directory}")

    for i, file_path in enumerate(files, 1):
        print(f"  [{i}/{len(files)}] {file_path.name}", end="")
        try:
            chunks = ingest_file(file_path)
            print(f" -> {len(chunks)} chunks")
            all_chunks.extend(chunks)
        except Exception as e:
            print(f" -> ERROR: {e}")

    print(f"Total: {len(all_chunks)} chunks from {len(files)} files")
    return all_chunks
