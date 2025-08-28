from typing import Dict, Any, List
from autogen_agentchat.agents import AssistantAgent

from config.agent_config import AGENT_DEFAULTS, build_openai_chat_client
from config.prompts import SOP_GENERATOR_SYSTEM_PROMPT


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
    corpus_part = f"\nДОКУМЕНТЫ (краткое содержание):\n{parsed_corpus_summary}\n" if parsed_corpus_summary else ""
    structured_sections = "\n".join(
        [
            f"- Раздел: {s['title']} | режим: {s['mode']} | подсказка: {s.get('prompt','')}"
            for s in sections
        ]
    )
    critique_part = f"\nУЧТИ КРИТИКУ И ИСПРАВЬ: \n{critique_feedback}\n" if critique_feedback else ""
    return (
        f"Сгенерируй СОП '{sop_title}' (№ {sop_number}) для оборудования: {equipment_type}.\n"
        f"Разделы и режимы генерации:\n{structured_sections}\n"
        f"Требования: четкие шаги, ссылки на мануалы, безопасность, placeholders для изображений."
        f"{corpus_part}{critique_part}"
    ) 