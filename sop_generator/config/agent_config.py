from __future__ import annotations

import asyncio
import json
import os
import re
import textwrap
from dataclasses import dataclass
from threading import Lock
from typing import Any, Callable, Dict, List, Optional

import requests
from requests import exceptions as requests_exceptions
from dotenv import load_dotenv

load_dotenv()

CUSTOM_LLM_BASE = "http://88.204.158.4:9100/v1"
CUSTOM_LLM_MODEL = "openai/gpt-oss-120b"

def _coerce_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _coerce_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default



def _describe_exception(exc: Exception) -> str:
    if isinstance(exc, requests_exceptions.RequestException):
        response = getattr(exc, "response", None)
        if response is not None:
            try:
                body = response.text
            except Exception:  # pragma: no cover
                body = "<unavailable>"
            snippet = (body or "").strip()
            if len(snippet) > 200:
                snippet = snippet[:200] + "…"
            status = getattr(response, "status_code", "?")
            return f"{exc.__class__.__name__} (status={status}): {snippet or str(exc)}"
        return f"{exc.__class__.__name__}: {exc}"
    return f"{exc.__class__.__name__}: {exc}"


@dataclass
class LLMConfig:
    model: str = os.getenv("CUSTOM_LLM_MODEL", CUSTOM_LLM_MODEL)
    base_url: str = os.getenv("CUSTOM_LLM_BASE", CUSTOM_LLM_BASE)
    temperature: float = _coerce_float(os.getenv("LLM_TEMPERATURE"), 0.3)
    max_tokens: int = _coerce_int(os.getenv("LLM_MAX_TOKENS"), 1000)
    timeout: int = _coerce_int(os.getenv("LLM_TIMEOUT"), 30)
    api_key: str = os.getenv("CUSTOM_LLM_API_KEY", "")

    def to_dict(self) -> Dict[str, Any]:
        cfg: Dict[str, Any] = {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "base_url": self.base_url,
            "api_key": self.api_key,
            "extra_headers": {"Content-Type": "application/json"},
        }
        if self.timeout > 0:
            cfg["request_timeout"] = self.timeout
        return cfg


DEFAULT_LLM = LLMConfig()


SOP_GENERATOR_SYSTEM_PROMPT = textwrap.dedent(
    """
    You are SOP_Generator, an expert technical writer who drafts detailed Standard Operating Procedures in Russian.
    Respond strictly in JSON using UTF-8 encoding. The top-level object must contain the keys:
      - "overall_summary": short paragraph summarizing the SOP (string)
      - "sections": list of objects each having keys "title" (string) and "content" (Markdown string)
    Do not include additional commentary or markdown outside of the JSON object. Maintain professional tone.
    """
).strip()


CRITIC_SYSTEM_PROMPT = textwrap.dedent(
    """
    You are Critic, a rigorous reviewer of SOP drafts. Analyse the provided SOP sections and decide if they satisfy the
    specification. Respond strictly in JSON with keys:
      - "approved": boolean (true if the draft fully meets requirements)
      - "feedback": concise Russian explanation of missing details or confirmation when approved
    When rejecting, provide actionable feedback. Avoid any text outside of the JSON object.
    """
).strip()


AGENT_DEFAULTS: Dict[str, Dict[str, Any]] = {
    "sop_generator": {
        "name": "SOP_Generator",
        "system_prompt": SOP_GENERATOR_SYSTEM_PROMPT,
        "llm_config": {**DEFAULT_LLM.to_dict(), "temperature": 0.3, "max_tokens": 2000},
    },
    "critic": {
        "name": "Critic",
        "system_prompt": CRITIC_SYSTEM_PROMPT,
        "llm_config": {**DEFAULT_LLM.to_dict(), "temperature": 0.2, "max_tokens": 800},
    },
}


def _extract_text_from_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: List[str] = []
        for item in content:
            if isinstance(item, dict):
                if item.get("type") == "text" and isinstance(item.get("text"), str):
                    parts.append(item["text"])
                elif isinstance(item.get("content"), str):
                    parts.append(item["content"])
                continue
            text = getattr(item, "text", None) or getattr(item, "content", None)
            if isinstance(text, str):
                parts.append(text)
        return "\n".join([p for p in parts if p])
    return str(content)


def _normalize_messages(messages_input: Any) -> List[Dict[str, str]]:
    normalized: List[Dict[str, str]] = []
    if isinstance(messages_input, list):
        for message in messages_input:
            if isinstance(message, dict):
                role = message.get("role", "user")
                content = _extract_text_from_content(message.get("content", ""))
                normalized.append({"role": role, "content": content})
                continue
            role = getattr(message, "role", None)
            if not role:
                cls_name = message.__class__.__name__.lower()
                if "system" in cls_name:
                    role = "system"
                elif "assistant" in cls_name:
                    role = "assistant"
                else:
                    role = "user"
            content = _extract_text_from_content(getattr(message, "content", ""))
            normalized.append({"role": role, "content": content})
    else:
        normalized.append({"role": "user", "content": _extract_text_from_content(messages_input)})
    return normalized


class _ChatMessage:
    def __init__(self, content: str):
        self.content = content


class _ChatChoice:
    def __init__(self, content: str):
        self.message = _ChatMessage(content)


class _ChatCompletion:
    def __init__(self, content: str):
        self.choices = [_ChatChoice(content)]


class NoAuthChatClient:
    def __init__(self, config: Dict[str, Any]):
        self.config = dict(config)
        base_url = (self.config.get("base_url") or CUSTOM_LLM_BASE).rstrip("/")
        if base_url.endswith("/chat/completions"):
            self._endpoint = base_url
        elif base_url.endswith("/v1"):
            self._endpoint = f"{base_url}/chat/completions"
        else:
            self._endpoint = f"{base_url}/v1/chat/completions"
        self._model = self.config.get("model") or CUSTOM_LLM_MODEL
        self._timeout = _coerce_int(self.config.get("request_timeout"), DEFAULT_LLM.timeout)
        if self._timeout <= 0:
            self._timeout = DEFAULT_LLM.timeout

        self._headers: Dict[str, str] = {"Content-Type": "application/json"}
        self._headers.update(self.config.get("extra_headers") or {})
        api_key = (self.config.get("api_key") or "").strip()
        if api_key:
            self._headers["Authorization"] = f"Bearer {api_key}"

        self._model_info = {
            "vision": False,
            "function_calling": False,
            "json_output": False,
            "structured_output": False,
            "multiple_system_messages": True,
            "family": "openai-compatible",
        }

        self._verified = False
        self._verify_lock = Lock()
        self._last_usage: Dict[str, int] = {}
        self._verify_connection(initial=True)

    @property
    def model_info(self) -> Dict[str, Any]:
        return self._model_info

    @property
    def last_usage(self) -> Dict[str, int]:
        return dict(self._last_usage)

    def _post(self, payload: Dict[str, Any], timeout: int | None = None) -> Dict[str, Any]:
        response = requests.post(
            self._endpoint,
            headers=self._headers,
            json=payload,
            timeout=timeout or self._timeout,
        )
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise ValueError("Unexpected response format from LLM")
        return data

    @staticmethod
    def _extract_content_from_response(
        data: Dict[str, Any], *, require_content: bool = True
    ) -> str:
        choices = data.get("choices")
        if not isinstance(choices, list) or not choices:
            raise ValueError("LLM response does not contain choices")
        first_choice = choices[0]
        if isinstance(first_choice, dict):
            message = first_choice.get("message")
            if isinstance(message, dict):
                content = message.get("content")
                if isinstance(content, str) and content.strip():
                    return content
                if isinstance(content, list):
                    text = _extract_text_from_content(content)
                    if text.strip():
                        return text
                    if not require_content:
                        return text
                if content in {"", None} and not require_content:
                    return content or ""
                reasoning = message.get("reasoning_content")
                if isinstance(reasoning, str) and reasoning.strip():
                    return reasoning
                if isinstance(reasoning, list):
                    text = _extract_text_from_content(reasoning)
                    if text.strip():
                        return text
                    if not require_content:
                        return text
            text_entry = first_choice.get("text")
            if isinstance(text_entry, str) and text_entry.strip():
                return text_entry
            if isinstance(text_entry, list):
                text = _extract_text_from_content(text_entry)
                if text.strip():
                    return text
                if not require_content:
                    return text
            direct_content = first_choice.get("content")
            if isinstance(direct_content, str) and direct_content.strip():
                return direct_content
            if isinstance(direct_content, list):
                text = _extract_text_from_content(direct_content)
                if text.strip():
                    return text
                if not require_content:
                    return text
            delta = first_choice.get("delta")
            if isinstance(delta, dict):
                delta_content = delta.get("content")
                if isinstance(delta_content, str) and delta_content.strip():
                    return delta_content
                if isinstance(delta_content, list):
                    text = _extract_text_from_content(delta_content)
                    if text.strip():
                        return text
                    if not require_content:
                        return text
        import json as _json
        if isinstance(first_choice, dict):
            try:
                snippet = _json.dumps(first_choice, ensure_ascii=False)[:400]
            except Exception:
                snippet = str(first_choice)[:400]
        else:
            snippet = str(first_choice)[:400]
        raise ValueError(
            f"LLM response is missing text content (choice keys: {list(first_choice.keys()) if isinstance(first_choice, dict) else type(first_choice).__name__}) snippet={snippet}"
        )

    def _verify_connection(self, initial: bool = False) -> None:
        if self._verified:
            return
        with self._verify_lock:
            if self._verified:
                return
            payload = {
                "model": self._model,
                "messages": [
                    {"role": "system", "content": "Reply with the single word 'pong'."},
                    {"role": "user", "content": "ping"},
                ],
                "temperature": 0.0,
                "max_tokens": 5,
                "stream": False,
            }
            try:
                data = self._post(payload)
                _ = self._extract_content_from_response(data, require_content=False)
                self._verified = True
            except Exception as exc:
                stage = "initial" if initial else "runtime"
                reason = _describe_exception(exc)
                raise RuntimeError(
                    f"Failed to reach LLM at {self._endpoint} during {stage} connectivity check: {reason}"
                ) from exc

    def complete(self, messages: Any, **kwargs: Any) -> str:
        normalized_messages = _normalize_messages(messages)
        self._verify_connection()

        payload = {
            "model": self._model,
            "messages": normalized_messages,
            "temperature": kwargs.get("temperature", self.config.get("temperature", DEFAULT_LLM.temperature)),
            "max_tokens": kwargs.get("max_tokens", self.config.get("max_tokens", DEFAULT_LLM.max_tokens)),
            "stream": False,
        }
        payload.update({k: v for k, v in kwargs.items() if k in {"stop", "frequency_penalty", "presence_penalty"}})

        try:
            data = self._post(payload, timeout=kwargs.get("timeout"))
            self._last_usage = _normalize_usage(data.get("usage"))
            return self._extract_content_from_response(data)
        except Exception as exc:
            reason = _describe_exception(exc)
            raise RuntimeError(f"LLM request failed: {reason}") from exc

    async def create(self, messages: Any, **kwargs: Any) -> _ChatCompletion:
        normalized_messages = _normalize_messages(messages)
        await asyncio.to_thread(self._verify_connection)

        payload = {
            "model": self._model,
            "messages": normalized_messages,
            "temperature": kwargs.get("temperature", self.config.get("temperature", DEFAULT_LLM.temperature)),
            "max_tokens": kwargs.get("max_tokens", self.config.get("max_tokens", DEFAULT_LLM.max_tokens)),
            "stream": False,
        }
        try:
            data = await asyncio.to_thread(self._post, payload)
            self._last_usage = _normalize_usage(data.get("usage"))
            content = self._extract_content_from_response(data)
        except Exception as exc:
            reason = _describe_exception(exc)
            raise RuntimeError(f"LLM request failed: {reason}") from exc
        return _ChatCompletion(content)


@dataclass
class GenerationResult:
    content: str
    sections: List[Dict[str, str]]
    raw_output: str
    overall_summary: str = ""
    usage: Optional[Dict[str, int]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "sections": self.sections,
            "raw_output": self.raw_output,
            "overall_summary": self.overall_summary,
            "usage": dict(self.usage or {}),
        }


@dataclass
class CriticResult:
    approved: bool
    feedback: str
    usage: Optional[Dict[str, int]] = None


def _parse_json_payload(text: str) -> Optional[Any]:
    if not text:
        return None
    stripped = text.strip()
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", stripped, flags=re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                return None
    return None


def _normalize_usage(raw_usage: Any) -> Dict[str, int]:
    if not isinstance(raw_usage, dict):
        return {}
    usage: Dict[str, int] = {}
    for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
        value = raw_usage.get(key)
        if isinstance(value, (int, float)):
            usage[key] = int(value)
    if "total_tokens" not in usage and usage:
        usage["total_tokens"] = usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0)
    return usage


def _accumulate_usage(target: Dict[str, int], usage: Optional[Dict[str, int]]) -> None:
    if not usage:
        return
    for key, value in usage.items():
        if isinstance(value, (int, float)):
            target[key] = target.get(key, 0) + int(value)


def _format_usage_for_log(usage: Dict[str, int]) -> str:
    parts: List[str] = []
    labels = {
        "prompt_tokens": "prompt",
        "completion_tokens": "completion",
        "total_tokens": "total",
    }
    for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
        if usage.get(key) is not None:
            parts.append(f"{labels[key]}={usage.get(key, 0)}")
    return ", ".join(parts) if parts else "нет данных"


def _sections_to_markdown(sections: List[Dict[str, str]]) -> str:
    lines: List[str] = []
    for idx, sec in enumerate(sections, start=1):
        raw_title = sec.get("title")
        title = (raw_title or "").strip()
        content = (sec.get("content") or "").strip()
        if title:
            block = f"## {idx}. {title}\n\n{content}".strip()
        else:
            block = content
        if block:
            lines.append(block)
    return "\n\n".join(lines)


def _summarize_generation_for_memory(result: "GenerationResult", *, max_chars: int = 800) -> str:
    """Build a compact summary of sections for memory prompts."""
    lines: List[str] = []
    for idx, section in enumerate(result.sections, start=1):
        title = section.get("title") or f"Раздел {idx}"
        content = (section.get("content") or "").strip().replace("\n", " ")
        if len(content) > 160:
            content = content[:157].rstrip() + "…"
        lines.append(f"{idx}. {title}: {content}")
        if sum(len(line) for line in lines) > max_chars:
            break
    summary = "\n".join(lines)
    if len(summary) > max_chars:
        summary = summary[:max_chars].rstrip() + "…"
    return summary or "(пусто)"


class SOPGeneratorAgent:
    def __init__(self, *, name: str, system_prompt: str, llm_config: Dict[str, Any]):
        self.name = name
        self.system_prompt = system_prompt
        self.llm_config = {**llm_config}
        self._client = build_openai_chat_client(self.llm_config)

    def generate(
        self,
        *,
        instruction: str,
        sections: List[Dict[str, Any]],
        meta: Optional[Dict[str, Any]] = None,
        corpus_summary: Optional[str] = None,
        section_summaries: Optional[Dict[int, str]] = None,
        history: Optional[List["GenerationResult"]] = None,
        feedback_history: Optional[List[str]] = None,
    ) -> GenerationResult:
        prompt_parts = [instruction.strip()]
        if corpus_summary:
            prompt_parts.append("\nКраткое содержание загруженных документов:\n" + corpus_summary.strip())
        if section_summaries:
            per_section_lines: List[str] = ["\nДополнительные материалы по разделам:"]
            for idx, summary in section_summaries.items():
                per_section_lines.append(f"Раздел {idx}: {summary.strip()}")
            prompt_parts.append("\n".join(per_section_lines))
        if meta:
            meta_lines = ["\nМетаданные СОП:"]
            if meta.get("title"):
                meta_lines.append(f"Название: {meta['title']}")
            if meta.get("number"):
                meta_lines.append(f"Номер: {meta['number']}")
            if meta.get("equipment"):
                meta_lines.append(f"Оборудование: {meta['equipment']}")
            prompt_parts.append("\n".join(meta_lines))

        # Include memory from previous drafts and critiques to discourage repeated mistakes.
        effective_history = (history or [])[-3:]
        if effective_history:
            memory_lines: List[str] = ["\nПредыдущие черновики (учти ошибки):"]
            for idx, attempt in enumerate(effective_history, start=1):
                summary = _summarize_generation_for_memory(attempt, max_chars=600)
                memory_lines.append(f"Черновик {idx}:\n{summary}")
            prompt_parts.append("\n".join(memory_lines))

        effective_feedback = (feedback_history or [])[-3:]
        if effective_feedback:
            fb_lines: List[str] = ["\nПредыдущие комментарии критика (исправь их):"]
            for idx, fb in enumerate(effective_feedback, start=1):
                trimmed = fb.strip()
                if len(trimmed) > 400:
                    trimmed = trimmed[:397].rstrip() + "…"
                fb_lines.append(f"Комментарий {idx}: {trimmed}")
            prompt_parts.append("\n".join(fb_lines))

        user_prompt = "\n\n".join(part for part in prompt_parts if part).strip()
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        raw_output = self._client.complete(
            messages,
            temperature=self.llm_config.get("temperature", DEFAULT_LLM.temperature),
            max_tokens=self.llm_config.get("max_tokens", DEFAULT_LLM.max_tokens),
        )

        parsed = _parse_json_payload(raw_output)
        overall_summary = ""
        section_payload: List[Dict[str, str]] = []
        usage = self._client.last_usage
        if isinstance(parsed, dict):
            overall_summary = str(parsed.get("overall_summary", "")).strip()
            raw_sections = parsed.get("sections")
            if isinstance(raw_sections, list):
                for idx, sec in enumerate(raw_sections, start=1):
                    if isinstance(sec, dict):
                        title = str(sec.get("title") or f"Раздел {idx}").strip()
                        content = str(sec.get("content") or "").strip()
                        section_payload.append({
                            "title": title or f"Раздел {idx}",
                            "content": content,
                        })

            # Some misaligned models mirror the critic schema; salvage useful text when possible.
            if not section_payload:
                for fallback_key in ("feedback", "content", "body", "text", "document"):
                    alt_text = parsed.get(fallback_key)
                    if isinstance(alt_text, str) and alt_text.strip():
                        section_payload.append({"title": "", "content": alt_text.strip()})
                        break

            # Handle a single blob of text stored under overall_summary when sections missing
            if not section_payload and overall_summary:
                section_payload.append({"title": "", "content": overall_summary})

        if not section_payload:
            fallback_titles = [s.get("title") for s in sections if isinstance(s, dict) and s.get("title")]
            fallback_text = raw_output.strip()
            if fallback_titles:
                section_payload = [{"title": str(title), "content": fallback_text} for title in fallback_titles]
            else:
                section_payload = [{"title": "", "content": fallback_text}]

        content_body = _sections_to_markdown(section_payload)
        return GenerationResult(
            content=content_body,
            sections=section_payload,
            raw_output=raw_output,
            overall_summary=overall_summary,
            usage=usage,
        )


class CriticAgent:
    def __init__(self, *, name: str, system_prompt: str, llm_config: Dict[str, Any]):
        self.name = name
        self.system_prompt = system_prompt
        self.llm_config = {**llm_config}
        self._client = build_openai_chat_client(self.llm_config)

    def review(
        self,
        *,
        generation: GenerationResult,
        instruction: str,
        sections: List[Dict[str, Any]],
        meta: Optional[Dict[str, Any]] = None,
        history: Optional[List[GenerationResult]] = None,
        feedback_history: Optional[List[str]] = None,
    ) -> CriticResult:
        spec_lines: List[str] = ["Требования к документу:", instruction.strip()]
        if meta:
            meta_lines = ["\nМетаданные:"]
            if meta.get("title"):
                meta_lines.append(f"Название: {meta['title']}")
            if meta.get("number"):
                meta_lines.append(f"Номер: {meta['number']}")
            if meta.get("equipment"):
                meta_lines.append(f"Оборудование: {meta['equipment']}")
            spec_lines.extend(meta_lines)

        structure_lines: List[str] = ["\nОжидаемая структура:"]
        for idx, sec in enumerate(sections, start=1):
            title = sec.get("title") or f"Раздел {idx}"
            mode = sec.get("mode", "ai")
            prompt_hint = sec.get("prompt") or ""
            descriptor = f"{idx}. {title} (режим: {mode})"
            if prompt_hint:
                descriptor += f" — подсказка: {prompt_hint}"
            structure_lines.append(descriptor)

        review_payload = {
            "overall_summary": generation.overall_summary,
            "sections": generation.sections,
        }
        review_json = json.dumps(review_payload, ensure_ascii=False, indent=2)

        effective_history = (history or [])[-3:]
        if effective_history:
            history_lines: List[str] = ["\nИстория предыдущих черновиков (последи повторяющиеся ошибки):"]
            for idx, attempt in enumerate(effective_history, start=1):
                summary = _summarize_generation_for_memory(attempt, max_chars=400)
                history_lines.append(f"{idx}. {summary}")
            spec_lines.extend(history_lines)

        effective_feedback = (feedback_history or [])[-3:]
        if effective_feedback:
            fb_lines: List[str] = ["\nПредыдущие выводы критика:"]
            for idx, fb in enumerate(effective_feedback, start=1):
                trimmed = fb.strip()
                if len(trimmed) > 300:
                    trimmed = trimmed[:297].rstrip() + "…"
                fb_lines.append(f"{idx}. {trimmed}")
            spec_lines.extend(fb_lines)

        user_prompt = "\n".join(
            spec_lines
            + structure_lines
            + ["\nСгенерированная версия (JSON):", review_json, "Проверь соответствие требованиям."]
        )

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_prompt.strip()},
        ]

        raw_output = self._client.complete(
            messages,
            temperature=self.llm_config.get("temperature", DEFAULT_LLM.temperature),
            max_tokens=self.llm_config.get("max_tokens", DEFAULT_LLM.max_tokens),
        )

        parsed = _parse_json_payload(raw_output)
        approved = False
        feedback = raw_output.strip()
        usage = self._client.last_usage
        if isinstance(parsed, dict):
            approved_val = parsed.get("approved")
            if isinstance(approved_val, bool):
                approved = approved_val
            elif isinstance(approved_val, str):
                approved = approved_val.lower() in {"true", "yes", "да", "approved"}
            fb = parsed.get("feedback")
            if isinstance(fb, str) and fb.strip():
                feedback = fb.strip()

        return CriticResult(approved=approved, feedback=feedback, usage=usage)


def build_sop_generator() -> SOPGeneratorAgent:
    cfg = AGENT_DEFAULTS["sop_generator"]
    return SOPGeneratorAgent(
        name=cfg["name"],
        system_prompt=cfg["system_prompt"],
        llm_config=cfg["llm_config"],
    )


def build_critic() -> CriticAgent:
    cfg = AGENT_DEFAULTS["critic"]
    return CriticAgent(
        name=cfg["name"],
        system_prompt=cfg["system_prompt"],
        llm_config=cfg["llm_config"],
    )


def build_generation_instruction(
    *,
    sop_title: str = "",
    sop_number: str = "",
    equipment_type: str = "",
    sections: Optional[List[Dict[str, Any]]] = None,
    parsed_corpus_summary: Optional[str] = None,
    critique_feedback: Optional[str] = None,
) -> str:
    sections = sections or []

    lines: List[str] = ["Сформируй проект стандартной операционной процедуры (СОП) на русском языке."]

    if sop_title or sop_number or equipment_type:
        lines.append("\nИсходные данные:")
        if sop_title:
            lines.append(f"Название: {sop_title}")
        if sop_number:
            lines.append(f"Номер: {sop_number}")
        if equipment_type:
            lines.append(f"Оборудование/процесс: {equipment_type}")

    if sections:
        lines.append("\nНеобходимые разделы:")
        for idx, section in enumerate(sections, start=1):
            title = section.get("title") or f"Раздел {idx}"
            mode = section.get("mode", "ai")
            prompt_hint = section.get("prompt") or ""
            descriptor = f"{idx}. {title} (режим: {mode})"
            if prompt_hint:
                descriptor += f" — подсказка: {prompt_hint}"
            lines.append(descriptor)

    if parsed_corpus_summary:
        lines.append("\nКраткое содержание справочных документов:")
        lines.append(parsed_corpus_summary.strip())

    if critique_feedback:
        lines.append("\nКомментарии критика с предыдущей итерации (учти их):")
        lines.append(critique_feedback.strip())

    lines.extend([
        "\nПодготовь содержательный текст каждого раздела, используй Markdown для структурирования.",
        "Ответ верни строго в формате JSON, как указано в системной подсказке.",
    ])

    return "\n".join(lines).strip()


def summarize_parsed_chunks(chunks: List[Dict[str, Any]], *, max_length: int = 1200) -> str:
    collected: List[str] = []
    for chunk in chunks or []:
        if not isinstance(chunk, dict):
            continue
        text = chunk.get("content")
        if not text:
            continue
        snippet = str(text).strip()
        if not snippet:
            continue
        collected.append(snippet)
        if sum(len(part) for part in collected) >= max_length * 1.5:
            break

    if not collected:
        return ""

    merged = "\n".join(collected)
    if len(merged) <= max_length:
        return merged

    truncated = merged[:max_length]
    last_sentence_end = max(truncated.rfind("."), truncated.rfind("!"), truncated.rfind("?"))
    if last_sentence_end > max_length * 0.6:
        truncated = truncated[: last_sentence_end + 1]
    return truncated.rstrip() + "…"


def iterative_generate_until_approved(
    *,
    sop_gen: SOPGeneratorAgent,
    critic: CriticAgent,
    base_instruction_builder: Callable[[str], str],
    sections: List[Dict[str, Any]],
    max_iters: int = 5,
    enforce_mandatory_sections: bool = False,
    logger: Optional[Callable[[str], None]] = None,
    auto_backfill_meta: Optional[Dict[str, Any]] = None,
    auto_backfill_summary: Optional[str] = None,
    section_summaries: Optional[Dict[int, str]] = None,
) -> Dict[str, Any]:
    _ = enforce_mandatory_sections
    history: List[str] = []
    critique: str = ""
    last_result: Optional[GenerationResult] = None
    total_usage: Dict[str, int] = {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
    }
    attempt_history: List[GenerationResult] = []
    feedback_history: List[str] = []

    def _log(message: str) -> None:
        history.append(message)
        if logger:
            logger(message)
        else:
            pass

    for iteration in range(1, max_iters + 1):
        instruction = base_instruction_builder(critique)
        generation = sop_gen.generate(
            instruction=instruction,
            sections=sections,
            meta=auto_backfill_meta,
            corpus_summary=auto_backfill_summary,
            section_summaries=section_summaries,
            history=attempt_history,
            feedback_history=feedback_history,
        )
        last_result = generation
        _log(f"Итерация {iteration}: сгенерировано {len(generation.content)} символов текста.")
        _accumulate_usage(total_usage, generation.usage)
        attempt_history.append(generation)
        if len(attempt_history) > 5:
            del attempt_history[:-5]

        critic_result = critic.review(
            generation=generation,
            instruction=instruction,
            sections=sections,
            meta=auto_backfill_meta,
            history=attempt_history,
            feedback_history=feedback_history,
        )
        _log(
            f"Итерация {iteration}: критик {'одобрил' if critic_result.approved else 'не одобрил'} черновик."
        )
        _accumulate_usage(total_usage, critic_result.usage)

        if critic_result.approved:
            usage_message = _format_usage_for_log(total_usage)
            _log(f"Суммарный расход токенов: {usage_message}")
            result = generation.to_dict()
            result.update({"approved": True, "logs": history, "token_usage": dict(total_usage)})
            return result

        critique = critic_result.feedback
        _log(f"Комментарий критика: {critique}")
        feedback_history.append(critique)
        if len(feedback_history) > 5:
            del feedback_history[:-5]

    if not last_result:
        usage_message = _format_usage_for_log(total_usage)
        _log(f"Суммарный расход токенов: {usage_message}")
        return {
            "approved": False,
            "content": "",
            "sections": [],
            "logs": history,
            "token_usage": dict(total_usage),
        }

    result = last_result.to_dict()
    result.update({"approved": False, "logs": history, "token_usage": dict(total_usage)})
    usage_message = _format_usage_for_log(total_usage)
    _log(f"Суммарный расход токенов: {usage_message}")
    return result


def build_openai_chat_client(cfg: Dict[str, Any]) -> NoAuthChatClient:
    merged_cfg = {**DEFAULT_LLM.to_dict(), **(cfg or {})}
    return NoAuthChatClient(merged_cfg)


__all__ = [
    "LLMConfig",
    "DEFAULT_LLM",
    "AGENT_DEFAULTS",
    "build_openai_chat_client",
    "build_sop_generator",
    "build_critic",
    "build_generation_instruction",
    "summarize_parsed_chunks",
    "iterative_generate_until_approved",
    "CUSTOM_LLM_BASE",
    "CUSTOM_LLM_MODEL",
]
