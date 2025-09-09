from __future__ import annotations
import os
import streamlit as st

from agents import run_author_critic_loop
from utils import save_uploaded_files, summarize_npa_documents, export_sop_to_docx, extract_structure_outline

APP_TITLE = "SOP Author-Critic (AutoGen + Streamlit)"


def _init_state() -> None:
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "final_text" not in st.session_state:
        st.session_state.final_text = ""


def main() -> None:
    st.set_page_config(page_title=APP_TITLE, layout="wide")
    _init_state()

    st.title(APP_TITLE)

    col1, col2 = st.columns(2)
    with col1:
        sop_title = st.text_input("Название СОП", value=st.session_state.get("sop_title", ""))
        sop_number = st.text_input("Номер СОП", value=st.session_state.get("sop_number", ""))
        equipment_type = st.text_input("Тип оборудования", value=st.session_state.get("equipment_type", ""))
        sections_text = st.text_area(
            "Разделы",
            value=st.session_state.get("sections_text", "Цель и область применения\nОтветственность\nПроцедуры\nБезопасность\nКонтроль качества"),
            height=150,
            help="Каждый раздел с новой строки",
        )
        content_mode = st.selectbox("Тип содержимого", ["ИИ генерация", "ИИ + ссылка на документ"], index=0)
        structure_hint_manual = st.text_area("Описание структуры документа (опционально)", value=st.session_state.get("structure_hint", ""), height=120)

    with col2:
        st.markdown("НПА (документы для справки: PDF/DOCX/Excel)")
        uploaded = st.file_uploader(
            "Загрузите файлы НПА",
            type=["pdf", "docx", "xlsx", "xls"],
            accept_multiple_files=True,
            help="Файлы учитываются в любом режиме. При 'ИИ генерация' они используются как контекст, при 'ИИ + ссылка на документ' — как обязательная фактура."
        )
        docs_paths = []
        docs_summary = ""
        if uploaded:
            with st.spinner("Обрабатываем документы..."):
                docs_paths = save_uploaded_files(uploaded)
                docs_summary = summarize_npa_documents(docs_paths)
                st.caption(f"Файлов сохранено: {len(docs_paths)}")

        st.divider()
        st.markdown("Документ со структурой (опционально)")
        structure_files = st.file_uploader(
            "Загрузите документ со структурой",
            type=["pdf", "docx", "txt"],
            accept_multiple_files=True,
            key="structure_uploader",
            help="Будет извлечен ориентировочный план (оглавление/заголовки) и передан агентам."
        )
        structure_outline = ""
        if structure_files:
            with st.spinner("Извлекаем структуру из документа..."):
                struct_paths = save_uploaded_files(structure_files)
                structure_outline = extract_structure_outline(struct_paths)
                if structure_outline:
                    st.caption("Извлечённая структура (фрагмент):")
                    st.code("\n".join(structure_outline.splitlines()[:10]))

    # Merge manual hint and extracted outline
    merged_structure_hint = None
    if structure_hint_manual or structure_outline:
        merged_structure_hint = "\n".join([s for s in [structure_hint_manual.strip(), structure_outline.strip()] if s])

    run_col, export_col = st.columns([1, 1])
    with run_col:
        if st.button("Запустить групповой чат агентов", type="primary"):
            if not sop_title or not sop_number:
                st.error("Укажите название и номер СОП")
            else:
                with st.spinner("Генерация и рецензирование..."):
                    result = run_author_critic_loop(
                        sop_title=sop_title,
                        sop_number=sop_number,
                        equipment_type=equipment_type,
                        sections_text=sections_text.strip(),
                        content_mode=content_mode,
                        docs_summary=docs_summary or None,
                        structure_hint=merged_structure_hint,
                        max_iters=6,
                    )
                    st.session_state.messages = result.get("messages", [])
                    st.session_state.final_text = result.get("final_text", "")

    st.markdown("---")
    st.subheader("Диалог (Author ↔ Critic)")
    if not st.session_state.messages:
        st.info("Пока нет сообщений. Введите данные и запустите процесс.")
    else:
        for m in st.session_state.messages:
            role = m.get("sender", "Agent")
            content = m.get("content", "")
            if hasattr(st, "chat_message"):
                with st.chat_message(role):
                    st.markdown(content)
            else:
                with st.expander(role, expanded=False):
                    st.markdown(content)

    st.subheader("Итоговый текст")
    if st.session_state.final_text:
        st.markdown(st.session_state.final_text)
    else:
        st.caption("Итоговый текст появится после завершения диалога")

    with export_col:
        if st.session_state.final_text:
            if st.button("Экспортировать в DOCX"):
                out_path = export_sop_to_docx(
                    meta={"title": sop_title, "number": sop_number},
                    markdown_text=st.session_state.final_text,
                )
                st.success(f"Сохранено: {out_path}")
                with open(out_path, "rb") as f:
                    st.download_button("Скачать DOCX", f, file_name="sop_result.docx")
            # New: export only final text to Markdown in docs/
            if st.button("Экспортировать в Markdown (docs/)"):
                docs_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "docs"))
                os.makedirs(docs_dir, exist_ok=True)
                md_path = os.path.join(docs_dir, "sop_generated.md")
                with open(md_path, "w", encoding="utf-8") as mf:
                    mf.write(f"# {sop_title or 'СОП'}\n\n")
                    if sop_number:
                        mf.write(f"Номер: {sop_number}\n\n")
                    mf.write(st.session_state.final_text.strip() + "\n")
                st.success(f"Сохранено: {md_path}")


if __name__ == "__main__":
    main() 