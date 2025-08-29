from sop_generator.config.agent_config import AGENT_DEFAULTS, build_openai_chat_client
from sop_generator.config.prompts import CRITIC_SYSTEM_PROMPT
from sop_generator.agents.base_imports import AssistantAgent


def build_critic() -> AssistantAgent:
    cfg = AGENT_DEFAULTS["critic"]["llm_config"]
    model_client = build_openai_chat_client(cfg)
    return AssistantAgent(
        name=AGENT_DEFAULTS["critic"]["name"],
        system_message=CRITIC_SYSTEM_PROMPT,
        model_client=model_client,
    ) 