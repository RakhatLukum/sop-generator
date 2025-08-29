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
        # Return a mock response that provides useful content for SOP generation
        print(f"Mock client generating response for {len(messages) if isinstance(messages, list) else 1} messages")
        
        # Analyze the request to provide appropriate mock content
        user_content = ""
        if isinstance(messages, list):
            for msg in messages:
                if isinstance(msg, dict) and msg.get("role") == "user":
                    user_content = msg.get("content", "")
                    break
        elif isinstance(messages, str):
            user_content = messages
        
        # Generate appropriate mock content based on the request
        if "СОП" in user_content or "sop" in user_content.lower():
            mock_content = """# Стандартная операционная процедура (СОП)

## 1. Назначение и область применения
Данная СОП определяет порядок выполнения операций с оборудованием.

## 2. Ответственность
Ответственность за выполнение процедуры возлагается на оператора оборудования.

## 3. Процедура выполнения
3.1. Подготовительные операции
3.2. Основные операции  
3.3. Завершающие операции

## 4. Требования безопасности
**ВНИМАНИЕ:** Соблюдайте требования техники безопасности при работе с оборудованием.

## 5. Контроль качества
Контроль качества осуществляется на всех этапах процедуры."""
        
        elif "безопасность" in user_content.lower() or "safety" in user_content.lower():
            mock_content = """ПРОВЕРКА БЕЗОПАСНОСТИ:
- Требования к средствам индивидуальной защиты соблюдены
- Процедуры аварийного останова описаны
- Контактная информация службы безопасности указана
СТАТУС: ОДОБРЕНО"""
        
        elif "качеств" in user_content.lower() or "quality" in user_content.lower():
            mock_content = """КОНТРОЛЬ КАЧЕСТВА:
- Техническая документация соответствует стандартам
- Процедуры детально описаны
- Критерии успеха определены
СТАТУС: ОДОБРЕНО"""
        
        elif "критик" in user_content.lower() or "critic" in user_content.lower():
            mock_content = """SUMMARY: Документ соответствует основным требованиям
ISSUES: Незначительные улучшения в детализации процедур
STATUS: APPROVED"""
        
        else:
            mock_content = f"Обработан запрос: {user_content[:100]}..." if user_content else "Стандартный ответ системы"
        
        return MockChatCompletion(content=mock_content)

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


def create_direct_openai_client(cfg: Dict[str, Any]):
    """Create a direct OpenAI client for deployment compatibility."""
    try:
        from openai import AsyncOpenAI
        
        # Create a wrapper that mimics the expected autogen interface
        class DirectOpenAIClientWrapper:
            def __init__(self, config):
                self.config = config
                self._client = AsyncOpenAI(
                    api_key=config["api_key"],
                    base_url=config["base_url"]
                )
                self._model = config["model"]
                self._model_info = {
                    "vision": False,
                    "function_calling": False,
                    "json_output": False,
                    "structured_output": False,
                    "multiple_system_messages": True,
                    "family": "openai",
                }
                print(f"Created direct OpenAI client for model: {self._model}")
            
            @property
            def model_info(self):
                return self._model_info
            
            async def create(self, messages, **kwargs):
                try:
                    print(f"Direct OpenAI API call: model={self._model}, messages={len(messages) if isinstance(messages, list) else 1}")
                    
                    # Clean up kwargs to match OpenAI API
                    openai_kwargs = {
                        "model": self._model,
                        "messages": messages,
                        "temperature": kwargs.get("temperature", 0.3),
                        "max_tokens": kwargs.get("max_tokens", 1000),
                        "timeout": 30.0,  # Add timeout
                    }
                    
                    response = await self._client.chat.completions.create(**openai_kwargs)
                    print(f"Direct OpenAI API success: received {len(response.choices)} choices")
                    
                    # Convert to expected format
                    class DirectResponse:
                        def __init__(self, openai_response):
                            self.choices = [DirectChoice(openai_response.choices[0])]
                    
                    class DirectChoice:
                        def __init__(self, openai_choice):
                            self.message = DirectMessage(openai_choice.message)
                    
                    class DirectMessage:
                        def __init__(self, openai_message):
                            self.content = openai_message.content
                    
                    return DirectResponse(response)
                    
                except Exception as e:
                    print(f"Direct OpenAI client error: {e}")
                    return MockChatCompletion(f"Error from LLM API: {e}")
        
        return DirectOpenAIClientWrapper(cfg)
    except Exception as e:
        print(f"Failed to create direct OpenAI client: {e}")
        return MockOpenAIChatCompletionClient(**cfg)


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
    
    # Try to import real clients with multiple fallbacks
    try:
        # Try new autogen structure first
        from autogen_ext.models.openai import OpenAIChatCompletionClient
        print("Using autogen_ext OpenAI client")
    except ImportError as e1:
        print(f"Warning: autogen_ext.models.openai import failed: {e1}")
        try:
            # Try older autogen structure
            from autogen.models.openai import OpenAIChatCompletionClient
            print("Using autogen.models.openai client")
        except ImportError as e2:
            print(f"Warning: autogen.models.openai import failed: {e2}")
            try:
                # Use direct OpenAI client as fallback
                return create_direct_openai_client(cfg)
            except ImportError as e3:
                print(f"Warning: direct OpenAI client creation failed: {e3}")
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