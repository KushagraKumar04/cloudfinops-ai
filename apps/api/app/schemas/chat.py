from pydantic import Field

from app.schemas.base import CamelModel


class ChatRequest(CamelModel):
    message: str = Field(min_length=1, max_length=2000)


class ChatToolCall(CamelModel):
    id: str
    name: str
    args: dict = Field(default_factory=dict)
    result_summary: str = ""
    duration_ms: int = 0


class ChatFinding(CamelModel):
    severity: str
    title: str
    detail: str


class ChatEvidence(CamelModel):
    label: str
    value: str
    source: str


class ChatRecommendationRef(CamelModel):
    id: str
    title: str
    estimated_monthly_savings: float
    risk: str


class ChatResponse(CamelModel):
    answer: str
    plan: list[str] = Field(default_factory=list)
    tool_calls: list[ChatToolCall] = Field(default_factory=list)
    findings: list[ChatFinding] = Field(default_factory=list)
    evidence: list[ChatEvidence] = Field(default_factory=list)
    recommendations: list[ChatRecommendationRef] = Field(default_factory=list)
    confidence: float = 0.5
    requires_human_review: bool = False
    follow_ups: list[str] | None = None
    intent: str = "generic"
    source: str = "rules"
    llm_error: str | None = None
    run_id: str = ""