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
    # Fallback to streamlit secrets if environment variable not found
    api_key: str = os.getenv("API_KEY", "")
    
    def __post_init__(self):
        # Additional check for Streamlit secrets
        if not self.api_key:
            try:
                import streamlit as st
                if hasattr(st, 'secrets'):
                    self.api_key = st.secrets.get("API_KEY", "")
                    if not self.base_url and st.secrets.get("OPENAI_BASE_URL"):
                        self.base_url = st.secrets["OPENAI_BASE_URL"]
                    if not self.model and st.secrets.get("CUSTOM_LLM_MODEL"):
                        self.model = st.secrets["CUSTOM_LLM_MODEL"]
            except (ImportError, AttributeError):
                pass

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


# Define mock client classes at module level
class MockOpenAIChatCompletionClient:
    def __init__(self, **kwargs):
        self.config = kwargs
        self._model = kwargs.get('model', 'mock-model')
        # Add required attributes that might be accessed
        self._model_info = {
            "vision": False,
            "function_calling": False,
            "json_output": False,
            "structured_output": False,
            "multiple_system_messages": True,
            "family": "mock",
        }
        print(f"Warning: Using mock client for model {self._model}")
    
    @property
    def model_info(self):
        """Model information property to match expected interface."""
        return self._model_info
    
    async def create(self, messages, **kwargs):
        # Return a mock response
        return MockChatCompletion(
            content="Mock response: Unable to generate content. Please check API configuration or autogen dependencies."
        )

class MockChatCompletion:
    def __init__(self, content):
        self.content = content
        self.choices = [MockChoice(content)]

class MockChoice:
    def __init__(self, content):
        self.message = MockMessage(content)

class MockMessage:
    def __init__(self, content):
        self.content = content


def build_openai_chat_client(cfg: Dict[str, Any]):
    # Validate configuration first
    api_key = cfg.get("api_key", "")
    base_url = cfg.get("base_url", "")
    
    # Debug print to see what we're getting from environment
    print(f"Debug: API_KEY from env: {'***' if api_key else 'NOT SET'}")
    print(f"Debug: BASE_URL from env: {base_url or 'NOT SET'}")
    
    if not api_key:
        print(f"Error: No API key provided. Using mock client. Set API_KEY environment variable for real LLM functionality.")
        return MockOpenAIChatCompletionClient(**cfg)
    
    if not base_url:
        print(f"Error: No base URL provided. Using mock client. Set OPENAI_BASE_URL environment variable for real LLM functionality.")
        return MockOpenAIChatCompletionClient(**cfg)
    
    # Try to import real clients
    try:
        from autogen_ext.models.openai import OpenAIChatCompletionClient
    except ImportError as e:
        print(f"Warning: autogen_ext.models.openai import failed: {e}")
        # Fallback for deployment environments where autogen_ext might not be available
        try:
            from autogen.models.openai import OpenAIChatCompletionClient
            print("Using fallback autogen.models.openai client")
        except ImportError as e2:
            print(f"Warning: autogen.models.openai import also failed: {e2}")
            print("Using mock client due to missing dependencies")
            return MockOpenAIChatCompletionClient(**cfg)
    
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