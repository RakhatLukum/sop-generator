from typing import Callable, Dict, Any, List
import asyncio
import os
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import TextMessage, BaseChatMessage
from autogen_agentchat.teams import RoundRobinGroupChat

from config.agent_config import AGENT_DEFAULTS, build_openai_chat_client
from config.prompts import COORDINATOR_SYSTEM_PROMPT


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

def _run_agent_and_get_messages(agent: AssistantAgent, task: str, timeout_s: int | None = None) -> List[BaseChatMessage]:
    timeout = timeout_s or int(os.getenv("LLM_TIMEOUT", "90"))

    async def _runner():
        return await agent.run(task=task)

    try:
        result = asyncio.run(asyncio.wait_for(_runner(), timeout=timeout))
    except asyncio.TimeoutError:
        raise TimeoutError(f"LLM timed out after {timeout}s")
    return list(getattr(result, "messages", []) or [])


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


def iterative_generate_until_approved(
    coordinator: AssistantAgent,
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
    content: str = ""
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
            content = "\n\n".join([m.content for m in gen_msgs if isinstance(m, TextMessage)])
            _log(f"Генерация завершена. Длина: {len(content)} симв.")
        except Exception as e:
            _log(f"Ошибка генератора: {e}")
            break

        _log("Проверка безопасности...")
        try:
            safety_msgs = _run_agent_and_get_messages(
                safety,
                f"Проверь раздел безопасности и добавь недостающее.\nТЕКСТ:\n{content}",
            )
            safety_text = "\n\n".join([m.content for m in safety_msgs if isinstance(m, TextMessage)])
            content = content + "\n\n" + safety_text
            _log("Безопасность обновлена.")
        except Exception as e:
            _log(f"Ошибка агента безопасности: {e}")
            break

        _log("Проверка качества...")
        try:
            quality_msgs = _run_agent_and_get_messages(
                quality,
                f"Проверь качество. Верни только список проблем и предложения.\nТЕКСТ:\n{content}",
            )
            quality_text = "\n\n".join([m.content for m in quality_msgs if isinstance(m, TextMessage)])
        except Exception as e:
            _log(f"Ошибка контроля качества: {e}")
            break

        _log("Рецензирование критиком...")
        try:
            critic_msgs = _run_agent_and_get_messages(
                critic,
                f"Оцени документ по протоколу (SUMMARY/ISSUES/STATUS).\nТЕКСТ:\n{content}\n\nДОП. ЗАМЕЧАНИЯ КАЧЕСТВА:\n{quality_text}",
            )
            critic_texts = [m.content for m in critic_msgs if isinstance(m, TextMessage)]
            feedback = "\n\n".join(critic_texts)
            status_approved = any("STATUS:" in t and "APPROVED" in t for t in critic_texts)
            _log(f"Статус критика: {'APPROVED' if status_approved else 'REVISE'}")
        except Exception as e:
            _log(f"Ошибка критика: {e}")
            break

        if status_approved:
            _log("Финальная стилизация...")
            try:
                styled_msgs = _run_agent_and_get_messages(
                    styler,
                    f"Приведи текст к корпоративному стилю.\nТЕКСТ:\n{content}",
                )
                styled_text = "\n\n".join([m.content for m in styled_msgs if isinstance(m, TextMessage)])
                content = styled_text or content
                _log("Стилизация завершена.")
            except Exception as e:
                _log(f"Ошибка стилизации: {e}")
            return {"content": content, "approved": True, "feedback": feedback, "logs": logs}

        _log("Критик запросил правки. Повтор итерации.")

    return {"content": content, "approved": False, "feedback": feedback, "logs": logs} 