# Shared import handling for all agent modules
"""
This module handles the import of autogen components with fallbacks for deployment.
All agent modules should import from this module to ensure consistent behavior.
"""

import os
from typing import Any, List

# Prefer simple local agent implementation by default to avoid strict client interfaces
USE_SIMPLE_AGENT = os.getenv("USE_SIMPLE_AGENT", "true").lower() in {"1", "true", "yes", "on"}

AUTOGEN_AVAILABLE = False

# Try to import autogen components only if explicitly requested
if not USE_SIMPLE_AGENT:
    try:
        from autogen_agentchat.agents import AssistantAgent as _AG_AssistantAgent  # type: ignore
        from autogen_agentchat.messages import TextMessage as _AG_TextMessage, BaseChatMessage as _AG_BaseChatMessage  # type: ignore
        from autogen_agentchat.teams import RoundRobinGroupChat as _AG_RoundRobinGroupChat  # type: ignore
        AUTOGEN_AVAILABLE = True
        AssistantAgent = _AG_AssistantAgent  # type: ignore
        TextMessage = _AG_TextMessage  # type: ignore
        BaseChatMessage = _AG_BaseChatMessage  # type: ignore
        RoundRobinGroupChat = _AG_RoundRobinGroupChat  # type: ignore
    except ImportError:
        try:
            from autogen.agentchat.agents import AssistantAgent as _AG_AssistantAgent  # type: ignore
            from autogen.agentchat.messages import TextMessage as _AG_TextMessage, BaseChatMessage as _AG_BaseChatMessage  # type: ignore
            from autogen.agentchat.teams import RoundRobinGroupChat as _AG_RoundRobinGroupChat  # type: ignore
            AUTOGEN_AVAILABLE = True
            AssistantAgent = _AG_AssistantAgent  # type: ignore
            TextMessage = _AG_TextMessage  # type: ignore
            BaseChatMessage = _AG_BaseChatMessage  # type: ignore
            RoundRobinGroupChat = _AG_RoundRobinGroupChat  # type: ignore
        except ImportError:
            try:
                # Legacy top-level import sometimes only exposes AssistantAgent
                from autogen import AssistantAgent as _AG_AssistantAgent  # type: ignore
                AUTOGEN_AVAILABLE = True
                AssistantAgent = _AG_AssistantAgent  # type: ignore
                # Provide shims for message and team types to satisfy imports
                class TextMessage:  # type: ignore
                    def __init__(self, source: str, content: str):
                        self.source = source
                        self.content = content
                class BaseChatMessage:  # type: ignore
                    def __init__(self, source: str, content: str):
                        self.source = source
                        self.content = content
                class RoundRobinGroupChat:  # type: ignore
                    def __init__(self, agents: List[Any]):
                        self.agents = agents
                    async def run(self, task: str):  # pragma: no cover - placeholder
                        return MockResult([])
            except ImportError:
                AUTOGEN_AVAILABLE = False


class MockResult:
    def __init__(self, messages: List[Any]):
        self.messages = messages


# If autogen unavailable or disabled, define simple local agents
if not AUTOGEN_AVAILABLE:
    class TextMessage:  # type: ignore
        def __init__(self, source: str, content: str):
            self.source = source
            self.content = content

    class BaseChatMessage:  # type: ignore
        def __init__(self, source: str, content: str):
            self.source = source
            self.content = content

    class AssistantAgent:  # type: ignore
        def __init__(self, name: str, system_message: str, model_client: Any):
            self.name = name
            self.system_message = system_message
            self.model_client = model_client

        async def generate_reply(self, messages: Any) -> str:
            try:
                # Build OpenAI-style messages
                full_messages: list[dict] = [{"role": "system", "content": self.system_message}]
                if isinstance(messages, str):
                    full_messages.append({"role": "user", "content": messages})
                elif isinstance(messages, list):
                    # Best-effort normalization: accept list of dicts or objects with .content
                    for m in messages:
                        if isinstance(m, dict):
                            role = m.get("role", "user")
                            content = m.get("content", "")
                            full_messages.append({"role": role, "content": content})
                        else:
                            content = getattr(m, "content", str(m))
                            full_messages.append({"role": "user", "content": content})
                else:
                    full_messages.append({"role": "user", "content": str(messages)})

                response = await self.model_client.create(full_messages)
                # Normalize typical response shapes
                if hasattr(response, "choices") and response.choices:
                    choice0 = response.choices[0]
                    message_obj = getattr(choice0, "message", None)
                    if message_obj is not None and hasattr(message_obj, "content"):
                        return message_obj.content or ""
                # Fallbacks for custom mocks
                content = getattr(response, "content", None)
                if isinstance(content, str):
                    return content
                return ""
            except Exception as e:  # pragma: no cover - runtime guard
                print(f"AssistantAgent.generate_reply error: {e}")
                return f"Error generating reply: {e}"

        async def run(self, task: str) -> MockResult:
            try:
                reply = await self.generate_reply(task)
                return MockResult([TextMessage(self.name, reply)])
            except Exception as e:  # pragma: no cover - runtime guard
                print(f"AssistantAgent.run error: {e}")
                return MockResult([TextMessage(self.name, f"Error: {e}")])

    class RoundRobinGroupChat:  # type: ignore
        def __init__(self, agents: List[Any]):
            self.agents = agents
        async def run(self, task: str) -> MockResult:  # pragma: no cover - placeholder
            return MockResult([])


__all__ = [
    "AssistantAgent",
    "TextMessage",
    "BaseChatMessage",
    "RoundRobinGroupChat",
    "MockResult",
    "AUTOGEN_AVAILABLE",
]