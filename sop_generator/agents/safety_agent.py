from autogen_agentchat.agents import AssistantAgent
from config.agent_config import AGENT_DEFAULTS, build_openai_chat_client
from config.prompts import SAFETY_AGENT_SYSTEM_PROMPT


def build_safety_agent() -> AssistantAgent:
    cfg = AGENT_DEFAULTS["safety_agent"]["llm_config"]
    model_client = build_openai_chat_client(cfg)
    return AssistantAgent(
        name=AGENT_DEFAULTS["safety_agent"]["name"],
        system_message=SAFETY_AGENT_SYSTEM_PROMPT,
        model_client=model_client,
    ) 