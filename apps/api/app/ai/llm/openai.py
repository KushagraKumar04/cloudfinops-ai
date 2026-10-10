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

    def _url(self, model: str) -> str:
        if self._azure:
            return f"{self._endpoint}/openai/deployments/{model}/chat/completions?api-version={self._api_version}"
        return f"{self._endpoint}/chat/completions"

    def _headers(self) -> dict[str, str]:
        if self._azure:
            return {"api-key": self._api_key, "Content-Type": "application/json"}
        return {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}

    def _serialize_messages(self, messages: list[Message]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for m in messages:
            if m.role == "tool":
                out.append(
                    {
                        "role": "tool",
                        "tool_call_id": m.tool_call_id or "",
                        "content": m.content or "",
                    }
                )
