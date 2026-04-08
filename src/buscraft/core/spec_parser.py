"""
BusCraft Spec Parser — Reads IP specification documents (PDF, Markdown, Text)
and converts them into clean, chunked text ready for AI analysis.
"""
from __future__ import annotations
from pathlib import Path
from typing import List
import re


def parse_spec(filepath: str) -> str:
    """Read a spec file and return its full text content.
    
    Supports:
      - .pdf  (via PyMuPDF)
      - .md   (plain read)
      - .txt  (plain read)
    """
    path = Path(filepath)
    
    if not path.exists():
        raise FileNotFoundError(f"Spec file not found: {filepath}")
    
    suffix = path.suffix.lower()
    
    if suffix == ".pdf":
        return _parse_pdf(path)
    elif suffix in (".md", ".txt", ".rst"):
        return _parse_text(path)
    else:
        # Try reading as plain text for unknown extensions
        return _parse_text(path)


def _parse_pdf(path: Path) -> str:
    """Extract text from a PDF using PyMuPDF."""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        raise ImportError(
            "PyMuPDF is required for PDF parsing. Install it with: pip install pymupdf"
        )
    
    doc = fitz.open(str(path))
    text_parts: List[str] = []
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text")
        
        if text.strip():
            text_parts.append(f"--- Page {page_num + 1} ---\n{text}")
        
        # Also extract tables if present (PyMuPDF can find structured content)
        tables = page.find_tables()
        if tables and tables.tables:
            for table in tables.tables:
                try:
                    rows = table.extract()
                    if rows:
                        table_text = _format_table(rows)
                        text_parts.append(f"[TABLE on Page {page_num + 1}]\n{table_text}")
                except Exception:
                    pass  # Skip malformed tables silently
    
    doc.close()
    
    raw_text = "\n\n".join(text_parts)
    return _clean_text(raw_text)


def _parse_text(path: Path) -> str:
    """Read a plain text or markdown file."""
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        raw_text = f.read()
    return _clean_text(raw_text)


def _format_table(rows: List[List]) -> str:
    """Convert a list of rows into a readable text table."""
    lines = []
    for row in rows:
        cells = [str(c).strip() if c else "" for c in row]
        lines.append(" | ".join(cells))
    return "\n".join(lines)


def _clean_text(text: str) -> str:
    """Normalize whitespace, remove junk characters, and clean up spec text."""
    # Remove non-printable characters except newlines/tabs
    text = re.sub(r'[^\x20-\x7E\n\t]', ' ', text)
    # Collapse multiple blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Collapse multiple spaces
    text = re.sub(r'[ \t]{2,}', ' ', text)
    return text.strip()


def chunk_text(text: str, max_tokens: int = 1200) -> List[str]:
    """Split text into chunks small enough for the local LLM's context window.
    
    Uses a rough heuristic of ~4 chars per token. Chunks are split at
    paragraph boundaries to keep context coherent.
    
    Args:
        text: The full cleaned spec text.
        max_tokens: Maximum tokens per chunk (leave room for prompts).
    
    Returns:
        List of text chunks.
    """
    max_chars = max_tokens * 4  # ~4 chars per token approximation
    
    # Split by double-newline (paragraphs) or page markers
    paragraphs = re.split(r'\n---\s*Page\s+\d+\s*---\n|\n\n', text)
    paragraphs = [p.strip() for p in paragraphs if p.strip()]
    
    chunks: List[str] = []
    current_chunk = ""
    
    for para in paragraphs:
        # If a single paragraph is too long, split it by sentences
        if len(para) > max_chars:
            sentences = re.split(r'(?<=[.!?])\s+', para)
            for sentence in sentences:
                if len(current_chunk) + len(sentence) + 1 > max_chars:
                    if current_chunk.strip():
                        chunks.append(current_chunk.strip())
                    current_chunk = sentence
                else:
                    current_chunk += " " + sentence
        elif len(current_chunk) + len(para) + 2 > max_chars:
            if current_chunk.strip():
                chunks.append(current_chunk.strip())
            current_chunk = para
        else:
            current_chunk += "\n\n" + para
    
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    
    return chunks
