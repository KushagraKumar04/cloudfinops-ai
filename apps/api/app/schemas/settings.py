from app.schemas.base import CamelModel


class PolicyRule(CamelModel):
    id: str
    scope: str
    description: str
    enabled: bool
    requires_approval: bool
    block_auto_execution: bool


class ThresholdRule(CamelModel):
    id: str
    label: str
    description: str
    value: float
    unit: str
    minimum: float
    maximum: float


class LlmConfig(CamelModel):
    provider: str
    model: str
    temperature: float
    max_tokens: int
    cache_enabled: bool
    compact_tool_outputs: bool
    prompt_version: str
    api_key_configured: bool = False


class SettingsOut(CamelModel):
    policies: list[PolicyRule]
    thresholds: list[ThresholdRule]
    llm: LlmConfig


class PoliciesIn(CamelModel):
    policies: list[PolicyRule]


class ThresholdsIn(CamelModel):
    thresholds: list[ThresholdRule]


class LlmIn(CamelModel):
    llm: LlmConfig