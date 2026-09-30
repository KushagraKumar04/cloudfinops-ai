import json
from typing import Any

import httpx

from app.ai.llm.base import LLMError, LLMResponse, Message, ToolCall, ToolSpec


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, api_key: str, base_url: str = "", timeout: float = 60.0) -> None:
        self._endpoint = (base_url or "https://api.anthropic.com/v1").rstrip("/")
        self._api_key = api_key
        self._timeout = timeout

    def _headers(self) -> dict[str, str]:
        return {
            "x-api-key": self._api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }

    def _split_system(self, messages: list[Message]) -> tuple[str, list[dict[str, Any]]]:
        system_parts: list[str] = []
        conversation: list[dict[str, Any]] = []
        for m in messages:
            if m.role == "system":
                if m.content:
                    system_parts.append(m.content)
                continue
            if m.role == "tool":
                conversation.append(
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": m.tool_call_id or "",
                                "content": m.content or "",
                            }
                        ],
                    }
                )
                continue
            if m.role == "assistant" and m.tool_calls:
                blocks: list[dict[str, Any]] = []
                if m.content:
                    blocks.append({"type": "text", "text": m.content})
                for tc in m.tool_calls:
                    blocks.append(
                        {"type": "tool_use", "id": tc.id, "name": tc.name, "input": tc.args}
                    )
                conversation.append({"role": "assistant", "content": blocks})
                continue
            conversation.append({"role": m.role, "content": m.content or ""})
        return "\n\n".join(system_parts), conversation

    def _serialize_tools(self, tools: list[ToolSpec]) -> list[dict[str, Any]]:
        return [
            {"name": t.name, "description": t.description, "input_schema": t.parameters}
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
        system_text, conversation = self._split_system(messages)
        body: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system": system_text,
            "messages": conversation,
        }
        if tools:
            body["tools"] = self._serialize_tools(tools)
            if tool_choice == "none":
                body["tool_choice"] = {"type": "none"}
            elif tool_choice == "required":
                body["tool_choice"] = {"type": "any"}

        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.post(f"{self._endpoint}/messages", headers=self._headers(), json=body)
        except httpx.HTTPError as exc:
            raise LLMError(f"Anthropic request failed: {exc}") from exc

        if response.status_code >= 400:
            raise LLMError(f"Anthropic returned {response.status_code}: {response.text[:300]}")

        try:
            payload = response.json()
        except ValueError as exc:
            raise LLMError("Anthropic response was not JSON") from exc

        content_blocks = payload.get("content") or []
        text_parts: list[str] = []
        tool_calls: list[ToolCall] = []
        for block in content_blocks:
            btype = block.get("type")
            if btype == "text":
                text_parts.append(block.get("text", ""))
            elif btype == "tool_use":
                tool_calls.append(
                    ToolCall(
                        id=block.get("id", ""),
                        name=block.get("name", ""),
                        args=block.get("input") or {},
                    )
                )

        usage = payload.get("usage") or {}
        return LLMResponse(
            content="\n".join(p for p in text_parts if p) or None,
            tool_calls=tool_calls,
            input_tokens=int(usage.get("input_tokens", 0)),
            output_tokens=int(usage.get("output_tokens", 0)),
            model=payload.get("model", model),
        )