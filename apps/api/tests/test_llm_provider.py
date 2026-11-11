import json

import httpx
import pytest

from app.ai.llm import LLMError, Message, ToolSpec, get_provider
from app.ai.llm.base import estimate_cost_usd
from app.ai.llm.openai import OpenAICompatibleProvider


class FakeResponse:
    def __init__(self, status_code: int, body: dict) -> None:
        self.status_code = status_code
        self._body = body
        self.text = json.dumps(body)

    def json(self) -> dict:
        return self._body


def test_get_provider_requires_key():
    with pytest.raises(LLMError):
        get_provider("openai", "")


def test_get_provider_openai():
    provider = get_provider("openai", "sk-test")
    assert isinstance(provider, OpenAICompatibleProvider)


def test_get_provider_azure():
    provider = get_provider("azure-openai", "key", base_url="https://example.openai.azure.com")
    assert isinstance(provider, OpenAICompatibleProvider)


def test_get_provider_unknown():
    with pytest.raises(LLMError):
        get_provider("grok", "key")


def test_estimate_cost_known_model():
    cost = estimate_cost_usd("gpt-4o-mini", 1_000_000, 1_000_000)
    assert cost == pytest.approx(0.75)


def test_estimate_cost_unknown_model():
    assert estimate_cost_usd("unknown-model", 1000, 1000) == 0.0


def test_openai_chat_parses_text(monkeypatch):
    provider = OpenAICompatibleProvider(api_key="sk-test")

    def fake_post(self, url, headers=None, json=None):
        return FakeResponse(
            200,
            {
                "model": "gpt-4o-mini",
                "choices": [
                    {"message": {"content": '{"answer":"ok","findings":[],"evidence":[],"recommendations":[],"confidence":0.9,"requires_human_review":false}'}}
                ],
                "usage": {"prompt_tokens": 100, "completion_tokens": 50},
            },
        )

    monkeypatch.setattr(httpx.Client, "post", fake_post)

    response = provider.chat(
        messages=[Message(role="user", content="hi")],
        tools=[],
        model="gpt-4o-mini",
        temperature=0.2,
        max_tokens=512,
    )
    assert response.content is not None
    assert response.tool_calls == []
    assert response.input_tokens == 100
    assert response.output_tokens == 50


def test_openai_chat_parses_tool_calls(monkeypatch):
    provider = OpenAICompatibleProvider(api_key="sk-test")

    def fake_post(self, url, headers=None, json=None):
        return FakeResponse(
            200,
            {
                "model": "gpt-4o-mini",
                "choices": [
                    {
                        "message": {
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": "call_1",
                                    "type": "function",
                                    "function": {"name": "get_cost_summary", "arguments": '{"range":"7d"}'},
                                }
                            ],
                        }
                    }
                ],
                "usage": {"prompt_tokens": 20, "completion_tokens": 10},
            },
        )

    monkeypatch.setattr(httpx.Client, "post", fake_post)

    response = provider.chat(
        messages=[Message(role="user", content="hi")],
        tools=[ToolSpec(name="get_cost_summary", description="x", parameters={})],
        model="gpt-4o-mini",
        temperature=0.2,
        max_tokens=512,
    )
    assert len(response.tool_calls) == 1
    assert response.tool_calls[0].name == "get_cost_summary"
    assert response.tool_calls[0].args == {"range": "7d"}


def test_openai_chat_error_status(monkeypatch):
    provider = OpenAICompatibleProvider(api_key="sk-test")

    def fake_post(self, url, headers=None, json=None):
        return FakeResponse(401, {"error": "unauthorized"})

    monkeypatch.setattr(httpx.Client, "post", fake_post)

    with pytest.raises(LLMError):
        provider.chat(
            messages=[Message(role="user", content="hi")],
            tools=[],
            model="gpt-4o-mini",
            temperature=0.2,
            max_tokens=512,
        )