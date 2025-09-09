import os
import sys
import json
import tempfile
from typing import List, Dict, Any

# Add parent directory to Python path for module resolution
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

import streamlit as st
import threading
from streamlit.runtime.scriptrunner import add_script_run_ctx
from typing import List, Dict, Any
import os
from datetime import datetime

from sop_generator.agents.coordinator import (
    build_coordinator, 
    iterative_generate_until_approved,
    enhanced_iterative_generate_with_chat
)
from sop_generator.agents.sop_generator import build_sop_generator
from sop_generator.agents.document_parser import build_document_parser, parse_documents_to_chunks, summarize_parsed_chunks
from sop_generator.agents.content_styler import build_content_styler
from sop_generator.agents.critic import build_critic
from sop_generator.agents.quality_checker import build_quality_checker
from sop_generator.agents.safety_agent import build_safety_agent
from sop_generator.agents.sop_generator import build_generation_instruction
from sop_generator.utils.export_manager import export_to_docx, export_to_pdf, populate_docx

from sop_generator.ui.dashboard_components import (
    AgentConversationViewer, 
    render_agent_interaction_analysis
)

APP_TITLE = "SOP Generator (AutoGen + Streamlit)"


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
        st.caption("Задача выполняется... Обновите вкладку или перейдите между вкладками для обновления логов.")


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
            sec["content"] = st.text_area("Контент (Markdown поддерживается)", value=content, height=220, key=f"prev_content_{idx}", help="Используйте Markdown для форматирования. Таблицы: | Заголовок | Заголовок | \\n |-------|-------|")
        st.session_state.preview[idx] = sec

    st.subheader("Экспорт")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Экспорт в Word"):
            doc, styles = load_template(os.path.join(os.path.dirname(__file__), "templates"))
            apply_styles(doc, styles)
            doc = populate_docx(doc, st.session_state.meta, st.session_state.preview)
            out_path = export_to_docx(doc, os.path.join(tempfile.gettempdir(), "sop_generated.docx"))
            st.success(f"Сохранено: {out_path}")
            with open(out_path, "rb") as f:
                st.download_button("Скачать DOCX", f, file_name="sop_generated.docx")
    with col2:
        if st.button("Экспорт в PDF"):
            out_path = export_to_pdf(st.session_state.preview, os.path.join(tempfile.gettempdir(), "sop_generated.pdf"), st.session_state.meta)
            st.success(f"Сохранено: {out_path}")
            with open(out_path, "rb") as f:
                st.download_button("Скачать PDF", f, file_name="sop_generated.pdf")
    with col3:
        if st.button("Экспорт в Markdown (docs/)"):
            docs_dir = os.path.join(os.path.dirname(__file__), "..", "docs")
            os.makedirs(docs_dir, exist_ok=True)
            md_path = os.path.abspath(os.path.join(docs_dir, "sop_generated.md"))
            with open(md_path, "w", encoding="utf-8") as mf:
                mf.write(f"# {st.session_state.meta.get('title','СОП')}\n\n")
                if st.session_state.meta.get("number"):
                    mf.write(f"Номер: {st.session_state.meta['number']}\n\n")
                for idx, sec in enumerate(st.session_state.preview, start=1):
                    mf.write(f"## {idx}. {sec['title']}\n\n{sec.get('content','')}\n\n")
            st.success(f"Сохранено: {md_path}")


def run_generation_safe():
    try:
        run_generation()
    except Exception as e:
        add_log(f"Ошибка: {e}")
    finally:
        st.session_state.running = False


def run_generation():
    add_log("Инициализация агентов...")
    coord = build_coordinator(on_log=add_log)
    sop_gen = build_sop_generator()
    doc_parser = build_document_parser()
    styler = build_content_styler()
    critic = build_critic()
    quality = build_quality_checker()
    safety = build_safety_agent()

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
        coordinator=coord,
        sop_gen=sop_gen,
        safety=safety,
        critic=critic,
        quality=quality,
        styler=styler,
        base_instruction_builder=base_instruction_builder,
        max_iters=2,  # Reduced for faster generation
        logger=add_log,
    )

    add_log("Сборка разделов...")
    generated_clean_content = loop_result.get("content", "")
    
    # Parse sections from the clean content
    def parse_sections_from_content(content: str, section_configs: list) -> list:
        """Parse the generated content into sections."""
        if not content.strip():
            return [{"title": s["title"], "content": "Нет содержания"} for s in section_configs]
        
        # For now, use the full content for each section since it's a complete SOP
        # In the future, this could be enhanced to split by section headers
        sections = []
        for section_config in section_configs:
            if section_config.get("mode") == "manual" and section_config.get("content"):
                # Use manual content if provided
                sections.append({
                    "title": section_config["title"],
                    "content": section_config["content"]
                })
            else:
                # Use generated content for AI modes
                sections.append({
                    "title": section_config["title"],
                    "content": content
                })
        return sections
    
    st.session_state.preview = parse_sections_from_content(generated_clean_content, st.session_state.sections)

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
    if "use_enhanced_chat" not in st.session_state:
        st.session_state.use_enhanced_chat = True
    if "agent_conversations" not in st.session_state:
        st.session_state.agent_conversations = []
    if "live_conversation_feed" not in st.session_state:
        st.session_state.live_conversation_feed = []

    # Sidebar configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Generation mode selection
        st.subheader("🤖 Generation Mode")
        use_enhanced = st.toggle(
            "Enhanced Group Chat Mode",
            value=st.session_state.use_enhanced_chat,
            help="Use the new interactive group chat system with real-time agent conversations"
        )
        st.session_state.use_enhanced_chat = use_enhanced
        
        if use_enhanced:
            st.success("🚀 Enhanced mode: Real-time agent interactions")
        else:
            st.info("📝 Classic mode: Sequential agent processing")
        
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
            st.session_state.uploaded_files = uploaded_files
            st.success(f"✅ {len(uploaded_files)} file(s) uploaded")

    # Main tabs
    if st.session_state.use_enhanced_chat:
        tabs = st.tabs([
            "📝 Basic Setup", 
            "🔧 Sections", 
            "🚀 Enhanced Generation", 
            "💬 Agent Conversations",
            "📊 Interaction Analysis",
            "📋 Preview & Export"
        ])
    else:
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
        if st.session_state.use_enhanced_chat:
            ui_enhanced_generation()
        else:
            ui_generate()
    
    if st.session_state.use_enhanced_chat:
        with tabs[3]:
            ui_agent_conversations()
        
        with tabs[4]:
            ui_interaction_analysis()
        
        with tabs[5]:
            ui_preview_and_export()
    else:
        with tabs[3]:
            ui_preview_and_export()


def ui_enhanced_generation():
    """Enhanced generation UI with real-time agent conversations"""
    st.header("🚀 Enhanced AI Agent Generation")
    
    # Pre-generation validation
    validation_messages = []
    if not st.session_state.meta.get("title"):
        validation_messages.append("❌ SOP title is required")
    if not st.session_state.meta.get("number"):
        validation_messages.append("❌ SOP number is required")
    if not st.session_state.sections:
        validation_messages.append("❌ At least one section must be configured")
    
    if validation_messages:
        st.error("**Pre-generation Validation Failed:**")
        for msg in validation_messages:
            st.write(msg)
        return
    
    # Generation controls
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        if st.button(
            "🚀 Start Enhanced Generation", 
            type="primary", 
            disabled=st.session_state.running,
            help="Start AI agent collaboration with real-time conversations"
        ):
            if st.session_state.worker and st.session_state.worker.is_alive():
                add_log("Generation already in progress. Please wait...")
            else:
                st.session_state.running = True
                st.session_state.agent_conversations = []  # Reset conversations
                st.session_state.live_conversation_feed = []  # Reset live feed
                t = threading.Thread(target=run_enhanced_generation_safe, daemon=True)
                add_script_run_ctx(t)
                st.session_state.worker = t
                t.start()
                st.rerun()
    
    with col2:
        if st.button("⏹️ Stop Generation", disabled=not st.session_state.running):
            st.session_state.running = False
            add_log("Generation stop requested")
    
    with col3:
        if st.button("🔄 Clear Logs"):
            st.session_state.logs = []
            st.session_state.agent_conversations = []
            st.session_state.live_conversation_feed = []
            st.rerun()
    
    # Generation progress
    if st.session_state.running:
        st.info("🔄 Enhanced generation in progress...")
        progress_bar = st.progress(0)
        
        # Estimate progress based on logs
        if st.session_state.logs:
            iteration_keywords = ["ITERATION", "Starting collaborative", "Starting critic review"]
            progress_indicators = [log for log in st.session_state.logs if any(keyword in log for keyword in iteration_keywords)]
            progress = min(len(progress_indicators) / 6, 1.0)  # Estimate 6 major steps
            progress_bar.progress(progress)
    
    # Live conversation feed
    if st.session_state.live_conversation_feed:
        st.markdown("---")
        conversation_viewer = AgentConversationViewer()
        conversation_viewer.render_live_conversation_feed(st.session_state.live_conversation_feed)
    
    # Generation logs
    st.markdown("---")
    st.subheader("📝 Generation Logs")
    
    if st.session_state.logs:
        # Display recent logs in a scrollable container
        log_container = st.container()
        with log_container:
            recent_logs = st.session_state.logs[-20:]  # Show last 20 logs
            for log in recent_logs:
                if "❌" in log or "Error" in log:
                    st.error(log)
                elif "✅" in log or "completed" in log:
                    st.success(log)
                elif "⚠️" in log or "Warning" in log:
                    st.warning(log)
                elif "🔄" in log or "ITERATION" in log:
                    st.info(log)
                else:
                    st.text(log)
        
        # Auto-refresh hint
        if st.session_state.running:
            st.caption("🔄 Logs update automatically during generation")
    else:
        st.info("No logs yet. Start generation to see progress.")


def ui_agent_conversations():
    """UI for displaying agent conversations"""
    st.header("💬 Agent Conversations")
    
    if not st.session_state.agent_conversations:
        st.info("No agent conversations available yet. Start enhanced generation to see real-time interactions!")
        return
    
    # Display conversations using the conversation viewer
    conversation_viewer = AgentConversationViewer()
    conversation_viewer.render_conversation_dashboard(st.session_state.agent_conversations)


def ui_interaction_analysis():
    """UI for agent interaction analysis"""
    if st.session_state.agent_conversations:
        render_agent_interaction_analysis(st.session_state.agent_conversations)
    else:
        st.info("No conversation data available for analysis. Complete a generation cycle first.")


def run_enhanced_generation_safe():
    """Safe wrapper for enhanced generation"""
    try:
        run_enhanced_generation()
    except Exception as e:
        add_log(f"❌ Generation error: {e}")
        st.session_state.running = False
    finally:
        st.session_state.running = False


def run_enhanced_generation():
    """Enhanced generation using the new group chat system"""
    add_log("🚀 Initializing enhanced AI agent system...")
    
    # Initialize agents
    coord = build_coordinator(on_log=add_log_and_conversation)
    sop_gen = build_sop_generator()
    doc_parser = build_document_parser()
    styler = build_content_styler()
    critic = build_critic()
    quality = build_quality_checker()
    safety = build_safety_agent()

    add_log("📚 Processing reference documents...")
    
    # Process global documents
    all_docs = st.session_state.uploaded_files.copy() if st.session_state.uploaded_files else []
    
    # Add section-specific documents
    for section in st.session_state.sections:
        if section.get("mode") == "ai+doc" and section.get("documents"):
            all_docs.extend(section["documents"])
    
    chunks = parse_documents_to_chunks(all_docs)
    st.session_state.parsed_chunks = chunks
    corpus_summary = summarize_parsed_chunks(chunks)
    
    add_log(f"📄 Processed {len(all_docs)} documents, extracted {len(chunks)} content chunks")

    def base_instruction_builder(critique: str) -> str:
        return build_generation_instruction(
            sop_title=st.session_state.meta["title"],
            sop_number=st.session_state.meta["number"],
            equipment_type=st.session_state.meta["equipment"],
            sections=st.session_state.sections,
            parsed_corpus_summary=corpus_summary if corpus_summary else None,
            critique_feedback=critique or None,
        )

    add_log("💬 Starting enhanced collaborative generation...")
    
    # Use the enhanced generation system
    loop_result = enhanced_iterative_generate_with_chat(
        coordinator=coord,
        sop_gen=sop_gen,
        safety=safety,
        critic=critic,
        quality=quality,
        styler=styler,
        base_instruction_builder=base_instruction_builder,
        max_iters=3,
        logger=add_log_and_conversation,
    )

    # Store conversation data
    st.session_state.agent_conversations = loop_result.get("conversations", [])
    
    generated_full_text = loop_result.get("content", "")
    
    # Create preview sections
    preview = []
    if generated_full_text:
        parts = generated_full_text.split("\n\n")
        for idx, section in enumerate(st.session_state.sections):
            if section["mode"] == "manual":
                final_text = section.get("content", "")
            else:
                # Extract relevant parts for this section
                slice_text = "\n".join(parts[idx*2:(idx+1)*2]).strip()
                if section["mode"] == "ai+doc":
                    top_chunks = chunks[:3]
                    cites = "\n".join([f"Источник: {c['source']} | {c['keywords']}" for c in top_chunks])
                    final_text = (section.get("content") or f"{slice_text}\n\n{cites}").strip()
                else:
                    final_text = section.get("content") or slice_text or f"[Generated] {section['title']}"
            
            preview.append({"title": section["title"], "content": final_text})
    
    st.session_state.preview = preview
    
    if loop_result.get("approved", False):
        add_log("🎉 Enhanced generation completed successfully!")
    else:
        add_log("⚠️ Generation completed but may need manual review")


def add_log_and_conversation(message: str):
    """Add log message and update live conversation feed"""
    add_log(message)
    
    # Extract agent conversations from log messages
    if "🗣️" in message:
        # Parse agent conversation format: "🗣️ AgentName: message content..."
        try:
            parts = message.split("🗣️ ", 1)[1].split(": ", 1)
            if len(parts) == 2:
                sender = parts[0].strip()
                content = parts[1].strip()
                
                conversation_entry = {
                    "sender": sender,
                    "content": content,
                    "timestamp": datetime.now().strftime('%H:%M:%S')
                }
                
                st.session_state.live_conversation_feed.append(conversation_entry)
                
                # Keep only last 50 messages to prevent memory issues
                if len(st.session_state.live_conversation_feed) > 50:
                    st.session_state.live_conversation_feed = st.session_state.live_conversation_feed[-50:]
        except Exception:
            pass  # Ignore parsing errors


if __name__ == "__main__":
    main() 