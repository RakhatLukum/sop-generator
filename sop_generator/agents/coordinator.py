from typing import Callable, Dict, Any, List
import asyncio
import os

from sop_generator.config.agent_config import AGENT_DEFAULTS, build_openai_chat_client
from sop_generator.config.prompts import COORDINATOR_SYSTEM_PROMPT
from sop_generator.utils.section_validator import SOPSectionValidator
from sop_generator.agents.base_imports import AssistantAgent, TextMessage, BaseChatMessage, RoundRobinGroupChat, MockResult


def build_coordinator(on_log: Callable[[str], None] | None = None) -> AssistantAgent:
    cfg = AGENT_DEFAULTS["coordinator"]["llm_config"]
    model_client = build_openai_chat_client(cfg)
    agent = AssistantAgent(
        name=AGENT_DEFAULTS["coordinator"]["name"],
        system_message=COORDINATOR_SYSTEM_PROMPT,
        model_client=model_client,
    )

    def log(msg: str) -> None:
        if on_log:
            on_log(msg)

    agent._on_log = log  # type: ignore[attr-defined]
    return agent


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


# Note: orchestrate_workflow is kept for potential UI logs, but the main generation uses single-agent calls

def orchestrate_workflow(
    coordinator: AssistantAgent,
    agents: List[AssistantAgent],
    instructions: str,
    max_rounds: int = 8,
) -> List[Dict[str, Any]]:
    team = RoundRobinGroupChat([coordinator, *agents])
    result = asyncio.run(team.run(task=instructions))
    ui_messages: List[Dict[str, Any]] = []
    for m in getattr(result, "messages", []):
        if isinstance(m, TextMessage):
            ui_messages.append({"sender": m.source, "content": m.content})
        elif isinstance(m, BaseChatMessage):
            ui_messages.append({"sender": getattr(m, "source", "unknown"), "content": getattr(m, "content", str(m))})
    return ui_messages


def _extract_clean_sop_content(raw_content: str) -> str:
    """Extract clean SOP content, removing agent conversation artifacts and duplications."""
    lines = raw_content.split('\n')
    clean_lines = []
    skip_sections = False
    seen_headers = set()
    
    for line in lines:
        line_lower = line.lower().strip()
        
        # Skip agent conversation artifacts
        if any(keyword in line_lower for keyword in [
            'summary:', 'issues:', 'status:', 'проблемы и предложения',
            'дополнительные рекомендации:', 'критик:', 'безопасность:',
            'контроль качества:', 'стилизация:', 'генератор:',
            'сгенерируй соп', 'разделы и режимы', 'требования:',
            'учти критику', 'оцени документ', 'текст:', 'замечания качества:',
            'создай профессиональный', 'обязательные требования', 'структура документа'
        ]):
            skip_sections = True
            continue
            
        # Resume when we hit actual content headers
        if line.strip().startswith('#') or (line.strip().startswith('**') and line.strip().endswith('**') and len(line.strip()) > 4):
            skip_sections = False
            
            # Check for duplicate headers
            header_text = line.strip().lower()
            if header_text in seen_headers:
                skip_sections = True
                continue
            else:
                seen_headers.add(header_text)
            
        # Skip empty lines when in skip mode
        if skip_sections and not line.strip():
            continue
            
        # Add line if not skipping or if it looks like real content
        if not skip_sections:
            clean_lines.append(line)
    
    # Post-processing: remove duplicate consecutive empty lines
    final_lines = []
    prev_empty = False
    
    for line in clean_lines:
        is_empty = not line.strip()
        if is_empty and prev_empty:
            continue
        final_lines.append(line)
        prev_empty = is_empty
    
    return '\n'.join(final_lines).strip()


def iterative_generate_until_approved(
    coordinator: AssistantAgent,  # Kept for compatibility
    sop_gen: AssistantAgent,
    safety: AssistantAgent,
    critic: AssistantAgent,
    quality: AssistantAgent,
    styler: AssistantAgent,
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
            _log(f"Генерация завершена. Длина: {len(clean_sop_content)} симв.")
        except Exception as e:
            _log(f"Ошибка генератора: {e}")
            break

        _log("Проверка безопасности...")
        safety_feedback = ""
        try:
            safety_msgs = _run_agent_and_get_messages(
                safety,
                f"Проверь раздел безопасности и предложи улучшения.\nТЕКСТ:\n{clean_sop_content}",
            )
            safety_feedback = "\n\n".join([m.content for m in safety_msgs if isinstance(m, TextMessage)])
            _log("Проверка безопасности завершена.")
        except Exception as e:
            _log(f"Ошибка агента безопасности: {e}")
            break

        _log("Проверка качества...")
        quality_feedback = ""
        try:
            quality_msgs = _run_agent_and_get_messages(
                quality,
                f"Проверь качество. Верни только список проблем и предложения.\nТЕКСТ:\n{clean_sop_content}",
            )
            quality_feedback = "\n\n".join([m.content for m in quality_msgs if isinstance(m, TextMessage)])
        except Exception as e:
            _log(f"Ошибка контроля качества: {e}")
            break

        _log("Валидация структуры документа...")
        validator = SOPSectionValidator()
        validation_results = validator.comprehensive_validation(clean_sop_content)
        
        validation_feedback = ""
        if not validation_results["overall_assessment"]["is_production_ready"]:
            recommendations = "\n".join(validation_results["recommendations"])
            missing_sections = ", ".join(validation_results["section_analysis"]["missing_sections"])
            
            validation_feedback = f"""
СТРУКТУРНЫЕ ПРОБЛЕМЫ:
- Отсутствующие разделы: {missing_sections}
- Общее качество: {validation_results["overall_assessment"]["quality_score"]:.1%}
- Рекомендации: {recommendations}

ТЕХНИЧЕСКАЯ ДЕТАЛИЗАЦИЯ: {'Недостаточно' if not validation_results["technical_analysis"]["has_sufficient_detail"] else 'Достаточно'}
ИНТЕГРАЦИЯ БЕЗОПАСНОСТИ: {'Недостаточно' if not validation_results["safety_analysis"]["has_integrated_safety"] else 'Достаточно'}
"""
            _log(f"Валидация: найдено {len(validation_results['section_analysis']['missing_sections'])} проблем")
        else:
            _log("Валидация: структура соответствует требованиям")

        _log("Рецензирование критиком...")
        try:
            critic_prompt = f"""Оцени документ по протоколу (SUMMARY/ISSUES/STATUS).

ТЕКСТ СОП:
{clean_sop_content}

ЗАМЕЧАНИЯ БЕЗОПАСНОСТИ:
{safety_feedback}

ЗАМЕЧАНИЯ КАЧЕСТВА:
{quality_feedback}

РЕЗУЛЬТАТЫ СТРУКТУРНОЙ ВАЛИДАЦИИ:
{validation_feedback}
"""
            critic_msgs = _run_agent_and_get_messages(critic, critic_prompt)
            critic_texts = [m.content for m in critic_msgs if isinstance(m, TextMessage)]
            feedback = "\n\n".join(critic_texts)
            status_approved = any("STATUS:" in t and "APPROVED" in t for t in critic_texts)
            
            # Override approval if structure validation failed
            if not validation_results["overall_assessment"]["is_production_ready"]:
                status_approved = False
                feedback += f"\n\nСТРУКТУРНАЯ ВАЛИДАЦИЯ: REVISE\n{validation_feedback}"
            
            _log(f"Статус критика: {'APPROVED' if status_approved else 'REVISE'}")
        except Exception as e:
            _log(f"Ошибка критика: {e}")
            break

        if status_approved:
            _log("Финальная стилизация...")
            try:
                styled_msgs = _run_agent_and_get_messages(
                    styler,
                    f"Приведи текст к корпоративному стилю. Верни ТОЛЬКО отформатированный СОП текст без комментариев.\nТЕКСТ:\n{clean_sop_content}",
                )
                styled_text = "\n\n".join([m.content for m in styled_msgs if isinstance(m, TextMessage)])
                # Clean the styled text too in case it contains artifacts
                final_content = _extract_clean_sop_content(styled_text) if styled_text else clean_sop_content
                _log("Стилизация завершена.")
            except Exception as e:
                _log(f"Ошибка стилизации: {e}")
                final_content = clean_sop_content
            return {"content": final_content, "approved": True, "feedback": feedback, "logs": logs}

        _log("Критик запросил правки. Повтор итерации.")

    return {"content": clean_sop_content, "approved": False, "feedback": feedback, "logs": logs} 