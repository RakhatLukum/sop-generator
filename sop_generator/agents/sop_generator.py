from typing import Dict, Any, List

from sop_generator.config.agent_config import AGENT_DEFAULTS, build_openai_chat_client
from sop_generator.config.prompts import SOP_GENERATOR_SYSTEM_PROMPT
from sop_generator.agents.base_imports import AssistantAgent


def build_sop_generator() -> AssistantAgent:
    cfg = AGENT_DEFAULTS["sop_generator"]["llm_config"]
    model_client = build_openai_chat_client(cfg)
    return AssistantAgent(
        name=AGENT_DEFAULTS["sop_generator"]["name"],
        system_message=SOP_GENERATOR_SYSTEM_PROMPT,
        model_client=model_client,
    )


def build_generation_instruction(
    sop_title: str,
    sop_number: str,
    equipment_type: str,
    sections: List[Dict[str, Any]],
    parsed_corpus_summary: str | None,
    critique_feedback: str | None = None,
) -> str:
    user_sections = [dict(s) for s in sections if s.get("title")] if sections else []
    if not user_sections:
        raise ValueError("Для генерации требуется как минимум один раздел")

    sop_title = (sop_title or "СОП").strip()
    sop_number = (sop_number or "—").strip()
    equipment_type = (equipment_type or "не указан").strip()

    section_lines: list[str] = []
    for idx, section in enumerate(user_sections, start=1):
        title = section.get("title", "").strip() or f"Раздел {idx}"
        mode = section.get("mode", "ai").strip()
        prompt_hint = section.get("prompt", "").strip()

        line_parts = [f"{idx}. {title}"]
        if mode and mode != "ai":
            line_parts.append(f"режим: {mode}")
        if prompt_hint:
            line_parts.append(f"требования: {prompt_hint}")
        section_lines.append(" — ".join(line_parts))

    sections_overview = "\n".join(f"- {line}" for line in section_lines)

    corpus_part = ""
    if parsed_corpus_summary:
        corpus_part = "\n**ДОПОЛНИТЕЛЬНЫЙ КОНТЕКСТ ИЗ ДОКУМЕНТОВ:**\n" + parsed_corpus_summary.strip()

    critique_part = ""
    if critique_feedback:
        critique_part = "\n**УЧТИ СЛЕДУЮЩИЕ ЗАМЕЧАНИЯ:**\n" + critique_feedback.strip()

    return f"""Подготовь стандартную операционную процедуру '{sop_title}' (№ {sop_number}) для оборудования: {equipment_type}.

**РАБОТАЙ СТРОГО С ПЕРЕЧИСЛЕННЫМИ РАЗДЕЛАМИ:**
{sections_overview}

**КЛЮЧЕВЫЕ ПРАВИЛА:**
- Генерируй разделы последовательно и возвращай только один раздел за вызов.
- Используй ранее сгенерированные разделы как обязательный контекст, не переписывая их.
- Не добавляй новые разделы и не меняй порядок.
- Сохраняй техническую детальность, единый стиль и четкую логику изложения.

**ОБЩИЕ ТРЕБОВАНИЯ К СОДЕРЖАНИЮ:**
- Фиксируй параметры, контрольные точки, критерии приемки и риски.
- Указывай оборудование, материалы, СИЗ и нормативные ссылки, если это уместно.
- Делай текст готовым к непосредственному использованию в производственных условиях.

{corpus_part}{critique_part}
"""
