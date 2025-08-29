from typing import List, Dict, Any
from autogen_agentchat.agents import AssistantAgent

from sop_generator.config.agent_config import AGENT_DEFAULTS, build_openai_chat_client
from sop_generator.config.prompts import DOCUMENT_PARSER_SYSTEM_PROMPT
from sop_generator.utils.document_processor import parse_documents_to_chunks, create_enhanced_corpus_summary


def build_document_parser() -> AssistantAgent:
    cfg = AGENT_DEFAULTS["document_parser"]["llm_config"]
    model_client = build_openai_chat_client(cfg)
    return AssistantAgent(
        name=AGENT_DEFAULTS["document_parser"]["name"],
        system_message=DOCUMENT_PARSER_SYSTEM_PROMPT,
        model_client=model_client,
    )


def summarize_parsed_chunks(chunks: List[Dict[str, Any]]) -> str:
    """Create enhanced summary of parsed chunks with technical focus"""
    if not chunks:
        return ""
    
    # Use the enhanced corpus summary that extracts technical details
    enhanced_summary = create_enhanced_corpus_summary(chunks)
    
    if enhanced_summary:
        return enhanced_summary
    
    # Fallback to original method if enhanced summary fails
    texts = []
    for ch in chunks[:20]:
        prefix = f"[src: {ch.get('source','unknown')}] "
        snippet = ch.get("text", "").strip().replace("\n", " ")
        if snippet:
            texts.append(prefix + (snippet[:500] + ("..." if len(snippet) > 500 else "")))
    return "\n".join(texts) 