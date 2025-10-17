from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from threading import Lock
from typing import Any, Dict, List

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


AGENT_DEFAULTS: Dict[str, Dict[str, Any]] = {
    "coordinator": {
        "name": "Coordinator",
        "llm_config": {**DEFAULT_LLM.to_dict(), "max_tokens": 500},
    },
    "sop_generator": {
        "name": "SOP_Generator",
        "llm_config": {**DEFAULT_LLM.to_dict(), "temperature": 0.3, "max_tokens": 2000},
    },
    "document_parser": {
        "name": "Document_Parser",
        "llm_config": {**DEFAULT_LLM.to_dict(), "temperature": 0.2, "max_tokens": 800},
    },
    "critic": {
        "name": "Critic",
        "llm_config": {**DEFAULT_LLM.to_dict(), "temperature": 0.2, "max_tokens": 500},
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
        self._verify_connection(initial=True)

    @property
    def model_info(self) -> Dict[str, Any]:
        return self._model_info

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
            content = self._extract_content_from_response(data)
        except Exception as exc:
            reason = _describe_exception(exc)
            raise RuntimeError(f"LLM request failed: {reason}") from exc
        return _ChatCompletion(content)


def build_openai_chat_client(cfg: Dict[str, Any]) -> NoAuthChatClient:
    merged_cfg = {**DEFAULT_LLM.to_dict(), **(cfg or {})}
    return NoAuthChatClient(merged_cfg)


__all__ = [
    "LLMConfig",
    "DEFAULT_LLM",
    "AGENT_DEFAULTS",
    "build_openai_chat_client",
    "CUSTOM_LLM_BASE",
    "CUSTOM_LLM_MODEL",
]
