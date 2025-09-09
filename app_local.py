import os
import sys
import json
import tempfile
from typing import List, Dict, Any

import streamlit as st
import threading
from streamlit.runtime.scriptrunner import add_script_run_ctx

# Add the sop_generator directory to Python path for local development
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'sop_generator'))

from agents import (
    build_coordinator,
    build_sop_generator,
    build_document_parser,
    build_content_styler,
    build_critic,
    build_quality_checker,
    build_safety_agent,
    build_generation_instruction,
    orchestrate_workflow,
    summarize_parsed_chunks,
)
from agents.coordinator import iterative_generate_until_approved
from utils.document_processor import parse_documents_to_chunks
from utils.template_manager import load_template, apply_styles
from utils.export_manager import populate_docx, export_to_docx, export_to_pdf

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
    if "conversation" not in st.session_state:
        st.session_state.conversation = []  # [{sender, content}]


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
    st.text("\\n".join(st.session_state.logs[-50:]))
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
            doc, styles = load_template(os.path.join("sop_generator", "templates"))
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
            docs_dir = os.path.join("docs")
            os.makedirs(docs_dir, exist_ok=True)
            md_path = os.path.abspath(os.path.join(docs_dir, "sop_generated.md"))
            with open(md_path, "w", encoding="utf-8") as mf:
                mf.write(f"# {st.session_state.meta.get('title','СОП')}\\n\\n")
                if st.session_state.meta.get("number"):
                    mf.write(f"Номер: {st.session_state.meta['number']}\\n\\n")
                for idx, sec in enumerate(st.session_state.preview, start=1):
                    mf.write(f"## {idx}. {sec['title']}\\n\\n{sec.get('content','')}\\n\\n")
            st.success(f"Сохранено: {md_path}")


def run_mock_generation():
    """Generate SOP via a multi-round MOCK group chat using uploaded docs and section prompts."""
    add_log("Создание тестового СОП с уникальными разделами (многораундовый диалог)...")
    
    # Conversation transcript holder
    st.session_state.conversation = []
    def say(sender: str, content: str):
        st.session_state.conversation.append({"sender": sender, "content": content})
        add_log(f"{sender}: {content[:120]}{'...' if len(content)>120 else ''}")
    
    # Ingest docs (global + per-section ai+doc)
    all_docs = st.session_state.uploaded_files.copy() if st.session_state.uploaded_files else []
    for section in st.session_state.sections:
        if section.get("mode") == "ai+doc" and section.get("documents"):
            all_docs.extend(section["documents"])
    chunks = parse_documents_to_chunks(all_docs)
    corpus_summary = summarize_parsed_chunks(chunks)
    
    title = st.session_state.meta.get("title", "Тестовый СОП")
    number = st.session_state.meta.get("number", "TEST-001")
    equipment = st.session_state.meta.get("equipment", "Тестовое оборудование")
    
    # Build a simple section outline from configured sections
    cfg_titles = [s.get("title", f"Раздел {i+1}") for i, s in enumerate(st.session_state.sections)]
    outline_md = "\n".join([f"## {i+1}. {t}" for i, t in enumerate(cfg_titles, start=1)])
    prompts_md = "\n".join([f"- {i+1}. {s.get('title','')}: {s.get('prompt','') or '—'}" for i, s in enumerate(st.session_state.sections)])
    corpus_md = ""
    
    # Round loop
    max_iters = 3
    draft = f"# {title}\nНомер: {number}\n\n{outline_md}\n\nТехнические требования:\n- Указать параметры, критерии приемки и QC\n- Интегрировать безопасность\n\nУказания пользователя:\n{prompts_md}{corpus_md}"
    
    for it in range(1, max_iters+1):
        say("SOP_Generator", f"Итерация {it}: сформирован черновик разделов на основе подсказок и документов.")
        # Expand sections using heuristics + doc summary
        body = []
        for idx, sec in enumerate(st.session_state.sections):
            sec_title = sec.get("title", f"Раздел {idx+1}")
            prompt = sec.get("prompt", "")
            base = ""
            lt = sec_title.lower()
            if any(k in lt for k in ["ответственн", "обучен"]):
                base = """Ответственный персонал:\n- Старший лаборант — контроль выполнения процедуры\n- Лаборант-аналитик — выполнение анализов\nТребования к квалификации: профильное образование, сертификат, стаж ≥2 лет.\nПрограмма обучения: вводный курс + ежегодная переаттестация."""
            elif any(k in lt for k in ["цель", "область"]):
                base = f"""Данная процедура определяет порядок работы с оборудованием {equipment}.\nОбласть применения: аналитические лабораторные работы.\nОграничения: вне рамок технического обслуживания.\nИсключения: особые опасные вещества требуют отдельного СОП."""
            elif any(k in lt for k in ["риск", "безопас"]):
                base = """Идентифицированные риски: химическое воздействие, электрический шок, механические травмы.\nМеры защиты: СИЗ (очки, перчатки, халат), вытяжной шкаф, аварийный душ.\nВНИМАНИЕ: при утечках/запахе немедленно остановить работу."""
            elif any(k in lt for k in ["оборуд", "материал"]):
                base = f"""Основное оборудование: {equipment}.\nДополнительно: аналитические весы, мерная посуда.\nРеагенты: растворители высокой чистоты, стандарты.\nХранение: 15–25°C, RH<60%."""
            elif any(k in lt for k in ["процедур", "шаг"]):
                base = """1) Подготовить систему и прогреть.\n2) Калибровка: 1–100 мг/л, R²>0.995.\n3) Анализ: объём 1.0 мл, время 15 мин, параллельные — 3.\nКритерии успеха: RSD<5%."""
            elif any(k in lt for k in ["контроль", "quality", "qc"]):
                base = """Контроль качества: холостая и контрольная пробы, контроль стабильности.\nКритерии приёмки: отклонение ±10%, дрейф<5%. Частота: ежедневно."""
            elif any(k in lt for k in ["документооборот", "запис", "журнал"]):
                base = """Журналы: работы оборудования, протоколы анализов, журнал QC.\nТребования: разборчивость, заверение исправлений, сроки хранения 3–5 лет."""
            elif any(k in lt for k in ["ссылк", "норматив", "стандарт"]):
                base = """Нормативные ссылки: ISO/IEC 17025, ГОСТы по методам, локальные регламенты лаборатории."""
            elif any(k in lt for k in ["неисправн", "troubleshooting", "симптом"]):
                base = """Симптом→Причина→Действие: нестабильный сигнал→загрязнение детектора→очистить; отсутствие сигнала→источник/кабель→проверить/заменить."""
            else:
                base = ""
            # Merge doc cues (removed from output)
            body.append(f"## {idx+1}. {sec_title}\n{base}")
        draft = f"# {title}\nНомер: {number}\n\n" + "\n\n".join(body)
        
        # Safety agent
        say("Safety_Agent", "Интегрирую отмеченные риски, СИЗ и предупреждения в соответствующие разделы.")
        if "ВНИМАНИЕ" not in draft:
            draft += "\n\nВНИМАНИЕ: соблюдать требования безопасности при работе с реагентами и под давлением."
        if "СИЗ" not in draft:
            draft += "\n\nСИЗ: защитные очки, перчатки, халат; при летучих — работа под вытяжкой."
        
        # Quality checker
        say("Quality_Checker", "Проверяю критерии приёмки и QC: добавляю явные пороги и частоты.")
        if "Критерии приёмки" not in draft:
            draft += "\n\nКритерии приёмки: R²>0.995; RSD<5%; отклонение контрольной пробы ±10%."
        if "Контроль качества" not in draft:
            draft += "\n\nКонтроль качества: холостая проба в начале/конце, контрольная — каждые 10 анализов."
        
        # Critic
        issues = []
        if "Цель" not in draft and "область применения" not in draft.lower():
            issues.append("Нет явного описания цели/области применения.")
        if "СИЗ" not in draft:
            issues.append("Слабая интеграция СИЗ.")
        if "Критерии приёмки" not in draft:
            issues.append("Нет критериев приёмки.")
        status = "APPROVED" if not issues or it == max_iters else "REVISE"
        say("Critic", f"SUMMARY: Итерация {it}.\nISSUES: {('; '.join(issues) or 'нет')}\nSTATUS: {status}")
        
        if status == "APPROVED":
            say("Styler", "Привожу текст к единому стилю и форматированию (заголовки, списки, обозначения).")
            break
        else:
            say("Coordinator", "Принято. Внесём правки и повторим итерацию.")
    
    # Final content is current 'draft'
    final_text = draft
    
    # Parse to preview sections
    def parse_sections_from_content(content: str, section_configs: list) -> list:
        # Reuse the robust parser defined in run_generation() below by calling it dynamically
        # If not available yet, perform minimal split by '## N.'
        import re
        parts = re.split(r"\n(?=##\s*\d+\.)", content)
        result = []
        if len(parts) <= 1:
            # Fallback to one section
            for s in section_configs:
                result.append({"title": s.get("title","Раздел"), "content": content})
            return result
        # Map parts by order
        body_sections = [p.strip() for p in parts if p.strip() and p.strip().startswith("##")]
        for idx, sc in enumerate(section_configs):
            if idx < len(body_sections):
                # strip heading line from content
                lines = body_sections[idx].split("\n", 1)
                content_i = lines[1] if len(lines) > 1 else ""
                result.append({"title": sc.get("title", f"Раздел {idx+1}"), "content": content_i.strip()})
            else:
                result.append({"title": sc.get("title", f"Раздел {idx+1}"), "content": ""})
        return result
    
    st.session_state.preview = parse_sections_from_content(final_text, st.session_state.sections)
    add_log("✅ Тестовый многораундовый диалог завершён. Предпросмотр разделов обновлён.")


def run_generation_safe():
    try:
        run_generation()
    except Exception as e:
        add_log(f"Ошибка: {e}")
    finally:
        st.session_state.running = False


def run_generation():
    add_log("Инициализация агентов...")
    
    # Check if we should use mock mode (no API key or mock flag)
    use_mock_mode = not os.getenv("API_KEY") or os.getenv("USE_MOCK_MODE", "").lower() == "true"
    
    if use_mock_mode:
        add_log("🔧 Режим тестирования: используем моковые данные")
        run_mock_generation()
        return
    
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
        max_iters=4,  # Increased for better refinement
        logger=add_log,
    )

    add_log("Сборка разделов...")
    generated_clean_content = loop_result.get("content", "")
    
    # Parse sections from the clean content
    def parse_sections_from_content(content: str, section_configs: list) -> list:
        """Parse the generated content into individual sections with robust rules."""
        if not content.strip():
            return [{"title": s["title"], "content": "Нет содержания"} for s in section_configs]
        
        # Pre-filter: drop obvious instruction/spec blocks
        filtered_lines = []
        skip_spec_block = False
        for raw_line in content.split('\n'):
            line = raw_line.strip()
            line_lower = line.lower()
            if any(k in line_lower for k in [
                "критически важно - избегай", "детальные спецификации разделов", 
                "требования пользователя:", "шаблон для этого раздела:",
                "критически важно для раздела", "финальная проверка перед генерацией"
            ]):
                skip_spec_block = True
                continue
            # End skip when we reach a real section header
            if line.startswith('#') or line_lower.startswith('сop-') or line_lower.startswith('соп-'):
                skip_spec_block = False
            if skip_spec_block:
                continue
            # Also skip lines like "РАЗДЕЛ X:" which are specs, not content
            if line.upper().startswith("РАЗДЕЛ "):
                continue
            filtered_lines.append(raw_line)
        text = '\n'.join(filtered_lines)
        
        # Split content by section headers
        sections_parsed = []
        lines = text.split('\n')
        current_section = None
        current_content: list[str] = []
        
        # Header patterns (exclude plain numeric to avoid capturing spec preambles)
        import re
        header_patterns = [
            re.compile(r'^#{1,6}\s*\d+\.?\s*(.+)$'),   # ## 1. Title
            re.compile(r'^#{1,6}\s*(.+)$'),              # ## Title
            re.compile(r'^\*\*\d+\.?\s*(.+)\*\*$'), # **1. Title**
            re.compile(r'^\s*РАЗДЕЛ\s+\d+[:\-. ]\s*(.+)$', re.IGNORECASE), # РАЗДЕЛ 1: Title
        ]
        
        def is_header(s: str) -> tuple[bool, str | None]:
            for pat in header_patterns:
                m = pat.match(s.strip())
                if m:
                    title = m.group(1).strip()
                    # Normalize bold markers
                    title = re.sub(r'\*+', '', title)
                    return True, title
            return False, None
        
        for raw in lines:
            stripped = raw.strip()
            match, header_title = is_header(stripped)
            if match and header_title:
                if current_section and current_content:
                    sections_parsed.append({
                        "title": current_section,
                        "content": '\n'.join(current_content).strip()
                    })
                current_section = header_title
                current_content = []
                continue
            if current_section is not None:
                current_content.append(raw)
        
        if current_section and current_content:
            sections_parsed.append({
                "title": current_section,
                "content": '\n'.join(current_content).strip()
            })
        
        # If nothing parsed, fallback to whole text as a single section to avoid duplication logic
        if not sections_parsed:
            sections_parsed = [{"title": "Документ", "content": text.strip()}]
        
        # Drop document preamble if present (title block with only metadata like "Номер:")
        if sections_parsed:
            first_block = sections_parsed[0]
            fb_text = (first_block.get("title", "") + "\n" + first_block.get("content", "")).lower()
            if ("номер:" in fb_text or "sop" in fb_text or "эксплуатац" in fb_text):
                # Consider it a preamble, not a real section
                sections_parsed = sections_parsed[1:] if len(sections_parsed) > 1 else sections_parsed
        
        # Heuristic classifiers (defined locally for mock parser)
        canonical_titles = {
            "scope": "Цель и область применения",
            "responsibility": "Ответственность и обучение персонала",
            "safety": "Анализ рисков и безопасность",
            "equipment": "Оборудование и материалы",
            "procedure": "Пошаговые процедуры",
            "quality": "Контроль качества",
            "records": "Документооборот и ведение записей",
            "references": "Нормативные ссылки",
            "troubleshooting": "Устранение неисправностей",
        }
        
        def guess_key_from_text(text_: str) -> str | None:
            t = text_.lower()
            if any(k in t for k in ["цель", "область примен", "исключен", "границ", "подготовк"]):
                return "scope"
            if any(k in t for k in ["ответствен", "обучен", "квалификац", "допуск", "персонал", "роль"]):
                return "responsibility"
            if any(k in t for k in ["риск", "опасност", "безопас", "сиз", "лото", "внимани", "предупрежд"]):
                return "safety"
            if any(k in t for k in ["оборуд", "материал", "колонк", "детектор", "реагент", "спецификац"]):
                return "equipment"
            if any(k in t for k in ["шаг", "процедур", "последователь", "инструкц", "температур", "время", "объем", "скорост", "давлен"]):
                return "procedure"
            if any(k in t for k in ["контроль каче", "qc", "критери", "приемк", "валидац", "rsd", "допуск"]):
                return "quality"
            if any(k in t for k in ["документооборот", "запис", "журнал", "отчет", "формат", "срок хран"]):
                return "records"
            if any(k in t for k in ["ссылк", "норматив", "стандарт", "gost", "iso"]):
                return "references"
            if any(k in t for k in ["неисправн", "симптом", "причин", "действ", "диагност", "устранен"]):
                return "troubleshooting"
            return None
        
        # Compute guess for parsed sections
        parsed_with_guess = []
        for ps in sections_parsed:
            key = guess_key_from_text(ps["title"] + "\n" + ps["content"])
            parsed_with_guess.append({**ps, "_key": key})
        
        # Map parsed sections to configured sections (consume parsed sections once)
        result_sections = []
        used_indices: set[int] = set()
        for idx, section_config in enumerate(section_configs):
            cfg_title = section_config["title"]
            cfg_prompt = section_config.get("prompt", "")
            if section_config.get("mode") == "manual" and section_config.get("content"):
                result_sections.append({"title": cfg_title, "content": section_config["content"]})
                continue
            
            # Determine intended key from config title/prompt
            intended_key = guess_key_from_text((cfg_title + "\n" + cfg_prompt))
            
            matched_content = ""
            chosen_idx: int | None = None
            # 1) Match by intended key
            if intended_key:
                for i, ps in enumerate(parsed_with_guess):
                    if i in used_indices:
                        continue
                    if ps["_key"] == intended_key and ps.get("content"):
                        matched_content = ps["content"]
                        chosen_idx = i
                        break
            # 2) Title similarity fallback
            if not matched_content:
                config_title_lower = cfg_title.lower()
                for i, ps in enumerate(sections_parsed):
                    if i in used_indices:
                        continue
                    if config_title_lower and (config_title_lower in ps["title"].lower() or ps["title"].lower() in config_title_lower):
                        matched_content = ps["content"]
                        chosen_idx = i
                        break
            # 3) Order-based fallback (use next unused by order)
            if not matched_content:
                for i in range(len(sections_parsed)):
                    if i not in used_indices:
                        matched_content = sections_parsed[i]["content"]
                        chosen_idx = i
                        break
                if not matched_content and sections_parsed:
                    matched_content = sections_parsed[-1]["content"]
                    chosen_idx = len(sections_parsed) - 1
            
            if chosen_idx is not None:
                used_indices.add(chosen_idx)
            
            # Auto-rename generic titles to canonical when we know the intent
            result_title = cfg_title
            if re.match(r'^\s*Раздел\s+\d+\s*$', cfg_title, flags=re.IGNORECASE) and intended_key:
                result_title = canonical_titles.get(intended_key, cfg_title)
            
            result_sections.append({
                "title": result_title,
                "content": matched_content
            })
        
        return result_sections
    
    st.session_state.preview = parse_sections_from_content(generated_clean_content, st.session_state.sections)

    add_log("Готово. Статус: " + ("Одобрено" if loop_result.get("approved") else "Нужны правки"))


def _run_agent_and_get_messages_local(agent, task: str):
    """Local helper to run an agent and return a list of messages [{sender, content}]."""
    try:
        # Some agent implementations expose async run, others sync generate_reply
        if hasattr(agent, "run"):
            import asyncio
            async def _runner():
                try:
                    result = await agent.run(task=task)
                    msgs = getattr(result, "messages", [])
                    # Normalize
                    out = []
                    for m in msgs:
                        sender = getattr(m, "source", getattr(m, "role", agent.__class__.__name__))
                        content = getattr(m, "content", str(m))
                        out.append({"sender": sender, "content": content})
                    # Fallback when no structured messages
                    if not out and hasattr(result, "content"):
                        out = [{"sender": getattr(agent, "name", "Agent"), "content": result.content}]
                    return out
                except Exception as e:
                    return [{"sender": getattr(agent, "name", "Agent"), "content": f"Error: {e}"}]
            msgs = asyncio.run(_runner())
            return msgs
        elif hasattr(agent, "generate_reply"):
            import asyncio
            async def _runner2():
                try:
                    reply = await agent.generate_reply(task)
                    return [{"sender": getattr(agent, "name", "Agent"), "content": reply}]
                except Exception as e:
                    return [{"sender": getattr(agent, "name", "Agent"), "content": f"Error: {e}"}]
            return asyncio.run(_runner2())
        else:
            return [{"sender": getattr(agent, "name", "Agent"), "content": "[No run/generate method available]"}]
    except Exception as e:
        return [{"sender": getattr(agent, "name", "Agent"), "content": f"Execution error: {e}"}]


def run_conversation_preview() -> None:
    """Build agents and run a short conversation to preview interactions."""
    add_log("Запуск предпросмотра диалога агентов...")

    # Mock mode — no network calls
    use_mock_mode = not os.getenv("API_KEY") or os.getenv("USE_MOCK_MODE", "").lower() == "true"
    if use_mock_mode:
        st.session_state.conversation = [
            {"sender": "Coordinator", "content": "Коллеги, сформируйте черновик СОП по введенным метаданным и разделам."},
            {"sender": "SOP_Generator", "content": "Готов черновой вариант. Структура соблюдена, параметры заполнены."},
            {"sender": "Safety_Agent", "content": "Добавил предупреждения ВНИМАНИЕ/ПРЕДУПРЕЖДЕНИЕ и требования к СИЗ."},
            {"sender": "Quality_Checker", "content": "Найдены несоответствия: уточнить допуски RSD и частоту QC-проб."},
            {"sender": "Critic", "content": "SUMMARY: Хорошо структурировано.\nISSUES: Уточнить критерии приемки.\nSTATUS: REVISE"},
            {"sender": "Styler", "content": "Привел стиль к корпоративному, единая терминология и форматирование."},
        ]
        add_log("Диалог (мок) сформирован без обращения к LLM.")
        return

    # Initialize agents
    coord = build_coordinator(on_log=add_log)
    sop_gen = build_sop_generator()
    safety = build_safety_agent()
    critic = build_critic()
    quality = build_quality_checker()
    styler = build_content_styler()

    # Aggregate docs: global + ai+doc per-section
    all_docs = st.session_state.uploaded_files.copy() if st.session_state.uploaded_files else []
    for section in st.session_state.sections:
        if section.get("mode") == "ai+doc" and section.get("documents"):
            all_docs.extend(section["documents"])

    chunks = parse_documents_to_chunks(all_docs)
    corpus_summary = summarize_parsed_chunks(chunks)

    def base_instruction_builder(critique: str) -> str:
        return build_generation_instruction(
            sop_title=st.session_state.meta.get("title", "Без названия"),
            sop_number=st.session_state.meta.get("number", ""),
            equipment_type=st.session_state.meta.get("equipment", ""),
            sections=st.session_state.sections,
            parsed_corpus_summary=corpus_summary if corpus_summary else None,
            critique_feedback=critique or None,
        )

    # Try real group chat first
    try:
        instructions = base_instruction_builder("")
        messages = orchestrate_workflow(
            coordinator=coord,
            agents=[sop_gen, safety, critic, quality, styler],
            instructions=instructions,
            max_rounds=6,
        )
        st.session_state.conversation = messages
        add_log(f"Диалог завершен. Сообщений: {len(messages)}")
        return
    except Exception as e:
        add_log(f"Групповой чат недоступен, используем последовательный режим: {e}")

    # Sequential fallback transcript (short)
    transcript: list[dict] = []
    # 1) Generator produces initial draft
    gen_msgs = _run_agent_and_get_messages_local(sop_gen, base_instruction_builder(""))
    transcript.extend(gen_msgs)
    draft_text = "\n\n".join([m["content"] for m in gen_msgs])

    # 2) Safety review
    safety_msgs = _run_agent_and_get_messages_local(safety, f"Проверь раздел безопасности.\nТЕКСТ:\n{draft_text[:3000]}")
    transcript.extend(safety_msgs)

    # 3) Quality review
    quality_msgs = _run_agent_and_get_messages_local(quality, f"Выяви проблемы качества. Верни только список.\nТЕКСТ:\n{draft_text[:3000]}")
    transcript.extend(quality_msgs)

    # 4) Critic summary
    critic_msgs = _run_agent_and_get_messages_local(critic, f"Оцени документ. Верни SUMMARY/ISSUES/STATUS.\nТЕКСТ:\n{draft_text[:3000]}")
    transcript.extend(critic_msgs)

    # 5) Styler pass
    styler_msgs = _run_agent_and_get_messages_local(styler, f"Приведи к единому стилю. Верни ТОЛЬКО текст.\nТЕКСТ:\n{draft_text[:3000]}")
    transcript.extend(styler_msgs)

    st.session_state.conversation = transcript
    add_log(f"Последовательный диалог завершен. Сообщений: {len(transcript)}")


def run_conversation_preview_safe() -> None:
    try:
        run_conversation_preview()
    except Exception as e:
        add_log(f"Ошибка предпросмотра диалога: {e}")


def ui_conversation():
    st.header("Диалог ИИ-агентов")
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("Запустить предпросмотр диалога", type="primary"):
            t = threading.Thread(target=run_conversation_preview_safe, daemon=True)
            add_script_run_ctx(t)
            t.start()
            st.info("Диалог запускается... Обновите вкладку через несколько секунд.")
    with col2:
        if st.button("Очистить диалог"):
            st.session_state.conversation = []
            st.success("Очищено")

    st.markdown("---")
    if not st.session_state.conversation:
        st.info("Пока нет сообщений. Нажмите кнопку выше, чтобы запустить диалог.")
        return

    # Render conversation
    for i, msg in enumerate(st.session_state.conversation):
        sender = msg.get("sender", "agent")
        content = msg.get("content", "")
        with st.expander(f"{i+1}. {sender}", expanded=False):
            st.markdown(content)


def main():
    st.set_page_config(page_title=APP_TITLE, layout="wide")
    init_session_state()

    st.title(APP_TITLE)
    tabs = st.tabs(["Главная", "Разделы", "Генерация", "Предпросмотр и экспорт", "Диалог"]) 

    with tabs[0]:
        ui_home()
    with tabs[1]:
        ui_sections()
    with tabs[2]:
        ui_generate()
    with tabs[3]:
        ui_preview_and_export()
    with tabs[4]:
        ui_conversation()


if __name__ == "__main__":
    main()