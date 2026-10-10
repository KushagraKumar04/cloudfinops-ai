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
                continue
            entry: dict[str, Any] = {"role": m.role}
            if m.content is not None:
                entry["content"] = m.content
            if m.tool_calls:
                entry["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.name, "arguments": json.dumps(tc.args)},
                    }
                    for tc in m.tool_calls
                ]
            if m.role == "assistant" and m.content is None and not m.tool_calls:
                entry["content"] = ""
            out.append(entry)
        return out

    def _serialize_tools(self, tools: list[ToolSpec]) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                },
            }
            for t in tools
        ]

    def chat(
        self,
        messages: list[Message],
        tools: list[ToolSpec],
        model: str,
        temperature: float,
        max_tokens: int,
        force_json: bool = True,
        tool_choice: str | None = None,
    ) -> LLMResponse:
        body: dict[str, Any] = {
            "messages": self._serialize_messages(messages),
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if not self._azure:
            body["model"] = model
        if tools:
            body["tools"] = self._serialize_tools(tools)
            if tool_choice == "required":
                body["tool_choice"] = "required"
            elif tool_choice == "none":
                body["tool_choice"] = "none"
            else:
                body["tool_choice"] = tool_choice or "auto"
        if force_json and not tools and tool_choice != "none":
            body["response_format"] = {"type": "json_object"}

        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.post(self._url(model), headers=self._headers(), json=body)
                if response.status_code == 429:
                    import time as _time

                    _time.sleep(1.2)
                    response = client.post(self._url(model), headers=self._headers(), json=body)
        except httpx.HTTPError as exc:
            raise LLMError(f"LLM request failed: {exc}") from exc

        if response.status_code >= 400:
            raise LLMError(f"LLM returned {response.status_code}: {response.text[:300]}")

        try:
            payload = response.json()
        except ValueError as exc:
            raise LLMError("LLM response was not JSON") from exc

        choices = payload.get("choices") or []
        if not choices:
            raise LLMError("LLM returned no choices")

        message = choices[0].get("message") or {}
        tool_calls: list[ToolCall] = []
        for tc in message.get("tool_calls") or []:
