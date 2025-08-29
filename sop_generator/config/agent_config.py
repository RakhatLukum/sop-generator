from dataclasses import dataclass
from typing import Dict, Any
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


# Custom LLM server configuration
CUSTOM_LLM_BASE = "https://llm.govplan.kz/v1"
CUSTOM_LLM_MODEL = "meta-llama/Llama-3.3-70B-Instruct"


@dataclass
class LLMConfig:
    model: str = os.getenv("CUSTOM_LLM_MODEL", CUSTOM_LLM_MODEL)
    temperature: float = 0.3
    max_tokens: int = 1000  # Reduced for faster responses
    timeout: int = 30  # Reduced timeout
    base_url: str = os.getenv("OPENAI_BASE_URL", CUSTOM_LLM_BASE)
    api_key: str = os.getenv("API_KEY", "")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "request_timeout": self.timeout,
            "base_url": self.base_url,
            "api_key": self.api_key,
            "extra_headers": {
                "Content-Type": "application/json; charset=utf-8"
            },
        }


DEFAULT_LLM = LLMConfig()


AGENT_DEFAULTS: Dict[str, Dict[str, Any]] = {
    "coordinator": {
        "name": "Coordinator",
        "llm_config": {**DEFAULT_LLM.to_dict(), "max_tokens": 500},  # Shorter for coordination
    },
    "sop_generator": {
        "name": "SOP_Generator",
        "llm_config": {**DEFAULT_LLM.to_dict(), "temperature": 0.3, "max_tokens": 2000},  # Increased for detailed SOPs
    },
    "document_parser": {
        "name": "Document_Parser",
        "llm_config": {**DEFAULT_LLM.to_dict(), "temperature": 0.2, "max_tokens": 800},  # Increased for better extraction
    },
    "content_styler": {
        "name": "Content_Styler",
        "llm_config": {**DEFAULT_LLM.to_dict(), "temperature": 0.2, "max_tokens": 600},  # Increased for styling
    },
    "critic": {
        "name": "Critic",
        "llm_config": {**DEFAULT_LLM.to_dict(), "temperature": 0.2, "max_tokens": 500},  # Increased for detailed feedback
    },
    "quality_checker": {
        "name": "Quality_Checker",
        "llm_config": {**DEFAULT_LLM.to_dict(), "temperature": 0.2, "max_tokens": 400},  # Increased for detailed QC
    },
    "safety_agent": {
        "name": "Safety_Agent",
        "llm_config": {**DEFAULT_LLM.to_dict(), "temperature": 0.2, "max_tokens": 400},  # Increased for safety details
    },
}


def _needs_custom_model_info(model: str) -> bool:
    if not model:
        return True
    lower = model.lower()
    if "deepseek" in lower or "unsloth" in lower or "hosted_vllm" in lower:
        return True
    return not (lower.startswith("gpt-") or lower.startswith("o1") or lower.startswith("o3") or lower.startswith("o4"))


def build_openai_chat_client(cfg: Dict[str, Any]):
    try:
        from autogen_ext.models.openai import OpenAIChatCompletionClient
    except ImportError:
        # Fallback for deployment environments where autogen_ext might not be available
        try:
            from autogen.models.openai import OpenAIChatCompletionClient
        except ImportError:
            # Final fallback - create a mock client
            class MockOpenAIChatCompletionClient:
                def __init__(self, **kwargs):
                    self.config = kwargs
                    print(f"Warning: Using mock client due to missing autogen dependencies")
            OpenAIChatCompletionClient = MockOpenAIChatCompletionClient
    create_args = {
        "model": cfg.get("model"),
        "api_key": cfg.get("api_key"),
        "base_url": cfg.get("base_url"),
        "temperature": cfg.get("temperature", 0.3),
        "max_tokens": cfg.get("max_tokens", 2000),
        "request_timeout": cfg.get("request_timeout", 60),
        # Ensure messages from multiple agents remain valid for OpenAI-compatible servers
        "add_name_prefixes": True,
    }
    if _needs_custom_model_info(str(create_args["model"])):
        create_args["model_info"] = {
            "vision": False,
            "function_calling": False,
            "json_output": False,
            "structured_output": False,
            "multiple_system_messages": True,
            "family": "unknown",
        }
    return OpenAIChatCompletionClient(**create_args) 