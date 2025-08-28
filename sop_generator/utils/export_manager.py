from __future__ import annotations
from typing import Dict, Any, List
from docx import Document
from docx.shared import Pt
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
import re
from pathlib import Path


def populate_docx(document: Document, sop_meta: Dict[str, Any], sections: List[Dict[str, Any]]) -> Document:
    title = sop_meta.get("title", "СОП")
    number = sop_meta.get("number", "")

    document.add_heading(f"{title}", level=0)
    if number:
        document.add_paragraph(f"Номер: {number}")

    for idx, section in enumerate(sections, start=1):
        document.add_heading(f"{idx}. {section['title']}", level=1)
        body = section.get("content", "")
        
        # Split content into paragraphs and handle tables
        paragraphs = body.split("\n\n")
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
                
            # Check if it's a table
            if '|' in para and ('---' in para or '━' in para):
                # Handle markdown table
                lines = para.split('\n')
                table_data = []
                for line in lines:
                    if '|' in line and not (line.strip().startswith('|---') or line.strip().startswith('|━')):
                        cells = [cell.strip() for cell in line.split('|') if cell.strip()]
                        if cells:
                            table_data.append(cells)
                
                if table_data:
                    # Add table to document
                    table = document.add_table(rows=len(table_data), cols=len(table_data[0]) if table_data else 1)
                    table.style = 'Light Grid Accent 1'
                    for row_idx, row_data in enumerate(table_data):
                        for col_idx, cell_data in enumerate(row_data):
                            if col_idx < len(table.rows[row_idx].cells):
                                table.rows[row_idx].cells[col_idx].text = cell_data
            else:
                # Regular paragraph - handle basic markdown
                # Remove markdown formatting for DOCX (since DOCX handles styling differently)
                clean_para = re.sub(r'\*\*(.*?)\*\*', r'\1', para)  # Remove bold markers
                clean_para = re.sub(r'(?<!\*)\*([^*]+?)\*(?!\*)', r'\1', clean_para)  # Remove italic markers
                document.add_paragraph(clean_para)
    return document


def export_to_docx(document: Document, output_path: str) -> str:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    document.save(str(path))
    return str(path)


def export_to_pdf(sections: List[Dict[str, Any]], output_path: str, sop_meta: Dict[str, Any]) -> str:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    # Register DejaVu fonts for Cyrillic support
    try:
        pdfmetrics.registerFont(TTFont('DejaVu', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
        pdfmetrics.registerFont(TTFont('DejaVu-Bold', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'))
        font_name = 'DejaVu'
        font_bold = 'DejaVu-Bold'
    except:
        # Fallback to default fonts
        font_name = 'Helvetica'
        font_bold = 'Helvetica-Bold'
    
    # Use SimpleDocTemplate for better text handling
    doc = SimpleDocTemplate(str(path), pagesize=A4)
    styles = getSampleStyleSheet()
    
    # Create custom style that handles UTF-8
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_CENTER
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontSize=16,
        spaceAfter=12,
        alignment=TA_CENTER,
        fontName=font_bold
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading1'],
        fontSize=14,
        spaceAfter=8,
        spaceBefore=12,
        fontName=font_bold
    )
    
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=6,
        fontName=font_name
    )
    
    story = []
    
    # Add title and number
    title = sop_meta.get("title", "СОП")
    number = sop_meta.get("number", "")
    
    story.append(Paragraph(title, title_style))
    if number:
        story.append(Paragraph(f"Номер: {number}", body_style))
    # Add sections
    for idx, section in enumerate(sections, start=1):
        story.append(Paragraph(f"{idx}. {section['title']}", heading_style))
        content = section.get("content", "").strip()
        if content:
            # Split content into paragraphs and handle tables
            paragraphs = content.split('\n\n')
            for para in paragraphs:
                para = para.strip()
                if para:
                    # Check if it's a table
                    if '|' in para and ('---' in para or '━' in para):
                        # Convert Markdown table to ReportLab table
                        lines = para.split('\n')
                        table_data = []
                        for line in lines:
                            if '|' in line and not (line.strip().startswith('|---') or line.strip().startswith('|━')):
                                cells = [cell.strip() for cell in line.split('|') if cell.strip()]
                                if cells:
                                    table_data.append(cells)
                        
                        if table_data:
                            # Create proper table
                            table = Table(table_data)
                            table.setStyle(TableStyle([
                                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                                ('FONTNAME', (0, 0), (-1, 0), font_bold),
                                ('FONTNAME', (0, 1), (-1, -1), font_name),
                                ('FONTSIZE', (0, 0), (-1, -1), 9),
                                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                                ('GRID', (0, 0), (-1, -1), 1, colors.black)
                            ]))
                            story.append(table)
                            story.append(Spacer(1, 12))
                    else:
                        # Regular paragraph - handle markdown formatting
                        # Convert basic markdown to HTML for better rendering
                        formatted_para = para
                        # Handle bold text **text** -> <b>text</b>
                        import re
                        formatted_para = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', formatted_para)
                        # Handle italic text *text* -> <i>text</i>
                        formatted_para = re.sub(r'(?<!\*)\*([^*]+?)\*(?!\*)', r'<i>\1</i>', formatted_para)
                        # Handle line breaks
                        formatted_para = formatted_para.replace('\n', '<br/>')
                        
                        story.append(Paragraph(formatted_para, body_style))
                        story.append(Spacer(1, 6))
        story.append(Spacer(1, 12))
    
    # Build PDF
    doc.build(story)
    return str(path) 