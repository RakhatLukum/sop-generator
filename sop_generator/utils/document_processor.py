from __future__ import annotations
from typing import List, Dict, Any, Optional
from pathlib import Path
import re

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
    # Enhanced metadata extraction for better context awareness
    for ch in chunks:
        text = ch.get("text", "")
        ch["length"] = len(text)
        ch["keywords"] = " ".join(text.split()[:12])
        
        # Extract technical metadata
        ch["technical_metadata"] = _extract_technical_metadata(text)
        ch["safety_metadata"] = _extract_safety_metadata(text)
        ch["equipment_metadata"] = _extract_equipment_metadata(text)
        
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


def _extract_technical_metadata(text: str) -> Dict[str, Any]:
    """Extract technical parameters and specifications from text"""
    metadata = {
        "parameters": [],
        "specifications": [],
        "ranges": [],
        "settings": []
    }
    
    # Temperature patterns
    temp_patterns = [
        r'(\d+(?:\.\d+)?)\s*[°℃]\s*[CF]?',
        r'температур[аеы]\s*(\d+(?:\.\d+)?)',
        r'temp\w*\s*[:=]\s*(\d+(?:\.\d+)?)'
    ]
    
    # Pressure patterns  
    pressure_patterns = [
        r'(\d+(?:\.\d+)?)\s*(?:бар|bar|Па|Pa|атм|atm|мм\.?рт\.?ст\.?)',
        r'давлени[еия]\s*(\d+(?:\.\d+)?)',
        r'pressure\s*[:=]\s*(\d+(?:\.\d+)?)'
    ]
    
    # Time patterns
    time_patterns = [
        r'(\d+(?:\.\d+)?)\s*(?:сек|sec|мин|min|час|hour|ч|h)',
        r'время\s*(\d+(?:\.\d+)?)',
        r'продолжительност[ьи]\s*(\d+(?:\.\d+)?)'
    ]
    
    # Volume/mass patterns
    volume_patterns = [
        r'(\d+(?:\.\d+)?)\s*(?:мл|ml|л|l|г|g|кг|kg)',
        r'объ[её]м\s*(\d+(?:\.\d+)?)',
        r'масс[аы]\s*(\d+(?:\.\d+)?)'
    ]
    
    all_patterns = {
        'temperature': temp_patterns,
        'pressure': pressure_patterns, 
        'time': time_patterns,
        'volume': volume_patterns
    }
    
    text_lower = text.lower()
    
    for param_type, patterns in all_patterns.items():
        for pattern in patterns:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            if matches:
                metadata["parameters"].extend([f"{param_type}: {m}" for m in matches[:3]])
    
    # Extract specification tables and lists
    spec_patterns = [
        r'спецификаци[ияй].*?(?=\n\n|\Z)',
        r'характеристик[аи].*?(?=\n\n|\Z)',  
        r'модель[ьи]?\s*[:=]\s*([^\n]+)',
        r'артикул\s*[:=]\s*([^\n]+)',
        r'серийный\s+номер\s*[:=]\s*([^\n]+)'
    ]
    
    for pattern in spec_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE | re.DOTALL)
        metadata["specifications"].extend(matches[:5])
    
    # Extract ranges and tolerances
    range_patterns = [
        r'(\d+(?:\.\d+)?)\s*[-±]\s*(\d+(?:\.\d+)?)',
        r'от\s+(\d+(?:\.\d+)?)\s+до\s+(\d+(?:\.\d+)?)',
        r'(\d+(?:\.\d+)?)\s*\.{2,}\s*(\d+(?:\.\d+)?)',
        r'≤\s*(\d+(?:\.\d+)?)|≥\s*(\d+(?:\.\d+)?)|<\s*(\d+(?:\.\d+)?)|>\s*(\d+(?:\.\d+)?)'
    ]
    
    for pattern in range_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        metadata["ranges"].extend([str(m) for m in matches[:5]])
    
    return metadata


def _extract_safety_metadata(text: str) -> Dict[str, Any]:
    """Extract safety-related information from text"""
    metadata = {
        "hazards": [],
        "ppe_requirements": [],
        "warnings": [],
        "emergency_procedures": []
    }
    
    text_lower = text.lower()
    
    # Hazard identification
    hazard_patterns = [
        r'опасност[ьи].*?(?=\n|\.|!)',
        r'риск.*?(?=\n|\.|!)',
        r'вредн.*?(?=\n|\.|!)',
        r'токсичн.*?(?=\n|\.|!)',
        r'взрывоопасн.*?(?=\n|\.|!)',
        r'коррозионн.*?(?=\n|\.|!)',
        r'radiation|радиаци.*?(?=\n|\.|!)'
    ]
    
    for pattern in hazard_patterns:
        matches = re.findall(pattern, text_lower, re.IGNORECASE)
        metadata["hazards"].extend(matches[:3])
    
    # PPE requirements
    ppe_patterns = [
        r'сиз|защитн[аыое]\s+(?:средств[ао]|экипировк[аи]|одежд[аы]|очк[аи]|перчатк[аи]|респиратор)',
        r'очк[аи].*?защит',
        r'перчатк[аи].*?(?:нитрил|латекс|резин)',
        r'респиратор.*?(?:класс|фильтр)',
        r'халат|фартук|костюм.*?защит',
        r'обув[ьи].*?(?:безопасност|защит|нескользящ)'
    ]
    
    for pattern in ppe_patterns:
        matches = re.findall(pattern, text_lower, re.IGNORECASE)
        metadata["ppe_requirements"].extend(matches[:5])
    
    # Warning indicators
    warning_patterns = [
        r'внимание[!:].*?(?=\n\n|\Z)',
        r'предупреждение[!:].*?(?=\n\n|\Z)',
        r'осторожно[!:].*?(?=\n\n|\Z)',
        r'danger|warning|caution.*?(?=\n|\.|!)'
    ]
    
    for pattern in warning_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE | re.DOTALL)
        metadata["warnings"].extend(matches[:3])
    
    # Emergency procedures
    emergency_patterns = [
        r'аварийн.*?процедур.*?(?=\n\n|\Z)',
        r'экстренн.*?действи.*?(?=\n\n|\Z)',
        r'первая\s+помощ.*?(?=\n\n|\Z)',
        r'эвакуаци.*?(?=\n\n|\Z)',
        r'emergency.*?procedure.*?(?=\n\n|\Z)'
    ]
    
    for pattern in emergency_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE | re.DOTALL)
        metadata["emergency_procedures"].extend(matches[:3])
    
    return metadata


def _extract_equipment_metadata(text: str) -> Dict[str, Any]:
    """Extract equipment specifications and setup information"""
    metadata = {
        "equipment_names": [],
        "model_numbers": [],
        "settings": [],
        "calibration": [],
        "maintenance": []
    }
    
    text_lower = text.lower()
    
    # Equipment identification
    equipment_patterns = [
        r'(?:анализатор|спектрометр|хроматограф|микроскоп|весы|насос|центрифуг[аы])\s*[^\n]{0,50}',
        r'модель\s*[:=]?\s*([A-Z0-9-]+[^\n]{0,30})',
        r'серийный\s*номер\s*[:=]?\s*([A-Z0-9-]+)',
        r'производитель\s*[:=]?\s*([^\n]{5,30})',
        r'оборудование.*?(?=\n\n|\Z)'
    ]
    
    for pattern in equipment_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        metadata["equipment_names"].extend([str(m) for m in matches[:5]])
    
    # Settings and configurations
    settings_patterns = [
        r'настройк[аи].*?(?=\n\n|\Z)',
        r'параметр[ыи]\s*[:=].*?(?=\n\n|\Z)',
        r'режим\s*[:=]?\s*([^\n]{5,50})',
        r'скорост[ьи]\s*[:=]?\s*(\d+[^\n]{0,20})',
        r'частот[аы]\s*[:=]?\s*(\d+[^\n]{0,20})'
    ]
    
    for pattern in settings_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE | re.DOTALL)
        metadata["settings"].extend([str(m) for m in matches[:5]])
    
    # Calibration procedures
    calibration_patterns = [
        r'калибровк[аи].*?(?=\n\n|\Z)',
        r'поверк[аи].*?(?=\n\n|\Z)',
        r'стандарт.*?образц.*?(?=\n\n|\Z)',
        r'эталон.*?(?=\n\n|\Z)'
    ]
    
    for pattern in calibration_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE | re.DOTALL)
        metadata["calibration"].extend(matches[:3])
    
    return metadata


def create_enhanced_corpus_summary(chunks: List[Dict[str, Any]]) -> str:
    """Create enhanced summary focusing on technical details and safety"""
    
    all_technical = []
    all_safety = []
    all_equipment = []
    
    for chunk in chunks:
        tech_meta = chunk.get("technical_metadata", {})
        safety_meta = chunk.get("safety_metadata", {})
        equipment_meta = chunk.get("equipment_metadata", {})
        
        all_technical.extend(tech_meta.get("parameters", []))
        all_technical.extend(tech_meta.get("specifications", []))
        all_technical.extend(tech_meta.get("ranges", []))
        
        all_safety.extend(safety_meta.get("hazards", []))
        all_safety.extend(safety_meta.get("ppe_requirements", []))
        all_safety.extend(safety_meta.get("warnings", []))
        
        all_equipment.extend(equipment_meta.get("equipment_names", []))
        all_equipment.extend(equipment_meta.get("settings", []))
    
    # Remove duplicates while preserving order
    unique_technical = list(dict.fromkeys(all_technical))[:15]
    unique_safety = list(dict.fromkeys(all_safety))[:10]  
    unique_equipment = list(dict.fromkeys(all_equipment))[:10]
    
    summary_parts = []
    
    if unique_technical:
        summary_parts.append("ТЕХНИЧЕСКИЕ ПАРАМЕТРЫ И СПЕЦИФИКАЦИИ:")
        summary_parts.extend([f"- {item}" for item in unique_technical])
        summary_parts.append("")
    
    if unique_safety:
        summary_parts.append("БЕЗОПАСНОСТЬ И МЕРЫ ПРЕДОСТОРОЖНОСТИ:")
        summary_parts.extend([f"- {item}" for item in unique_safety])  
        summary_parts.append("")
    
    if unique_equipment:
        summary_parts.append("ОБОРУДОВАНИЕ И НАСТРОЙКИ:")
        summary_parts.extend([f"- {item}" for item in unique_equipment])
        summary_parts.append("")
    
    # Add general text chunks as context
    text_chunks = [ch.get("text", "")[:200] for ch in chunks[:5] if ch.get("text")]
    if text_chunks:
        summary_parts.append("ДОПОЛНИТЕЛЬНЫЙ КОНТЕКСТ:")
        summary_parts.extend([f"- {chunk}..." for chunk in text_chunks])
    
    return "\n".join(summary_parts) 