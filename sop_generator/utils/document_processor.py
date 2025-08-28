from __future__ import annotations
from typing import List, Dict, Any
from pathlib import Path

import io
import pandas as pd
from PyPDF2 import PdfReader
from docx import Document
from pdf2image import convert_from_path
import pytesseract
from PIL import Image


SUPPORTED_EXTS = {".pdf", ".docx", ".xlsx", ".xls"}


def parse_documents_to_chunks(file_paths: List[str], target_chunk_size: int = 1200, overlap: int = 150) -> List[Dict[str, Any]]:
    chunks: List[Dict[str, Any]] = []
    for p in file_paths:
        path = Path(p)
        if not path.exists() or path.suffix.lower() not in SUPPORTED_EXTS:
            continue
        if path.suffix.lower() == ".pdf":
            chunks.extend(_parse_pdf(path, target_chunk_size, overlap))
        elif path.suffix.lower() == ".docx":
            chunks.extend(_parse_docx(path, target_chunk_size, overlap))
        else:
            chunks.extend(_parse_excel(path))
    # add lightweight index fields: length and keywords heuristic (first words)
    for ch in chunks:
        text = ch.get("text", "")
        ch["length"] = len(text)
        ch["keywords"] = " ".join(text.split()[:12])
    return chunks


def _chunk_text(text: str, target: int, overlap: int) -> List[str]:
    text = text.strip()
    if not text:
        return []
    if len(text) <= target:
        return [text]
    parts: List[str] = []
    start = 0
    while start < len(text):
        end = min(start + target, len(text))
        parts.append(text[start:end])
        start = end - overlap
        if start < 0:
            start = 0
        if start >= len(text):
            break
        if end == len(text):
            break
    return parts


def _parse_pdf(path: Path, target_chunk_size: int, overlap: int) -> List[Dict[str, Any]]:
    chunks: List[Dict[str, Any]] = []
    try:
        reader = PdfReader(str(path))
        for page_idx, page in enumerate(reader.pages):
            text = (page.extract_text() or "").strip()
            images_text = ""
            if not text:
                # OCR whole page
                images = convert_from_path(str(path), first_page=page_idx + 1, last_page=page_idx + 1)
                for img in images:
                    images_text += "\n" + pytesseract.image_to_string(img, lang="eng+rus")
            # best-effort: mark image placeholders
            if page.images:
                images_text += "\n" + "\n".join([f"[IMAGE_PLACEHOLDER page={page_idx+1} name={getattr(im,'name','')}]" for im in page.images])
            combined = (text + "\n" + images_text).strip()
            for piece in _chunk_text(combined, target_chunk_size, overlap):
                chunks.append({
                    "source": f"{path.name}#p{page_idx+1}",
                    "type": "pdf-chunk",
                    "text": piece,
                })
    except Exception as e:
        chunks.append({"source": path.name, "type": "error", "text": f"PDF parse error: {e}"})
    return chunks


def _parse_docx(path: Path, target_chunk_size: int, overlap: int) -> List[Dict[str, Any]]:
    chunks: List[Dict[str, Any]] = []
    try:
        doc = Document(str(path))
        buffer: list[str] = []
        for para in doc.paragraphs:
            if para.text.strip():
                buffer.append(para.text.strip())
        text = "\n".join(buffer)
        for piece in _chunk_text(text, target_chunk_size, overlap):
            chunks.append({
                "source": path.name,
                "type": "docx-chunk",
                "text": piece,
            })
        for t_idx, table in enumerate(doc.tables):
            rows = []
            for row in table.rows:
                rows.append([cell.text.strip() for cell in row.cells])
            if rows:
                df = pd.DataFrame(rows)
                chunks.append({
                    "source": f"{path.name}#table{t_idx+1}",
                    "type": "table",
                    "text": df.to_csv(index=False, header=False),
                })
    except Exception as e:
        chunks.append({"source": path.name, "type": "error", "text": f"DOCX parse error: {e}"})
    return chunks


def _parse_excel(path: Path) -> List[Dict[str, Any]]:
    chunks: List[Dict[str, Any]] = []
    try:
        xls = pd.ExcelFile(str(path))
        for sheet_name in xls.sheet_names:
            df = xls.parse(sheet_name)
            csv_text = df.to_csv(index=False)
            chunks.append({
                "source": f"{path.name}#{sheet_name}",
                "type": "excel-sheet",
                "text": csv_text,
            })
    except Exception as e:
        chunks.append({"source": path.name, "type": "error", "text": f"Excel parse error: {e}"})
    return chunks 