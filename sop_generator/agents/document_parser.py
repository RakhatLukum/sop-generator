from typing import List, Dict, Any
from autogen_agentchat.agents import AssistantAgent

from config.agent_config import AGENT_DEFAULTS, build_openai_chat_client
from config.prompts import DOCUMENT_PARSER_SYSTEM_PROMPT
from utils.document_processor import parse_documents_to_chunks


def build_document_parser() -> AssistantAgent:
    cfg = AGENT_DEFAULTS["document_parser"]["llm_config"]
    model_client = build_openai_chat_client(cfg)
    return AssistantAgent(
        name=AGENT_DEFAULTS["document_parser"]["name"],
        system_message=DOCUMENT_PARSER_SYSTEM_PROMPT,
        model_client=model_client,
    )


def summarize_parsed_chunks(chunks: List[Dict[str, Any]]) -> str:
    # Simple heuristic to summarize parsed text chunks for conditioning the generator
    texts = []
    for ch in chunks[:20]:
        prefix = f"[src: {ch.get('source','unknown')}] "
        snippet = ch.get("text", "").strip().replace("\n", " ")
        if snippet:
            texts.append(prefix + (snippet[:500] + ("..." if len(snippet) > 500 else "")))
    return "\n".join(texts) 