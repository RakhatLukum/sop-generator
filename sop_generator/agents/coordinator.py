from typing import Callable, Dict, Any, List
import asyncio
import os
import re

from sop_generator.agents.base_imports import AssistantAgent, TextMessage, BaseChatMessage, MockResult
from sop_generator.utils.section_validator import SOPSectionValidator, create_mandatory_sections_template


# Helper: run a single agent with a user task and collect messages, with timeout


def _run_agent_and_get_messages(
    agent: AssistantAgent,
    task: str,
    timeout_s: int | None = None,
    conversation_logger: Callable[[str], None] | None = None,
    conversation_label: str | None = None,
) -> List[TextMessage]:
    # Determine effective timeout: 0 or None disables timeout entirely
    env_timeout_raw = os.getenv("LLM_TIMEOUT", "").strip()
    env_timeout = None
    try:
        if env_timeout_raw:
            env_timeout = int(env_timeout_raw)
    except ValueError:
        env_timeout = None
    effective_timeout = timeout_s if timeout_s is not None else env_timeout

    async def _runner():
        try:
            # Check if agent has run method (real autogen) or use generate_reply (mock)
            if hasattr(agent, 'run'):
                result = await agent.run(task=task)
                return result
            else:
                # For mock agents, use generate_reply
                reply = await agent.generate_reply(task)
                return MockResult([TextMessage(agent.name, reply)])
        except Exception as e:
            print(f"Agent execution error: {e}")
            return MockResult([TextMessage(agent.name, f"Error: {e}")])

    try:
        if effective_timeout and effective_timeout > 0:
            result = asyncio.run(asyncio.wait_for(_runner(), timeout=effective_timeout))
        else:
            # No timeout enforced
            result = asyncio.run(_runner())
    except asyncio.TimeoutError:
        raise TimeoutError(f"LLM timed out after {effective_timeout}s")
    except Exception as e:
        print(f"Async execution error: {e}")
        return [TextMessage(agent.name, f"Execution error: {e}")]
    
    # Return messages from result
    messages = getattr(result, "messages", [])
    chat_messages = [msg for msg in messages if isinstance(msg, (TextMessage, BaseChatMessage))]

    if conversation_logger:
        label = conversation_label or getattr(agent, "name", "Agent")
        for msg in chat_messages:
            content = getattr(msg, "content", "")
            if not content:
                continue
            speaker = getattr(msg, "source", None) or getattr(msg, "sender", None) or label
            conversation_logger(f"[{speaker}] {content.strip()}")

    return chat_messages


def _extract_clean_sop_content(raw_content: str) -> str:
    """Extract clean SOP content, removing agent conversation artifacts and duplications."""
    lines = raw_content.split('\n')
    clean_lines: list[str] = []
    skip_mode = False
    skip_until_next_header = False
    seen_headers: set[str] = set()
    skip_block_level: int = 0

    def is_header_line(s: str) -> bool:
        s = s.strip()
        return s.startswith('#') or (s.startswith('**') and s.endswith('**') and len(s) > 4)

    def parse_header(s: str) -> tuple[int, str]:
        """Return (level, normalized_title) for a header line, else (0, '')."""
        s_stripped = s.strip()
        level = 0
        title = s_stripped
        if s_stripped.startswith('#'):
            m = re.match(r"^(#+)\s*(.*)$", s_stripped)
            if m:
                level = len(m.group(1))
                title = m.group(2)
        elif s_stripped.startswith('**') and s_stripped.endswith('**'):
            level = 2
            title = s_stripped.strip('*')
        # Normalize title
        norm = re.sub(r"\s+", " ", title).strip().rstrip(':').lower()
        return level, norm

    for line in lines:
        line_stripped = line.strip()
        line_lower = line_stripped.lower()

        # Normalize a potential marker by dropping leading hashes/asterisks
        norm_marker = line_stripped.lstrip('#').lstrip('*').strip().lower().rstrip(':')

        # Skip known instruction scaffolding and meta markers
        if any(k in line_lower for k in [
            'критик:', 'безопасность:', 'контроль качества:', 'стилизация:', 'генератор:',
            'сгенерируй соп', 'разделы и режимы', 'требования:', 'оцени документ', 'текст:',
            'создай профессиональный', 'обязательные требования', 'структура документа',
            'критически важно', 'детальные спецификации разделов', 'техническая документация:',
            'шаблон для этого раздела', 'интеграция безопасности',
        ]):
            skip_mode = True
            continue

        # Skip critic blocks and approval metadata (SUMMARY/ISSUES/STATUS/COMMENTS)
        if norm_marker.startswith('summary') or norm_marker.startswith('issues') or norm_marker.startswith('status') or norm_marker.startswith('comments'):
            skip_until_next_header = True
            continue

        # Skip explicit pre-generation checks blocks
        if 'финальная проверка перед генерацией' in line_lower or 'критика для исправления' in line_lower:
            skip_until_next_header = True
            continue

        # If we are skipping a duplicate header block, check for header boundary to stop skipping
        if skip_block_level > 0 and is_header_line(line):
            lvl, _ = parse_header(line)
            if lvl <= skip_block_level:
                # End skipping at this new header; fall through to process it
                skip_block_level = 0
                skip_mode = False
                skip_until_next_header = False
            else:
                # Still within the same block depth; keep skipping
                continue

        # When a header appears, end skip regions and deduplicate header blocks
        if is_header_line(line):
            skip_mode = False
            if skip_until_next_header:
                skip_until_next_header = False
            lvl, norm_title = parse_header(line)
            if norm_title:
                if norm_title in seen_headers:
                    # Skip this entire header block content until a header of same or higher level
                    skip_block_level = max(lvl, 1)
                    continue
                seen_headers.add(norm_title)

        if skip_mode or skip_until_next_header or skip_block_level > 0:
            continue

        clean_lines.append(line)

    # Collapse multiple blank lines
    result_lines: list[str] = []
    prev_blank = False
    for l in clean_lines:
        is_blank = not l.strip()
        if is_blank and prev_blank:
            continue
        result_lines.append(l)
        prev_blank = is_blank

    return '\n'.join(result_lines).strip()


def _truncate_to_single_section(text: str) -> str:
    """Keep only the first section-sized chunk of text."""
    if not text:
        return ""
    trimmed = text.strip()
    if not trimmed:
        return ""

    numbered_header = re.search(r"\n##\s+\d+\.\s+", trimmed)
    if numbered_header:
        return trimmed[:numbered_header.start()].strip()

    any_header = re.search(r"\n##\s+", trimmed)
    if any_header:
        return trimmed[:any_header.start()].strip()

    return trimmed


def _normalize_section_output(index: int, title: str, raw_text: str) -> tuple[str, str]:
    """Ensure section text has the expected header and return (full_section, body_only)."""
    header = f"## {index}. {title}"
    content = raw_text.strip()
    if not content:
        return header, ""

    lines = content.splitlines()
    if lines:
        first_line = lines[0].strip()
        if first_line.startswith('#') or (first_line.startswith('**') and first_line.endswith('**')):
            lines = lines[1:]

    body = "\n".join(lines).strip()
    if body:
        return f"{header}\n\n{body}", body
    return header, ""


def _generate_sections_incrementally(
    sop_agent: AssistantAgent,
    base_instruction: str,
    sections: List[Dict[str, Any]],
    meta: Dict[str, Any] | None,
    corpus_summary: str | None,
    logger: Callable[[str], None] | None = None,
) -> tuple[str, List[Dict[str, str]]]:
    accumulated_markdown: list[str] = []
    produced_sections: list[Dict[str, str]] = []
    prior_context = ""
    total = len(sections)

    for index, section in enumerate(sections, start=1):
        title = (section.get("title") or f"Раздел {index}").strip()
        mode = (section.get("mode") or "ai").strip().lower()
        prompt_hint = (section.get("prompt") or "").strip()
        manual_content = (section.get("content") or "").strip()

        if mode == "manual" and manual_content:
            full_section, body = _normalize_section_output(index, title, manual_content)
            produced_sections.append({"title": title, "content": body})
            accumulated_markdown.append(full_section)
            prior_context = "\n\n".join(accumulated_markdown).strip()
            if logger:
                logger(f"Раздел {index} заполнен вручную (символов: {len(body)})")
            continue

        prompt_parts: list[str] = [base_instruction.strip()]

        meta_lines: list[str] = []
        if meta:
            title_meta = meta.get("title") or meta.get("sop_title")
            number_meta = meta.get("number") or meta.get("sop_number")
            equipment_meta = meta.get("equipment") or meta.get("equipment_type")
            if title_meta:
                meta_lines.append(f"Название: {str(title_meta).strip()}")
            if number_meta:
                meta_lines.append(f"Номер: {str(number_meta).strip()}")
            if equipment_meta:
                meta_lines.append(f"Оборудование: {str(equipment_meta).strip()}")
        if meta_lines:
            prompt_parts.append("\n".join(meta_lines))

        prompt_parts.append(
            f"Сформируй раздел {index} из {total}: '{title}'. Верни только этот раздел в Markdown."
        )
        prompt_parts.append(
            f"Заголовок раздела должен иметь вид `## {index}. {title}`."
        )
        if prompt_hint:
            prompt_parts.append("Требования пользователя:\n" + prompt_hint)
        if corpus_summary:
            prompt_parts.append("Сводка по документации:\n" + corpus_summary.strip())
        if prior_context:
            prompt_parts.append(
                "Контекст предыдущих разделов (не изменяй их, используй только для согласованности):\n"
                + prior_context
            )

        section_prompt = "\n\n".join(part for part in prompt_parts if part).strip()

        section_logger = (lambda text, idx=index: logger(f"[SECTION {idx}] {text}")) if logger else None
        messages = _run_agent_and_get_messages(
            sop_agent,
            section_prompt,
            conversation_logger=section_logger,
            conversation_label=f"{getattr(sop_agent, 'name', 'Generator')} / {index}",
        )
        raw_output = "\n\n".join(
            m.content for m in messages if isinstance(m, TextMessage)
        ).strip()
        raw_output = _extract_clean_sop_content(raw_output)
        raw_output = _truncate_to_single_section(raw_output)

        full_section, body = _normalize_section_output(index, title, raw_output)
        produced_sections.append({"title": title, "content": body})
        accumulated_markdown.append(full_section)
        prior_context = "\n\n".join(accumulated_markdown).strip()

        if logger:
            logger(f"Раздел {index} готов (символов: {len(body)})")

    combined_document = "\n\n".join(accumulated_markdown).strip()
    return combined_document, produced_sections


# Apply a strict outline with numbered H2 headers for mandatory sections
MANDATORY_SECTION_TITLES: list[str] = [
    "Цель и область применения",
    "Ответственность и обучение",
    "Анализ рисков и безопасность",
    "Оборудование и материалы",
    "Пошаговые процедуры",
    "Контроль качества",
    "Документооборот и записи",
    "Нормативные ссылки",
    "Устранение неисправностей",
]

# Common synonyms to help map headings to official titles
_SECTION_SYNONYMS: dict[str, list[str]] = {
    "Цель и область применения": ["цель", "назначение", "область применения", "scope"],
    "Ответственность и обучение": ["ответствен", "обучен", "квалификац", "роли", "персонал"],
    "Анализ рисков и безопасность": ["риск", "опасн", "безопасн", "сиз", "предупрежд"],
    "Оборудование и материалы": ["оборудован", "материал", "спецификац", "модель", "комплектация"],
    "Пошаговые процедуры": ["процедур", "шаг", "порядок", "инструкция", "выполнен", "последователь", "операц", "этап", "процесс", "workflow"],
    "Контроль качества": ["качест", "контроль", "приемк", "валидац", "критер"],
    "Документооборот и записи": ["документ", "запис", "учет", "журнал", "архив"],
    "Нормативные ссылки": ["ссылк", "норматив", "стандарт", "gost", "iso"],
    "Устранение неисправностей": ["неисправ", "проблем", "диагност", "troubleshoot"],
}


def _enforce_strict_outline(clean_content: str) -> str:
    """Re-map headings to the official order and enforce '## N. Title' formatting.
    Keeps the original body text of each section (first occurrence), drops duplicates,
    and ignores non-matching headers. Unknown content remains in place after the main sections.
    """
    lines = clean_content.split('\n')

    def _is_header(s: str) -> bool:
        s = s.strip()
        if not s:
            return False
        if s.startswith('#'):
            return True
        # Bold-only line as header
        if s.startswith('**') and s.endswith('**') and len(s) > 4:
            return True
        # A plain numbered header like "1. ..." on its own line
        if re.match(r"^\d+\.\s+[^\-].{0,120}$", s):
            return True
        return False

    def _map_to_official(title_text: str) -> str | None:
        norm = title_text.strip().strip('*# ').rstrip(':').lower()
        # Try direct match
        for official in MANDATORY_SECTION_TITLES:
            if norm == official.lower():
                return official
        # Try contains/synonyms
        for official, keys in _SECTION_SYNONYMS.items():
            if any(k in norm for k in keys):
                return official
        return None

    # Collect content by official title
    collected: dict[str, list[str]] = {t: [] for t in MANDATORY_SECTION_TITLES}
    used: set[str] = set()

    current_official: str | None = None
    buffer: list[str] = []

    def _buffer_has_text(buf: list[str]) -> bool:
        return any((l.strip() for l in buf))

    def _flush():
        nonlocal current_official, buffer
        if current_official is not None and _buffer_has_text(buffer):
            if current_official not in used:
                collected[current_official] = buffer.copy()
                used.add(current_official)
        buffer = []

    for line in lines:
        if _is_header(line):
            # Before switching, flush collected content for the previous section
            _flush()

            stripped = line.strip()
            stripped = stripped.lstrip('#').strip()
            stripped = stripped.strip('*').strip()

            mapped = None
            header_core = stripped

            # Detect explicit numbering like "5." or "Раздел 5." to map by index
            number_match = re.match(r"^(?:раздел\s+)?(\d+)[\.|\)]?\s*(.*)$", header_core, re.IGNORECASE)
            if number_match:
                section_idx = int(number_match.group(1))
                if 1 <= section_idx <= len(MANDATORY_SECTION_TITLES):
                    mapped = MANDATORY_SECTION_TITLES[section_idx - 1]
                header_core = number_match.group(2).strip()

            # Remove residual numeric prefixes like "-" or "–" after the number
            header_core = re.sub(r"^[\-–—)]\s*", "", header_core)

            # Try to map header text to an official title using synonyms
            mapped = mapped or _map_to_official(header_core)
            if not mapped and header_core:
                mapped = _map_to_official(header_core.rstrip('.'))

            # As a final fallback, attempt to map using the original stripped header
            if not mapped:
                remaining = [title for title in MANDATORY_SECTION_TITLES if title not in used]
                if remaining:
                    mapped = remaining[0]
            if not mapped:
                mapped = _map_to_official(stripped)

            current_official = mapped
            continue
        # Accumulate section body lines only when we have an active mapped section
        if current_official is not None:
            buffer.append(line)

    # Flush last buffer
    _flush()

    # Build the final document in strict order
    out_lines: list[str] = []
    placeholder_template = "**Требуется дополнить этот раздел детальными данными.**"

    for idx, official in enumerate(MANDATORY_SECTION_TITLES, start=1):
        section_body_lines = [l for l in collected.get(official, [])]
        has_content = any(l.strip() for l in section_body_lines)

        out_lines.append(f"## {idx}. {official}")

        if has_content:
            # Trim leading/trailing blanks within section and collapse excessive blank lines
            prev_blank = True
            for l in section_body_lines:
                is_blank = not l.strip()
                if is_blank and prev_blank:
                    continue
                out_lines.append(l)
                prev_blank = is_blank
        else:
            out_lines.append(placeholder_template)

        out_lines.append("")

    # Return formatted document (without leading/trailing newlines)
    return "\n".join([l.rstrip() for l in out_lines]).strip()


def _get_section_block(document: str, section_title: str) -> str | None:
    try:
        idx = MANDATORY_SECTION_TITLES.index(section_title) + 1
    except ValueError:
        return None
    pattern = re.compile(
        rf"##\s+{idx}\.\s+{re.escape(section_title)}\s*\n.*?(?=\n##\s+\d+\.\s+|$)",
        re.DOTALL
    )
    match = pattern.search(document)
    if match:
        return match.group(0).strip()
    return None


def _get_section_body(document: str, section_title: str) -> str:
    block = _get_section_block(document, section_title)
    if not block:
        return ""
    lines = block.splitlines()
    if lines and lines[0].strip().startswith("##"):
        lines = lines[1:]
    return "\n".join(lines).strip()


def _remove_section_block(document: str, section_title: str) -> str:
    block = _get_section_block(document, section_title)
    if not block:
        return document
    return document.replace(block, "").strip()


def _replace_section_block(document: str, section_title: str, new_block: str) -> str:
    try:
        idx = MANDATORY_SECTION_TITLES.index(section_title) + 1
    except ValueError:
        return document

    new_block = new_block.strip()
    if not new_block:
        return document

    if not new_block.lower().startswith(f"## {idx}."):
        header = f"## {idx}. {section_title}"
        new_block = f"{header}\n\n{new_block.strip()}"

    pattern = re.compile(
        rf"##\s+{idx}\.\s+{re.escape(section_title)}\s*\n.*?(?=\n##\s+\d+\.\s+|$)",
        re.DOTALL
    )
    match = pattern.search(document)
    replacement = new_block.strip() + "\n\n"
    if match:
        return document[:match.start()] + replacement + document[match.end():]

    if idx == 1:
        return replacement + document

    prev_title = MANDATORY_SECTION_TITLES[idx - 2]
    prev_pattern = re.compile(
        rf"##\s+{idx - 1}\.\s+{re.escape(prev_title)}\s*\n.*?(?=\n##\s+\d+\.\s+|$)",
        re.DOTALL
    )
    prev_match = prev_pattern.search(document)
    if prev_match:
        insert_pos = prev_match.end()
        return document[:insert_pos] + "\n" + replacement + document[insert_pos:]

    return document.rstrip() + "\n\n" + replacement


def _auto_backfill_sections(
    document: str,
    sop_agent: AssistantAgent,
    meta: Dict[str, Any],
    corpus_summary: str | None,
    logger: Callable[[str], None] | None = None,
) -> tuple[str, list[str]]:
    validator = SOPSectionValidator()
    _, missing_sections = validator.validate_section_presence(document)
    quality = validator.validate_section_content_quality(document)

    placeholder_marker = "**Требуется дополнить этот раздел детальными данными.**"
    sections_to_fill: set[str] = set(missing_sections)

    for title in MANDATORY_SECTION_TITLES:
        body = _get_section_body(document, title)
        info = quality.get(title, {})
        if not body:
            sections_to_fill.add(title)
            continue
        if placeholder_marker in body:
            sections_to_fill.add(title)
            continue
        if not info.get("meets_min_length", True):
            sections_to_fill.add(title)
            continue
        if not info.get("has_sufficient_keywords", True):
            sections_to_fill.add(title)
            continue

    if not sections_to_fill:
        return document, []

    templates = {item["title"]: item.get("prompt", "") for item in create_mandatory_sections_template()}
    filled_sections: list[str] = []

    for title in sections_to_fill:
        try:
            section_idx = MANDATORY_SECTION_TITLES.index(title) + 1
        except ValueError:
            continue

        context_without_section = _remove_section_block(document, title)
        template_hint = templates.get(title, "")

        prompt_parts = [
            "Ты выступаешь как профессиональный автор стандартных операционных процедур.",
            "Сформируй полностью содержимое конкретного раздела СОП.",
            f"Название документа: {meta.get('title') or 'СОП'} (№ {meta.get('number') or '—'})",
        ]
        equipment = meta.get('equipment') or meta.get('equipment_type')
        if equipment:
            prompt_parts.append(f"Тип оборудования: {equipment}")
        prompt_parts.append(
            f"Раздел: '## {section_idx}. {title}'. Верни только этот раздел в Markdown, не добавляй другие разделы и комментарии."
        )
        if template_hint:
            prompt_parts.append(template_hint)
        if corpus_summary:
            prompt_parts.append(f"Сводка по документам:\n{corpus_summary.strip()}")
        if context_without_section:
            prompt_parts.append(
                "Контекст других разделов (оставь их без изменений, не копируй):\n" + context_without_section.strip()
            )

        prompt = "\n\n".join(part for part in prompt_parts if part).strip()

        conv_logger = (lambda text: logger(f"[AUTO] {text}")) if logger else None
        messages = _run_agent_and_get_messages(
            sop_agent,
            prompt,
            conversation_logger=conv_logger,
            conversation_label=f"{sop_agent.name} (auto)" if hasattr(sop_agent, "name") else "Generator",
        )
        section_text = "\n\n".join(m.content for m in messages if isinstance(m, TextMessage)).strip()
        if not section_text:
            continue

        document = _replace_section_block(document, title, section_text)
        filled_sections.append(title)

    if filled_sections and logger:
        logger("Автодополнение разделов: " + ", ".join(filled_sections))

    document = _enforce_strict_outline(document)
    return document, filled_sections


def iterative_generate_until_approved(
    sop_gen: AssistantAgent,
    critic: AssistantAgent,
    base_instruction_builder,
    sections: List[Dict[str, Any]] | None = None,
    max_iters: int = 5,
    enforce_mandatory_sections: bool = True,
    logger: Callable[[str], None] | None = None,
    auto_backfill_meta: Dict[str, Any] | None = None,
    auto_backfill_summary: str | None = None,
) -> Dict[str, Any]:
    logs: List[str] = []
    clean_sop_content: str = ""
    feedback: str = ""

    def _log(s: str) -> None:
        if logger:
            try:
                logger(s)
            except Exception:
                pass

    sections_list: List[Dict[str, Any]] = [dict(s) for s in sections] if sections else []
    latest_sections_output: List[Dict[str, str]] = []

    for iteration in range(1, max_iters + 1):
        _log(f"Итерация {iteration}: генерация...")
        structural_feedback = ""

        try:
            instruction = base_instruction_builder(feedback)
            if enforce_mandatory_sections:
                gen_conv_logger = (lambda text: _log(f"[GENERATOR] {text}"))
                gen_msgs = _run_agent_and_get_messages(
                    sop_gen,
                    instruction,
                    conversation_logger=gen_conv_logger,
                    conversation_label=getattr(sop_gen, "name", "Generator"),
                )
                raw_generated_content = "\n\n".join(
                    m.content for m in gen_msgs if isinstance(m, TextMessage)
                )
                clean_sop_content = _extract_clean_sop_content(raw_generated_content)
                clean_sop_content = _enforce_strict_outline(clean_sop_content)
                if auto_backfill_meta is not None:
                    clean_sop_content, _ = _auto_backfill_sections(
                        clean_sop_content,
                        sop_gen,
                        auto_backfill_meta,
                        auto_backfill_summary,
                        logger=_log,
                    )
                latest_sections_output = []
            else:
                clean_sop_content, latest_sections_output = _generate_sections_incrementally(
                    sop_gen,
                    instruction,
                    sections_list,
                    auto_backfill_meta or {},
                    auto_backfill_summary,
                    logger=_log,
                )
            _log(f"Генерация завершена. Длина: {len(clean_sop_content)} симв.")
        except Exception as e:
            _log(f"Ошибка генератора: {e}")
            break

        if enforce_mandatory_sections:
            # Structural validation to ensure all mandatory sections are present
            validator = SOPSectionValidator()
            _, missing_sections = validator.validate_section_presence(clean_sop_content)
            section_quality = validator.validate_section_content_quality(clean_sop_content)

            structural_feedback_parts: list[str] = []
            if missing_sections:
                structural_feedback_parts.append(
                    "Добавь недостающие обязательные разделы: " + ", ".join(missing_sections)
                )

            weak_sections = [
                title for title, info in section_quality.items()
                if info.get("found") and not info.get("has_sufficient_keywords")
            ]
            if weak_sections:
                structural_feedback_parts.append(
                    "Усиль содержательное наполнение разделов: " + ", ".join(weak_sections)
                )

            structural_feedback = "\n".join(structural_feedback_parts)
            if structural_feedback:
                _log(f"Структурные замечания: {structural_feedback}")

        _log("Рецензирование критиком...")
        try:
            critic_prompt = f"""Оцени документ по протоколу (SUMMARY/ISSUES/STATUS).

ТЕКСТ СОП:
{clean_sop_content}
"""
            critic_conv_logger = (lambda text: _log(f"[CRITIC] {text}"))
            critic_msgs = _run_agent_and_get_messages(
                critic,
                critic_prompt,
                conversation_logger=critic_conv_logger,
                conversation_label=getattr(critic, "name", "Critic"),
            )
            critic_texts = [m.content for m in critic_msgs if isinstance(m, TextMessage)]
            feedback = "\n\n".join(critic_texts)
            status_approved = any("STATUS:" in t and "APPROVED" in t for t in critic_texts)
            _log(f"Статус критика: {'APPROVED' if status_approved else 'REVISE'}")
        except Exception as e:
            _log(f"Ошибка критика: {e}")
            break

        if structural_feedback:
            status_approved = False
            feedback = (feedback + "\n\n" + structural_feedback).strip() if feedback else structural_feedback

        if status_approved:
            _log("Документ одобрен критиком.")
            final_content = clean_sop_content
            return {
                "content": final_content,
                "approved": True,
                "feedback": feedback,
                "logs": logs,
                "sections": latest_sections_output,
            }

        _log("Критик запросил правки. Повтор итерации.")

    return {
        "content": clean_sop_content,
        "approved": False,
        "feedback": feedback,
        "logs": logs,
        "sections": latest_sections_output,
    } 
