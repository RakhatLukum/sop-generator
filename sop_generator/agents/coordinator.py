from typing import Callable, Dict, Any, List
import asyncio
import os
import re

from sop_generator.agents.base_imports import AssistantAgent, TextMessage, BaseChatMessage, MockResult


# Helper: run a single agent with a user task and collect messages, with timeout


def _run_agent_and_get_messages(agent: AssistantAgent, task: str, timeout_s: int | None = None) -> List[TextMessage]:
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
    return [msg for msg in messages if isinstance(msg, (TextMessage, BaseChatMessage))]


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
    "Пошаговые процедуры": ["процедур", "шаг", "порядок", "инструкция", "выполнен"],
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

    def _flush():
        nonlocal current_official, buffer
        if current_official is not None and buffer:
            if current_official not in used:
                collected[current_official] = buffer.copy()
                used.add(current_official)
        buffer = []

    for line in lines:
        if _is_header(line):
            # Before switching, flush
            _flush()
            # Determine mapped official
            # Extract raw header text without leading hashes and numbering
            raw = re.sub(r"^#+\s*", "", line.strip())
            raw = re.sub(r"^\d+\.\s*", "", raw)
            raw = raw.strip().strip('*').strip()
            mapped = _map_to_official(raw)
            current_official = mapped
            continue
        # Accumulate
        if current_official is not None:
            buffer.append(line)

    # Flush last buffer
    _flush()

    # Build the final document in strict order
    out_lines: list[str] = []
    for idx, official in enumerate(MANDATORY_SECTION_TITLES, start=1):
        section_body_lines = [l for l in collected.get(official, [])]
        if not section_body_lines:
            # If no content captured, skip empty section to avoid placeholders
            continue
        out_lines.append(f"## {idx}. {official}")
        # Trim leading/trailing blanks within section
        # and collapse excessive blank lines inside the section body
        prev_blank = True
        for l in section_body_lines:
            is_blank = not l.strip()
            if is_blank and prev_blank:
                continue
            out_lines.append(l)
            prev_blank = is_blank
        out_lines.append("")

    # Return formatted document (without leading/trailing newlines)
    return "\n".join([l.rstrip() for l in out_lines]).strip()



def iterative_generate_until_approved(
    sop_gen: AssistantAgent,
    critic: AssistantAgent,
    base_instruction_builder,
    max_iters: int = 5,
    logger: Callable[[str], None] | None = None,
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

    for iteration in range(1, max_iters + 1):
        _log(f"Итерация {iteration}: генерация...")
        try:
            gen_msgs = _run_agent_and_get_messages(
                sop_gen,
                base_instruction_builder(feedback),
            )
            raw_generated_content = "\n\n".join([m.content for m in gen_msgs if isinstance(m, TextMessage)])
            # Extract only the clean SOP content from generator
            clean_sop_content = _extract_clean_sop_content(raw_generated_content)
            # Enforce strict outline formatting (## N. Title)
            clean_sop_content = _enforce_strict_outline(clean_sop_content)
            _log(f"Генерация завершена. Длина: {len(clean_sop_content)} симв.")
        except Exception as e:
            _log(f"Ошибка генератора: {e}")
            break

        _log("Рецензирование критиком...")
        try:
            critic_prompt = f"""Оцени документ по протоколу (SUMMARY/ISSUES/STATUS).

ТЕКСТ СОП:
{clean_sop_content}
"""
            critic_msgs = _run_agent_and_get_messages(critic, critic_prompt)
            critic_texts = [m.content for m in critic_msgs if isinstance(m, TextMessage)]
            feedback = "\n\n".join(critic_texts)
            status_approved = any("STATUS:" in t and "APPROVED" in t for t in critic_texts)
            _log(f"Статус критика: {'APPROVED' if status_approved else 'REVISE'}")
        except Exception as e:
            _log(f"Ошибка критика: {e}")
            break

        if status_approved:
            _log("Документ одобрен критиком.")
            final_content = clean_sop_content
            return {"content": final_content, "approved": True, "feedback": feedback, "logs": logs}

        _log("Критик запросил правки. Повтор итерации.")

    return {"content": clean_sop_content, "approved": False, "feedback": feedback, "logs": logs} 