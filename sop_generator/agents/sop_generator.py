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

    # Use user-specified sections when provided; otherwise fall back to recommended templates
    user_sections = [dict(s) for s in sections] if sections else []
    recommended_sections = create_mandatory_sections_template()
    enhanced_sections = user_sections if user_sections else recommended_sections
    
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
    
    section_specifications: list[str] = []
    if user_sections:
        for s in enhanced_sections:
            section_title = s['title']
            section_key = section_title.lower()
            block_lines: list[str] = [f"- **{section_title}**"]
            if s.get('mode'):
                block_lines.append(f"  - Режим пользователя: {s.get('mode', 'ai')}")
            if s.get('prompt'):
                block_lines.append(f"  - Требования пользователя: {s['prompt']}")

            template_key = None
            for key in section_templates.keys():
                if key in section_key:
                    template_key = key
                    break

            if template_key:
                template_hint = section_templates[template_key].strip()
                block_lines.append("  - Рекомендуемый фокус (адаптируй при необходимости):")
                for hint_line in template_hint.splitlines():
                    block_lines.append(f"    {hint_line}")

            block_lines.append(
                "  - Используй этот пункт только если он усиливает итоговый документ; "
                "можно объединять, переименовывать или опускать темы, чтобы структура "
                "оставалась логичной и без повторов."
            )

            section_specifications.append("\n".join(block_lines))
    else:
        suggestion_lines: list[str] = []
        for rec in recommended_sections:
            title = rec.get('title', '').strip() or "Раздел"
            template_key = None
            lower_title = title.lower()
            for key in section_templates.keys():
                if key in lower_title:
                    template_key = key
                    break

            focus_summary = ""
            if template_key:
                template_hint = section_templates[template_key]
                focus_points = [
                    line.strip('- ').strip()
                    for line in template_hint.splitlines()
                    if line.strip().startswith('-')
                ]
                if focus_points:
                    focus_summary = "; ".join(focus_points[:3])

            if focus_summary:
                suggestion_lines.append(f"{title}: {focus_summary}")
            else:
                suggestion_lines.append(title)

        if suggestion_lines:
            section_specifications.append(
                "- Рассмотри включение тем (при необходимости объединяй или заменяй их своими): "
                + "; ".join(suggestion_lines)
                + "."
            )
            section_specifications.append(
                "- Добавляй собственные разделы, если они критичны для оборудования, процессов, обучения или контроля."
            )

    structured_sections = "\n\n".join(section_specifications)
    
    critique_part = ""
    if critique_feedback:
        critique_part = f"\n**КРИТИКА ДЛЯ ИСПРАВЛЕНИЯ:**\n{critique_feedback}\n"
    
    sop_title = sop_title or "СОП"
    sop_number = sop_number or "—"
    equipment_type = equipment_type or "не указан"

    section_guidance = structured_sections if section_specifications else "- Ориентируйся на входные данные пользователя"

    return f"""Создай профессиональный СОП '{sop_title}' (№ {sop_number}) для оборудования: {equipment_type}.

**СТРУКТУРА ДОКУМЕНТА:**
- Сначала разработай оптимальную структуру — выбери количество разделов, подходящее под задачу (обычно 5–12, но опирайся на логику).
- Используй Markdown: каждый основной раздел начинай с заголовка `##`, при необходимости добавляй подразделы `###`.
- Если пользователь указал разделы, сохрани их смысл и приоритет, но объединяй или расширяй, когда это упрощает чтение.
- Не считай рекомендованные темы обязательным перечнем; выбирай только нужные и дополняй собственными.
- Избегай дублирования информации между разделами и обеспечивай связный поток.

**РЕКОМЕНДУЕМЫЕ ТЕМЫ ДЛЯ ПОКРЫТИЯ (адаптируй по ситуации):**
{section_guidance}

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
- Убедись, что каждый раздел раскрывает уникальную часть процесса
- Проверь, что нет повторений между разделами
- Документ должен быть готов к производственному использованию без дополнительных правок

Создай документ, готовый к немедленному производственному использованию."""
