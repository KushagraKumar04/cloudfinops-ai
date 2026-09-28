from app.ai.llm.base import (
    LLMError,
    LLMResponse,
    LLMProvider,
    Message,
    ToolCall,
    ToolSpec,
)
from app.ai.llm.anthropic import AnthropicProvider
from app.ai.llm.openai import OpenAICompatibleProvider


def get_provider(
    provider: str,
    api_key: str,
    base_url: str = "",
    api_version: str = "",
) -> LLMProvider:
    if not api_key:
        raise LLMError("LLM API key is not configured")

    normalized = provider.strip().lower()
    if normalized in {"openai", "azure-openai", "azure_openai", "azureopenai"}:
        return OpenAICompatibleProvider(
            api_key=api_key,
            base_url=base_url,
            api_version=api_version,
            azure=normalized in {"azure-openai", "azure_openai", "azureopenai"},
        )
    if normalized == "anthropic":
        return AnthropicProvider(api_key=api_key, base_url=base_url)
    raise LLMError(f"Unsupported LLM provider: {provider}")


__all__ = [
    "get_provider",
    "LLMError",
    "LLMResponse",
    "LLMProvider",
    "Message",
    "ToolCall",
    "ToolSpec",
]