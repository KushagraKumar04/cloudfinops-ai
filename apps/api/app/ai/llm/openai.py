import json
from typing import Any

import httpx

from app.ai.llm.base import LLMError, LLMResponse, Message, ToolCall, ToolSpec


class OpenAICompatibleProvider:
    name = "openai-compatible"

    def __init__(
        self,
        api_key: str,
        base_url: str = "",
        api_version: str = "",
        azure: bool = False,
        timeout: float = 60.0,
    ) -> None:
        if azure:
            if not base_url:
                raise LLMError("Azure OpenAI requires LLM_BASE_URL")
            self._endpoint = base_url.rstrip("/")
        else:
            self._endpoint = (base_url or "https://api.openai.com/v1").rstrip("/")
        self._api_key = api_key
        self._api_version = api_version
        self._azure = azure
        self._timeout = timeout

