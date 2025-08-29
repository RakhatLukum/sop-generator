from typing import Dict, Any, List

from sop_generator.config.agent_config import AGENT_DEFAULTS, build_openai_chat_client
from sop_generator.config.prompts import SOP_GENERATOR_SYSTEM_PROMPT

# Try to import AssistantAgent with fallbacks
try:
    from autogen_agentchat.agents import AssistantAgent
except ImportError:
    try:
        from autogen.agentchat.agents import AssistantAgent
    except ImportError:
        try:
            from autogen import AssistantAgent
        except ImportError:
            # Create a mock AssistantAgent for deployment
            class AssistantAgent:
                def __init__(self, name, system_message, model_client):
                    self.name = name
                    self.system_message = system_message
                    self.model_client = model_client
                    print(f"Warning: Using mock AssistantAgent for {name}")
                
                async def generate_reply(self, messages):
                    try:
                        # Convert system message to message format
                        full_messages = [
                            {"role": "system", "content": self.system_message}
                        ]
                        
                        # Add user messages
                        if isinstance(messages, str):
                            full_messages.append({"role": "user", "content": messages})
                        elif isinstance(messages, list):
                            full_messages.extend(messages)
                        
                        # Get response from model client
                        response = await self.model_client.create(full_messages)
                        return response.choices[0].message.content
                    except Exception as e:
                        return f"Error generating reply: {e}"


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
    from utils.section_validator import create_mandatory_sections_template
    
    # Ensure mandatory sections are included
    mandatory_sections = create_mandatory_sections_template()
    user_section_titles = {s.get('title', '').lower() for s in sections}
    
    # Add any missing mandatory sections
    enhanced_sections = list(sections)
    for mandatory_section in mandatory_sections:
        if mandatory_section['title'].lower() not in user_section_titles:
            enhanced_sections.append(mandatory_section)
    
    corpus_part = f"\nТЕХНИЧЕСКАЯ ДОКУМЕНТАЦИЯ:\n{parsed_corpus_summary}\n" if parsed_corpus_summary else ""
    
    # Create detailed section specifications
    section_specifications = []
    for s in enhanced_sections:
        section_spec = f"- **{s['title']}** (режим: {s.get('mode', 'ai')})"
        if s.get('prompt'):
            section_spec += f"\n  Требования: {s['prompt']}"
        section_specifications.append(section_spec)
    
    structured_sections = "\n".join(section_specifications)
    
    critique_part = ""
    if critique_feedback:
        critique_part = f"\n**КРИТИКА ДЛЯ ИСПРАВЛЕНИЯ:**\n{critique_feedback}\n"
    
    return f"""Создай профессиональный СОП '{sop_title}' (№ {sop_number}) для оборудования: {equipment_type}.

**ОБЯЗАТЕЛЬНЫЕ ТРЕБОВАНИЯ К ДОКУМЕНТУ:**
1. Включи ВСЕ 9 обязательных разделов согласно отраслевым стандартам
2. Каждый раздел должен содержать конкретные технические детали
3. Интегрируй меры безопасности непосредственно в процедурные шаги
4. Укажи точные параметры, диапазоны значений, критерии успеха
5. Добавь ссылки на нормативные документы и стандарты

**СТРУКТУРА ДОКУМЕНТА:**
{structured_sections}

**ТЕХНИЧЕСКИЕ ТРЕБОВАНИЯ:**
- Конкретные значения параметров (температура, давление, время, объемы)
- Настройки оборудования с точными значениями
- Критерии успешного/неуспешного выполнения для каждого шага
- Требования к условиям окружающей среды
- Процедуры самодиагностики и калибровки

**ИНТЕГРАЦИЯ БЕЗОПАСНОСТИ:**
- Предупреждения **ВНИМАНИЕ** и **ПРЕДУПРЕЖДЕНИЕ** в критических точках
- Детальные требования к СИЗ для каждой операции
- Процедуры ЛОТО (блокировка/маркировка) где применимо
- Аварийные процедуры и контактная информация
- Ссылки на стандарты безопасности (ГОСТ, ISO 45001)

{corpus_part}{critique_part}

Создай документ, готовый к немедленному производственному использованию.""" 