from sop_generator.config.agent_config import AGENT_DEFAULTS, build_openai_chat_client
from sop_generator.config.prompts import SAFETY_AGENT_SYSTEM_PROMPT
from sop_generator.agents.base_imports import AssistantAgent


def build_safety_agent() -> AssistantAgent:
    cfg = AGENT_DEFAULTS["safety_agent"]["llm_config"]
    model_client = build_openai_chat_client(cfg)
    return AssistantAgent(
        name=AGENT_DEFAULTS["safety_agent"]["name"],
        system_message=SAFETY_AGENT_SYSTEM_PROMPT,
        model_client=model_client,
    ) 