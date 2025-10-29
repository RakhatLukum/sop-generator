"""Utility helpers for loading user-provided documents and splitting them into chunks."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Iterable, List


def parse_documents_to_chunks(paths: Iterable[str], *, max_chunk_size: int = 1500, overlap: int = 150) -> List[Dict[str, str]]:
    """Return a list of text chunks extracted from the provided documents.

    Parameters
    ----------
    paths:
        Iterable of file paths selected by the user.
    max_chunk_size:
        Maximum number of characters in a single chunk.
    overlap:
        Number of characters to keep as overlap between subsequent chunks.
    """

    chunks: List[Dict[str, str]] = []
    for raw_path in paths or []:
        if not raw_path:
            continue
        path = Path(raw_path)
        if not path.exists() or not path.is_file():
            continue

        try:
            text = _read_text_from_file(path)
        except Exception:
            continue

        for idx, chunk_text in enumerate(_split_text(text, max_chunk_size=max_chunk_size, overlap=overlap)):
            if not chunk_text:
                continue
            chunks.append({
                "source": str(path),
                "chunk_index": idx,
                "content": chunk_text,
            })
    return chunks


def _read_text_from_file(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".txt", ".md", ".markdown"}:
        return path.read_text(encoding="utf-8", errors="ignore")
    if suffix in {".json", ".yaml", ".yml"}:
        return path.read_text(encoding="utf-8", errors="ignore")
    if suffix in {".docx"}:
        return _read_docx(path)
    if suffix in {".pdf"}:
        return _read_pdf(path)
    if suffix in {".xlsx", ".xls"}:
        return _read_spreadsheet(path)
    # Fallback: treat as binary->text
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _read_docx(path: Path) -> str:
    try:
        from docx import Document
    except ImportError:
        return ""

    try:
        document = Document(str(path))
    except Exception:
        return ""

    paragraphs = [para.text.strip() for para in document.paragraphs if para.text.strip()]
    return "\n".join(paragraphs)


def _read_pdf(path: Path) -> str:
    try:
        from PyPDF2 import PdfReader
    except ImportError:
        return ""

    try:
        reader = PdfReader(str(path))
    except Exception:
        return ""

    pages: List[str] = []
    for page in reader.pages:
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        text = text.strip()
        if text:
            pages.append(text)
    return "\n".join(pages)


def _read_spreadsheet(path: Path) -> str:
    try:
        import pandas as pd  # type: ignore
    except ImportError:
        return ""

    try:
        sheets = pd.read_excel(str(path), sheet_name=None)
    except Exception:
        return ""

    blocks: List[str] = []
    for sheet_name, frame in sheets.items():
        blocks.append(f"Лист: {sheet_name}")
        try:
            csv_preview = frame.to_csv(index=False)
        except Exception:
            csv_preview = ""
        if csv_preview:
            blocks.append(csv_preview)
    return "\n".join(blocks)


def _split_text(text: str, *, max_chunk_size: int, overlap: int) -> List[str]:
    cleaned = (text or "").strip()
    if not cleaned:
        return []
    if len(cleaned) <= max_chunk_size:
        return [cleaned]

    chunks: List[str] = []
    start = 0
    length = len(cleaned)
    while start < length:
        end = min(start + max_chunk_size, length)
        candidate = cleaned[start:end]

        if end < length:
            local_break = max(candidate.rfind("\n\n"), candidate.rfind(". "), candidate.rfind(".\n"))
            if local_break != -1 and local_break > max_chunk_size * 0.5:
                end = start + local_break + 1
                candidate = cleaned[start:end]

        chunks.append(candidate.strip())
        if end >= length:
            break
        start = max(0, end - overlap)

    return [chunk for chunk in chunks if chunk]


__all__ = ["parse_documents_to_chunks"]

