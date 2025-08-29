from autogen_agentchat.agents import AssistantAgent
from sop_generator.config.agent_config import AGENT_DEFAULTS, build_openai_chat_client
from sop_generator.config.prompts import CONTENT_STYLER_SYSTEM_PROMPT


def build_content_styler() -> AssistantAgent:
    cfg = AGENT_DEFAULTS["content_styler"]["llm_config"]
    model_client = build_openai_chat_client(cfg)
    return AssistantAgent(
        name=AGENT_DEFAULTS["content_styler"]["name"],
        system_message=CONTENT_STYLER_SYSTEM_PROMPT,
        model_client=model_client,
    ) 