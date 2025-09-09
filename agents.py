from __future__ import annotations
from typing import List, Dict, Any
import asyncio
import re
import os

from sop_generator.config.agent_config import AGENT_DEFAULTS, build_openai_chat_client
from sop_generator.agents.base_imports import AssistantAgent, TextMessage, BaseChatMessage

"""agents.py
Author↔Critic loop using AutoGen AssistantAgents. Author drafts SOP, Critic reviews and provides
structured feedback. Author revises until Critic outputs 'Готово' or max iterations reached.
"""

# Soft char limits to keep prompts within model context windows (rough heuristic ~4 chars/token)
_MAX_DOCS_SUMMARY_CHARS = int(os.environ.get("DOCS_SUMMARY_CLIP", "40000"))
_MAX_STRUCTURE_HINT_CHARS = int(os.environ.get("STRUCTURE_HINT_CLIP", "8000"))
_MAX_SECTIONS_TEXT_CHARS = int(os.environ.get("SECTIONS_TEXT_CLIP", "2000"))
_MAX_SOP_TEXT_FOR_CRITIC_CHARS = int(os.environ.get("SOP_TEXT_CRITIC_CLIP", "60000"))
_MAX_PREVIOUS_TEXT_CHARS = int(os.environ.get("PREVIOUS_TEXT_CLIP", "60000"))
_MAX_CRITIC_FEEDBACK_CHARS = int(os.environ.get("CRITIC_FEEDBACK_CLIP", "8000"))


def _clip_text(text: str | None, max_chars: int) -> str | None:
    if text is None:
        return None
    if len(text) <= max_chars:
        return text
    return text[:max_chars]


AUTHOR_SYSTEM_PROMPT = (
    """
Ты — Author. Пиши профессиональные СОП (Standard Operating Procedure) на русском языке.
Всегда создавай полноразмерный документ в Markdown с четкими разделами с заголовками вида: "## N. <Название>".
Требования: уникальность контента между разделами, конкретные параметры (температуры, время, объемы),
критерии приемки, интеграция безопасности. Если предоставлены ссылки/сводка НПА, используй их как базу фактов.
Возвращай только сам документ без метакомментариев.
Никогда не включай в ответ текст инструкции/задания, блоки подсказок или служебные метки (например, "Ориентиры разделов", "ИСТОЧНИКИ/СВОДКА", "СТРУКТУРА (ориентир)"); не цитируй исходные подсказки и названия/фрагменты руководств.
    """
).strip()

CRITIC_SYSTEM_PROMPT = (
    """
Ты — Critic. Дай четкую, структурированную рецензию на текст СОП.
Формат ответа:
SUMMARY: 1–2 предложения общее качество.
ISSUES: нумерованный список конкретных проблем с указанием раздела/пункта и требуемого исправления.
ACTIONS: чек-лист конкретных правок, которые нужно внести Автору.
ИТОГ: На отдельной строке выведи ровно «Готово», если документ можно принять; иначе — «Не готово».
    """
).strip()

SUPERVISOR_SYSTEM_PROMPT = (
    """
Ты — Supervisor. Следи за прогрессом и при необходимости давай рекомендации Автору и Критику.
Отвечай только при прямом обращении.
    """
).strip()


def _build_agent(name: str, base_key: str, system_message: str) -> AssistantAgent:
    """Create an AutoGen AssistantAgent using existing config builders."""
    cfg = {**AGENT_DEFAULTS.get(base_key, {}).get("llm_config", {})}
    if base_key == "sop_generator":
        cfg["max_tokens"] = max(1500, int(cfg.get("max_tokens", 1500)))
        cfg["temperature"] = cfg.get("temperature", 0.3)
    model_client = build_openai_chat_client(cfg)
    return AssistantAgent(name=name, system_message=system_message, model_client=model_client)


def build_author_agent() -> AssistantAgent:
    """Factory for Author agent."""
    return _build_agent("Author", "sop_generator", AUTHOR_SYSTEM_PROMPT)


def build_critic_agent() -> AssistantAgent:
    """Factory for Critic agent."""
    return _build_agent("Critic", "critic", CRITIC_SYSTEM_PROMPT)


def build_supervisor_agent() -> AssistantAgent:
    """Optional future extension: Supervisor agent."""
    return _build_agent("Supervisor", "coordinator", SUPERVISOR_SYSTEM_PROMPT)


async def _run_async(agent: AssistantAgent, task: str):
    try:
        if hasattr(agent, "run"):
            result = await agent.run(task=task)
            return getattr(result, "messages", [])
        reply = await agent.generate_reply(task)
        return [TextMessage(content=reply, source=getattr(agent, "name", "Agent"))]
    except Exception as e:
        return [TextMessage(content=f"Error: {e}", source=getattr(agent, "name", "Agent"))]


def _run(agent: AssistantAgent, task: str) -> List[TextMessage]:
    try:
        raw = asyncio.run(_run_async(agent, task))
        out: List[TextMessage] = []
        for m in raw:
            if isinstance(m, (TextMessage, BaseChatMessage)):
                out.append(m)  # type: ignore[arg-type]
        return out
    except Exception as e:
        return [TextMessage(content=f"Execution error: {e}", source=getattr(agent, "name", "Agent"))]


def _extract_text(msgs: List[TextMessage]) -> str:
    return "\n\n".join([getattr(m, "content", "") for m in msgs])


def _sanitize_output(text: str) -> str:
    """Remove prompt artifacts and keep only the final SOP content.
    Heuristics:
    - Drop any echoed instruction block between generation cue and output directive
    - Keep from the first section header (or title) onward
    - Trim everything after the first critic/preamble marker (SUMMARY/ISSUES/ACTIONS/ИТОГ/ТЕКУЩАЯ ВЕРСИЯ/Оцени следующий текст)
    - Fallback: drop lines containing markers anywhere
    """
    markers = [
        "Сгенерируй развернутый СОП",
        "Ориентиры разделов",
        "СТРУКТУРА (ориентир)",
        "ИСТОЧНИКИ/СВОДКА",
        "Выдай ТОЛЬКО готовый документ",
        "SUMMARY:",
        "ISSUES:",
        "ACTIONS:",
        "ИТОГ:",
        "ТЕКУЩАЯ ВЕРСИЯ:",
        "Оцени следующий текст",
        "ТЕКСТ:",
    ]
    # 1) Remove any block between the generation instruction and the "Выдай ТОЛЬКО..." directive
    start_idx = text.find("Сгенерируй развернутый СОП")
    end_idx = text.find("Выдай ТОЛЬКО готовый документ")
    if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
        head = text[:start_idx]
        tail = text[end_idx:]
        text = head + tail

    lines = text.splitlines()

    # 2) Find the first document header start
    header_patterns = [r"^#\s+", r"^##\s+\d+\.\s", r"^##\s", r"^1\.\s"]
    first_header_idx = -1
    for idx, line in enumerate(lines):
        if any(re.match(p, line) for p in header_patterns):
            first_header_idx = idx
            break

    if first_header_idx != -1:
        doc_lines = lines[first_header_idx:]
        # 3) Trim at first marker after header
        cut_idx = None
        for j, ln in enumerate(doc_lines):
            if any(m in ln for m in markers if m not in ("Сгенерируй развернутый СОП", "Выдай ТОЛЬКО готовый документ")):
                cut_idx = j
                break
        if cut_idx is not None and cut_idx > 0:
            doc_lines = doc_lines[:cut_idx]
        # Remove any stray marker lines that slipped through
        cleaned = [ln for ln in doc_lines if not any(m in ln for m in markers)]
        return "\n".join(cleaned).strip()

    # 4) Fallback: drop lines containing obvious markers anywhere
    cleaned = [ln for ln in lines if not any(m in ln for m in markers)]
    return "\n".join(cleaned).strip()


def _author_prompt(
    title: str,
    number: str,
    equipment_type: str,
    sections_text: str,
    content_mode: str,
    docs_summary: str | None,
    structure_hint: str | None,
) -> str:
    # Clip long inputs to keep within context
    sections_text = _clip_text(sections_text, _MAX_SECTIONS_TEXT_CHARS) or ""
    docs_summary = _clip_text(docs_summary, _MAX_DOCS_SUMMARY_CHARS)
    structure_hint = _clip_text(structure_hint, _MAX_STRUCTURE_HINT_CHARS)

    ctx = ""
    if content_mode == "ИИ + ссылка на документ" and docs_summary:
        ctx = f"\n\nИСТОЧНИКИ/СВОДКА ДЛЯ ИСПОЛЬЗОВАНИЯ:\n{docs_summary}\n"
    structure_part = f"\n\nСТРУКТУРА (ориентир):\n{structure_hint}\n" if structure_hint else ""
    equipment_part = f" для оборудования: {equipment_type}" if equipment_type else ""
    return (
        f"Сгенерируй развернутый СОП '{title}' (№ {number}){equipment_part}.\n"
        f"Ориентиры разделов (по одному на строку):\n{sections_text}\n"
        f"Требования: детальные шаги, параметры, безопасность, критерии приемки.{ctx}{structure_part}\n"
        "Выдай ТОЛЬКО готовый документ в Markdown, без комментариев. Заголовки разделов как '## N. <Название>'. "
        "Никогда не включай в ответ текст задания, метки 'Ориентиры разделов', 'ИСТОЧНИКИ/СВОДКА', 'СТРУКТУРА (ориентир)'; не цитируй исходные подсказки."
    )


def _critic_prompt(sop_text: str, structure_hint: str | None, equipment_type: str | None) -> str:
    sop_text = _clip_text(sop_text, _MAX_SOP_TEXT_FOR_CRITIC_CHARS) or ""
    extra = []
    if equipment_type:
        extra.append(f"Тип оборудования: {equipment_type}")
    if structure_hint:
        extra.append(f"Ожидаемая структура: {structure_hint}")
    guide = ("\n\n" + "\n".join(extra)) if extra else ""
    return (
        "Оцени следующий текст СОП и дай структурированную рецензию по правилам из своей роли." + guide + "\n\n"
        f"ТЕКСТ:\n{sop_text}"
    )


def _revision_prompt(previous_text: str, critic_feedback: str, structure_hint: str | None, equipment_type: str | None) -> str:
    previous_text = _clip_text(previous_text, _MAX_PREVIOUS_TEXT_CHARS) or ""
    critic_feedback = _clip_text(critic_feedback, _MAX_CRITIC_FEEDBACK_CHARS) or ""
    extra = []
    if equipment_type:
        extra.append(f"Тип оборудования: {equipment_type}")
    if structure_hint:
        extra.append(f"Ожидаемая структура: {structure_hint}")
    guide = ("\n" + "\n".join(extra)) if extra else ""
    return (
        "Перепиши полностью документ, устранив замечания критика. Сохрани формат Markdown и структуру.\n"
        "Выдай только финальный документ без пояснений.\n"
        "Не включай текст задания/подсказок ('Ориентиры разделов', 'ИСТОЧНИКИ/СВОДКА', 'СТРУКТУРА (ориентир)').\n"
        + guide + "\n\n"
        f"ЗАМЕЧАНИЯ КРИТИКА:\n{critic_feedback}\n\n"
        f"ТЕКУЩАЯ ВЕРСИЯ:\n{previous_text}"
    )


def run_author_critic_loop(
    sop_title: str,
    sop_number: str,
    equipment_type: str,
    sections_text: str,
    content_mode: str,
    docs_summary: str | None,
    structure_hint: str | None,
    max_iters: int = 5,
) -> Dict[str, Any]:
    """
    Run iterative Author↔Critic loop until Critic outputs 'Готово' or max_iters is reached.

    Returns:
        {"messages": transcript, "final_text": current_text}
    """
    author = build_author_agent()
    critic = build_critic_agent()

    transcript: List[Dict[str, str]] = []
    current_text = ""
    critic_feedback = ""

    for iteration in range(1, max_iters + 1):
        # Author writes or revises
        if iteration == 1 and not current_text:
            prompt = _author_prompt(
                title=sop_title,
                number=sop_number,
                equipment_type=equipment_type,
                sections_text=sections_text,
                content_mode=content_mode,
                docs_summary=docs_summary,
                structure_hint=structure_hint,
            )
        else:
            prompt = _revision_prompt(current_text, critic_feedback, structure_hint, equipment_type)
        author_msgs = _run(author, prompt)
        author_text = _sanitize_output(_extract_text(author_msgs))
        transcript.append({"sender": "Author", "content": author_text})
        current_text = author_text

        # Critic reviews
        critic_msgs = _run(critic, _critic_prompt(current_text, structure_hint, equipment_type))
        critic_text = _extract_text(critic_msgs)
        transcript.append({"sender": "Critic", "content": critic_text})

        if "готово" in critic_text.lower():
            break
        critic_feedback = critic_text

    return {"messages": transcript, "final_text": current_text} 