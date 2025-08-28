from __future__ import annotations
from pathlib import Path
from typing import Any, Dict
import json
from docx import Document


def load_template(template_dir: str) -> tuple[Document, Dict[str, Any]]:
    base = Path(template_dir)
    docx_path = base / "sop_template.docx"
    styles_path = base / "styles.json"

    doc = Document(str(docx_path)) if docx_path.exists() else Document()

    styles: Dict[str, Any] = {}
    if styles_path.exists():
        try:
            styles = json.loads(styles_path.read_text(encoding="utf-8"))
        except Exception:
            styles = {}
    return doc, styles


def apply_styles(document: Document, styles: Dict[str, Any]) -> None:
    if not styles:
        return
    # Basic example: set default font
    default = styles.get("default_font")
    if default:
        for style in document.styles:
            try:
                if hasattr(style, "font"):
                    if default.get("name"):
                        style.font.name = default["name"]
                    if default.get("size"):
                        style.font.size = default["size"]
            except Exception:
                continue 