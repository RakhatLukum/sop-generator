from autogen_agentchat.agents import AssistantAgent
from config.agent_config import AGENT_DEFAULTS, build_openai_chat_client
from config.prompts import QUALITY_CHECKER_SYSTEM_PROMPT


def build_quality_checker() -> AssistantAgent:
    cfg = AGENT_DEFAULTS["quality_checker"]["llm_config"]
    model_client = build_openai_chat_client(cfg)
    return AssistantAgent(
        name=AGENT_DEFAULTS["quality_checker"]["name"],
        system_message=QUALITY_CHECKER_SYSTEM_PROMPT,
        model_client=model_client,
    ) 