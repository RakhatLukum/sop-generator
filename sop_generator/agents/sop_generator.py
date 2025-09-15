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
    from sop_generator.utils.section_validator import create_mandatory_sections_template
    
    # Ensure mandatory sections are included
    mandatory_sections = create_mandatory_sections_template()
    user_section_titles = {s.get('title', '').lower() for s in sections}
    
    # Add any missing mandatory sections
    enhanced_sections = list(sections)
    for mandatory_section in mandatory_sections:
        if mandatory_section['title'].lower() not in user_section_titles:
            enhanced_sections.append(mandatory_section)
    
    corpus_part = f"\nТЕХНИЧЕСКАЯ ДОКУМЕНТАЦИЯ:\n{parsed_corpus_summary}\n" if parsed_corpus_summary else ""
    
    # Create detailed section specifications with explicit templates
    section_specifications = []
    section_templates = {
        "цель и область применения": """
**ШАБЛОН ДЛЯ ЭТОГО РАЗДЕЛА:**
- Точная формулировка цели процедуры
- Границы применения (что включено)
- Четкие ограничения (что НЕ включено)
- Исключения и особые случаи
- НЕ ВКЛЮЧАТЬ: процедуры, технические детали, оборудование""",
        
        "ответственность и обучение": """
**ШАБЛОН ДЛЯ ЭТОГО РАЗДЕЛА:**
- Роли и обязанности каждой должности
- Требования к квалификации и сертификации
- Программа обучения и переаттестации
- Система допусков к работе
- НЕ ВКЛЮЧАТЬ: технические процедуры, оборудование, безопасность""",
        
        "анализ рисков и безопасность": """
**ШАБЛОН ДЛЯ ЭТОГО РАЗДЕЛА:**
- Идентификация конкретных опасностей
- Оценка рисков (вероятность × последствия)
- Меры предотвращения и защиты
- Требования к СИЗ по операциям
- Аварийные процедуры и контакты
- НЕ ВКЛЮЧАТЬ: основные рабочие процедуры, оборудование""",
        
        "оборудование и материалы": """
**ШАБЛОН ДЛЯ ЭТОГО РАЗДЕЛА:**
- Полный перечень оборудования с моделями
- Технические характеристики и спецификации
- Требования к материалам и реагентам
- Условия хранения и срок годности
- НЕ ВКЛЮЧАТЬ: как использовать оборудование, процедуры""",
        
        "пошаговые процедуры": """
**ШАБЛОН ДЛЯ ЭТОГО РАЗДЕЛА:**
- Детальная последовательность действий
- Конкретные параметры (температура, время, объемы)
- Критерии успешного выполнения каждого шага
- Контрольные точки и проверки
- НЕ ВКЛЮЧАТЬ: описания оборудования, теорию, безопасность""",
        
        "контроль качества": """
**ШАБЛОН ДЛЯ ЭТОГО РАЗДЕЛА:**
- Критерии приемки результатов
- Методы контроля и валидации
- Допустимые отклонения и RSD
- Частота и объем контрольных проб
- НЕ ВКЛЮЧАТЬ: основные процедуры, оборудование""",
        
        "документооборот": """
**ШАБЛОН ДЛЯ ЭТОГО РАЗДЕЛА:**
- Обязательные записи и журналы
- Форматы документов и отчетов
- Сроки хранения документации
- Процедуры архивирования
- НЕ ВКЛЮЧАТЬ: технические процедуры, оборудование""",
        
        "устранение неисправностей": """
**ШАБЛОН ДЛЯ ЭТОГО РАЗДЕЛА:**
- Таблица Симптом → Вероятная причина → Действие
- Диагностические процедуры
- Критерии для вызова сервиса
- Процедуры восстановления работы
- НЕ ВКЛЮЧАТЬ: нормальные рабочие процедуры"""
    }
    
    for i, s in enumerate(enhanced_sections):
        section_title = s['title'].lower()
        section_spec = f"**РАЗДЕЛ {i+1}: {s['title']}** (режим: {s.get('mode', 'ai')})"
        
        if s.get('prompt'):
            section_spec += f"\nТребования пользователя: {s['prompt']}"
        
        # Add section-specific template
        template_key = None
        for key in section_templates.keys():
            if key in section_title:
                template_key = key
                break
        
        if template_key:
            section_spec += section_templates[template_key]
        
        section_spec += f"\n**КРИТИЧЕСКИ ВАЖНО ДЛЯ РАЗДЕЛА {i+1}:** Создай УНИКАЛЬНЫЙ контент, НЕ дублируй информацию из других разделов!\n"
        
        section_specifications.append(section_spec)
    
    structured_sections = "\n\n".join(section_specifications)
    
    critique_part = ""
    if critique_feedback:
        critique_part = f"\n**КРИТИКА ДЛЯ ИСПРАВЛЕНИЯ:**\n{critique_feedback}\n"
    
    return f"""Создай профессиональный СОП '{sop_title}' (№ {sop_number}) для оборудования: {equipment_type}.

**КРИТИЧЕСКИ ВАЖНО - ИЗБЕГАЙ ДУБЛИРОВАНИЯ:**
🚫 ЗАПРЕЩЕНО копировать контент между разделами
🚫 ЗАПРЕЩЕНО повторять одинаковые процедуры в разных местах
✅ ОБЯЗАТЕЛЬНО создавай уникальный контент для каждого раздела
✅ ОБЯЗАТЕЛЬНО следуй шаблонам разделов ниже

**ОБЯЗАТЕЛЬНЫЕ ТРЕБОВАНИЯ К ДОКУМЕНТУ:**
1. Включи ВСЕ 9 обязательных разделов согласно отраслевым стандартам
2. Каждый раздел должен содержать ТОЛЬКО свою специфическую информацию
3. Интегрируй меры безопасности непосредственно в процедурные шаги
4. Укажи точные параметры, диапазоны значений, критерии успеха
5. Добавь ссылки на нормативные документы и стандарты

**ДЕТАЛЬНЫЕ СПЕЦИФИКАЦИИ РАЗДЕЛОВ:**
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

**ФИНАЛЬНАЯ ПРОВЕРКА ПЕРЕД ГЕНЕРАЦИЕЙ:**
- Убедись, что каждый раздел содержит РАЗНУЮ информацию
- Проверь, что нет повторений между разделами
- Каждый раздел должен быть самостоятельным и уникальным

Создай документ, готовый к немедленному производственному использованию.""" 