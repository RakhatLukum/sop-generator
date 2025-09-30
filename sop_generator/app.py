import os
import sys
import json
import tempfile
import time
from typing import List, Dict, Any

# Add parent directory to Python path for module resolution
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

import streamlit as st
import threading
from streamlit.runtime.scriptrunner import add_script_run_ctx
from datetime import datetime
import shutil

from sop_generator.agents.coordinator import (
    iterative_generate_until_approved,
)
from sop_generator.agents.sop_generator import build_sop_generator
from sop_generator.agents.critic import build_critic
from sop_generator.agents.sop_generator import build_generation_instruction
from sop_generator.utils.export_manager import export_to_docx, export_to_pdf, populate_docx
from sop_generator.utils.document_processor import parse_documents_to_chunks
from sop_generator.agents.document_parser import summarize_parsed_chunks
from sop_generator.utils.template_manager import load_template, apply_styles

# Enhanced conversation UI disabled in simplified mode
# from sop_generator.ui.dashboard_components import (
#     AgentConversationViewer, 
#     render_agent_interaction_analysis
# )

APP_TITLE = "SOP Generator (AutoGen + Streamlit)"


def _request_rerun(delay_seconds: float = 1.0) -> None:
    """Trigger a Streamlit rerun, compatible with multiple versions."""
    time.sleep(delay_seconds)
    rerun = getattr(st, "experimental_rerun", None) or getattr(st, "rerun", None)
    if rerun:
        rerun()


def init_session_state() -> None:
    if "meta" not in st.session_state:
        st.session_state.meta = {
            "title": "",
            "number": "",
            "equipment": "",
        }
    if "uploaded_files" not in st.session_state:
        st.session_state.uploaded_files = []
    if "sections" not in st.session_state:
        st.session_state.sections = []  # [{title, mode, prompt, content}]
    if "logs" not in st.session_state:
        st.session_state.logs = []
    if "parsed_chunks" not in st.session_state:
        st.session_state.parsed_chunks = []
    if "preview" not in st.session_state:
        st.session_state.preview = []  # sections with content
    if "running" not in st.session_state:
        st.session_state.running = False
    if "worker" not in st.session_state:
        st.session_state.worker = None


def add_log(message: str) -> None:
    # Be resilient when called from a background thread
    try:
        if "logs" not in st.session_state:
            st.session_state.logs = []
        st.session_state.logs.append(message)
        st.session_state.logs = st.session_state.logs[-500:]
        print(f"[SOP] {message}", flush=True)
    except Exception:
        # Best-effort: ignore logging errors from threads without context
        pass


def ui_home():
    st.header("Главная")
    col1, col2 = st.columns(2)
    with col1:
        st.session_state.meta["title"] = st.text_input("Название СОП", value=st.session_state.meta.get("title", ""))
        st.session_state.meta["number"] = st.text_input("Номер СОП", value=st.session_state.meta.get("number", ""))
        st.session_state.meta["equipment"] = st.text_input("Тип оборудования", value=st.session_state.meta.get("equipment", ""))
    with col2:
        st.markdown("Загрузка нормативных документов (PDF/DOCX/Excel)")
        uploads = st.file_uploader("Загрузите файлы", type=["pdf", "docx", "xlsx", "xls"], accept_multiple_files=True)
        if uploads:
            tmpdir = tempfile.mkdtemp(prefix="sop_docs_")
            paths = []
            for uf in uploads:
                p = os.path.join(tmpdir, uf.name)
                with open(p, "wb") as f:
                    f.write(uf.getbuffer())
                paths.append(p)
            st.session_state.uploaded_files = paths
            st.success(f"Загружено файлов: {len(paths)}")

    st.text_area("Описание структуры документа (опционально)", key="structure_hint")


def ui_sections():
    st.header("Конфигурация разделов")
    if st.button("Добавить раздел"):
        st.session_state.sections.append({
            "title": f"Раздел {len(st.session_state.sections)+1}",
            "mode": "ai",
            "prompt": "",
            "content": "",
        })
    for idx, section in enumerate(st.session_state.sections):
        with st.expander(f"{idx+1}. {section['title']}", expanded=False):
            section["title"] = st.text_input("Название", value=section["title"], key=f"title_{idx}")
            section["mode"] = st.selectbox(
                "Режим",
                options=["ai", "ai+doc", "manual"],
                index=["ai", "ai+doc", "manual"].index(section["mode"]),
                key=f"mode_{idx}"
            )
            section["prompt"] = st.text_area("Инструкция для генерации (подсказка)", value=section.get("prompt", ""), key=f"prompt_{idx}")
            
            # Add document upload for ai+doc mode
            if section["mode"] == "ai+doc":
                st.markdown("📁 **Загрузка справочных документов для этого раздела**")
                uploads = st.file_uploader(
                    f"Документы для раздела '{section['title']}'", 
                    type=["pdf", "docx", "xlsx", "xls", "txt"],
                    accept_multiple_files=True,
                    key=f"section_docs_{idx}",
                    help="Загрузите документы, которые будут использованы ИИ для генерации этого раздела"
                )
                if uploads:
                    import tempfile
                    tmpdir = tempfile.mkdtemp(prefix=f"sop_section_{idx}_")
                    paths = []
                    for uf in uploads:
                        p = os.path.join(tmpdir, uf.name)
                        with open(p, "wb") as f:
                            f.write(uf.getbuffer())
                        paths.append(p)
                    section["documents"] = paths
                    st.success(f"✅ Загружено файлов: {len(paths)} - {', '.join([uf.name for uf in uploads])}")
                else:
                    section["documents"] = section.get("documents", [])
                    
            elif section["mode"] == "manual":
                section["content"] = st.text_area("Контент раздела", value=section.get("content", ""), height=200, key=f"content_{idx}")
        st.session_state.sections[idx] = section


def ui_generate():
    st.header("Процесс генерации")
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("Запустить генерацию", type="primary", disabled=st.session_state.running):
            if st.session_state.worker and st.session_state.worker.is_alive():
                add_log("Уже выполняется задача. Подождите завершения.")
            else:
                st.session_state.running = True
                t = threading.Thread(target=run_generation_safe, daemon=True)
                add_script_run_ctx(t)
                st.session_state.worker = t
                t.start()
        if st.button("Остановить", help="Заглушка — остановка не реализована", disabled=not st.session_state.running):
            add_log("Остановка процесса (заглушка)")
    with col2:
        st.progress(min(len(st.session_state.preview) / max(len(st.session_state.sections), 1), 1.0))

    st.subheader("Лог агентов")
    st.text("\n".join(st.session_state.logs[-50:]))
    # Auto-refresh hint for long runs
    if st.session_state.running:
        st.caption("Задача выполняется... Интерфейс обновляется автоматически.")
        _request_rerun()


def ui_preview_and_export():
    st.header("Предварительный просмотр")
    st.session_state.preview = st.session_state.preview or [
        {"title": s["title"], "content": s.get("content", "")} for s in st.session_state.sections
    ]
    for idx, sec in enumerate(st.session_state.preview):
        with st.expander(f"{idx+1}. {sec['title']}", expanded=False):
            # Show formatted preview
            content = sec.get("content", "")
            if content:
                # Render markdown content with better table support
                st.markdown("**Форматированный просмотр:**")
                st.markdown(content, unsafe_allow_html=False)
                st.divider()
            # Allow editing in text area
            st.markdown("**Редактирование:**")
            new_value = st.text_area("Контент (Markdown поддерживается)", value=content, height=220, key=f"prev_content_{idx}", help="Используйте Markdown для форматирования. Таблицы: | Заголовок | Заголовок | \\n |-------|-------|")
            if not (new_value.strip() == "" and (content or "").strip() != ""):
                sec["content"] = new_value
        st.session_state.preview[idx] = sec

    st.subheader("Экспорт")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Экспорт в Word"):
            doc, styles = load_template(os.path.join(os.path.dirname(__file__), "templates"))
            apply_styles(doc, styles)
            doc = populate_docx(doc, st.session_state.meta, st.session_state.preview)
            out_path = export_to_docx(doc, os.path.join(tempfile.gettempdir(), "sop_generated.docx"))
            # Also save to project root for convenience
            try:
                project_root_copy = os.path.abspath(os.path.join(current_dir, "..", "sop_generated.docx"))
                shutil.copyfile(out_path, project_root_copy)
                st.info(f"Скопировано в: {project_root_copy}")
            except Exception:
                pass
            st.success(f"Сохранено: {out_path}")
            with open(out_path, "rb") as f:
                st.download_button("Скачать DOCX", f, file_name="sop_generated.docx", key="download_docx")
    with col2:
        if st.button("Экспорт в PDF"):
            out_path = export_to_pdf(st.session_state.preview, os.path.join(tempfile.gettempdir(), "sop_generated.pdf"), st.session_state.meta)
            st.success(f"Сохранено: {out_path}")
            with open(out_path, "rb") as f:
                st.download_button("Скачать PDF", f, file_name="sop_generated.pdf")
    with col3:
        # Build Markdown content and offer direct download (no saving to docs/)
        title = st.session_state.meta.get("title", "СОП") or "СОП"
        number = st.session_state.meta.get("number", "")
        md_lines = [f"# {title}", ""]
        if number:
            md_lines.append(f"Номер: {number}")
            md_lines.append("")
        for idx, sec in enumerate(st.session_state.preview, start=1):
            md_lines.append(f"## {idx}. {sec['title']}")
            md_lines.append("")
            md_lines.append(sec.get("content", ""))
            md_lines.append("")
        md_content = "\n".join(md_lines)
        st.download_button("Скачать Markdown", data=md_content, file_name="sop_generated.md", mime="text/markdown", key="download_md")


def run_generation_safe():
    try:
        run_generation()
    except Exception as e:
        add_log(f"Ошибка: {e}")
    finally:
        st.session_state.running = False
        st.session_state.worker = None


def run_generation():
    add_log("Инициализация агентов...")
    sop_gen = build_sop_generator()
    critic = build_critic()

    if not st.session_state.sections:
        add_log("Не заданы разделы. Добавьте хотя бы один раздел на вкладке 'Sections'.")
        return

    add_log("Обработка документов...")
    
    # Process global documents
    all_docs = st.session_state.uploaded_files.copy() if st.session_state.uploaded_files else []
    
    # Add section-specific documents
    for section in st.session_state.sections:
        if section.get("mode") == "ai+doc" and section.get("documents"):
            all_docs.extend(section["documents"])
    
    chunks = parse_documents_to_chunks(all_docs)
    st.session_state.parsed_chunks = chunks
    corpus_summary = summarize_parsed_chunks(chunks)

    # Build per-section summaries to scope influence of ai+doc uploads
    per_section_summaries: Dict[int, str] = {}
    try:
        for idx, section in enumerate(st.session_state.sections, start=1):
            if section.get("mode") == "ai+doc" and section.get("documents"):
                sec_chunks = parse_documents_to_chunks(section.get("documents") or [])
                per_section_summaries[idx] = summarize_parsed_chunks(sec_chunks)
    except Exception:
        per_section_summaries = {}
    
    add_log(f"Обработано документов: {len(all_docs)} (глобальных: {len(st.session_state.uploaded_files or [])}, по разделам: {len(all_docs) - len(st.session_state.uploaded_files or [])})")

    def base_instruction_builder(critique: str) -> str:
        return build_generation_instruction(
            sop_title=st.session_state.meta["title"],
            sop_number=st.session_state.meta["number"],
            equipment_type=st.session_state.meta["equipment"],
            sections=st.session_state.sections,
            parsed_corpus_summary=corpus_summary if corpus_summary else None,
            critique_feedback=critique or None,
        )

    add_log("Итеративная генерация до одобрения критиком...")
    loop_result = iterative_generate_until_approved(
        sop_gen=sop_gen,
        critic=critic,
        base_instruction_builder=base_instruction_builder,
        sections=st.session_state.sections,
        max_iters=5,
        enforce_mandatory_sections=False,
        logger=add_log,
        auto_backfill_meta={
            "title": st.session_state.meta.get("title"),
            "number": st.session_state.meta.get("number"),
            "equipment": st.session_state.meta.get("equipment"),
            "equipment_type": st.session_state.meta.get("equipment"),
        },
        auto_backfill_summary=corpus_summary if corpus_summary else None,
        section_summaries=per_section_summaries or None,
    )

    add_log("Сборка разделов...")
    generated_clean_content = loop_result.get("content", "")
    generated_sections = loop_result.get("sections") or []

    if generated_sections:
        st.session_state.preview = generated_sections
    else:
        # Fallback: pack entire документ в единственный блок
        title = st.session_state.meta.get("title") or "СОП"
        st.session_state.preview = [{"title": title, "content": generated_clean_content.strip()}]

    add_log("Готово. Статус: " + ("Одобрено" if loop_result.get("approved") else "Нужны правки"))


def main():
    st.set_page_config(
        page_title="SOP Generator",
        page_icon="📋",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.title("📋 SOP Generator - AI Agent System")
    
    # Initialize session state
    if "meta" not in st.session_state:
        st.session_state.meta = {"title": "", "number": "", "equipment": ""}
    if "sections" not in st.session_state:
        st.session_state.sections = []
    if "uploaded_files" not in st.session_state:
        st.session_state.uploaded_files = []
    if "preview" not in st.session_state:
        st.session_state.preview = []
    if "logs" not in st.session_state:
        st.session_state.logs = []
    if "running" not in st.session_state:
        st.session_state.running = False
    if "worker" not in st.session_state:
        st.session_state.worker = None
    if "parsed_chunks" not in st.session_state:
        st.session_state.parsed_chunks = []

    # Sidebar configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        st.markdown("---")
        # File upload
        st.subheader("📁 Documents")
        uploaded_files = st.file_uploader(
            "Upload reference documents",
            type=["pdf", "docx", "txt"],
            accept_multiple_files=True,
            help="Upload technical documentation, manuals, or standards"
        )
        
        if uploaded_files:
            # Persist uploaded files to a temporary directory and store their paths
            tmpdir = tempfile.mkdtemp(prefix="sop_global_docs_")
            paths: list[str] = []
            for uf in uploaded_files:
                out_path = os.path.join(tmpdir, uf.name)
                with open(out_path, "wb") as f:
                    f.write(uf.getbuffer())
                paths.append(out_path)
            st.session_state.uploaded_files = paths
            st.success(f"✅ {len(paths)} file(s) uploaded")

    # Main tabs (simplified)
    tabs = st.tabs([
        "📝 Basic Setup", 
        "🔧 Sections", 
        "⚡ Generation", 
        "📋 Preview & Export"
    ])

    with tabs[0]:
        ui_home()

    with tabs[1]:
        ui_sections()

    with tabs[2]:
        ui_generate()
    
    with tabs[3]:
        ui_preview_and_export()


# Enhanced generation is disabled in simplified mode; the following functions are intentionally omitted.


if __name__ == "__main__":
    main() 
