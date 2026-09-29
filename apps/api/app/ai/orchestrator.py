import json
import logging
import uuid
from typing import Any

from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.llm import LLMError, LLMProvider, Message, ToolCall, ToolSpec, get_provider
from app.ai.llm.base import estimate_cost_usd
from app.ai.llm.prompts import SYSTEM_PROMPT
from app.ai.tool_schemas import tool_specs
from app.ai.tools import TOOLS, ToolContext, ToolResult, execute_tool
from app.config import get_settings
from app.models.agent_helpers import persist_agent_run
from app.models.tenant import Tenant

logger = logging.getLogger(__name__)


class LLMFindings(BaseModel):
    severity: str = "info"
    title: str = ""
    detail: str = ""


class LLMEvidence(BaseModel):
    label: str = ""
    value: str = ""
    source: str = ""


class LLMRecommendationRef(BaseModel):
    id: str = ""
    title: str = ""
    estimated_monthly_savings: float = Field(default=0, alias="estimatedMonthlySavings")
    risk: str = "MEDIUM"

    model_config = {"populate_by_name": True}


class LLMAnswer(BaseModel):
    answer: str = ""
    findings: list[LLMFindings] = Field(default_factory=list)
    evidence: list[LLMEvidence] = Field(default_factory=list)
    recommendations: list[LLMRecommendationRef] = Field(default_factory=list)
    confidence: float = 0.5
    requires_human_review: bool = False
    follow_ups: list[str] | None = Field(default=None, alias="followUps")

    model_config = {"populate_by_name": True}


INTENT_PATTERNS: list[tuple[str, list[tuple[str, dict[str, Any]]], list[str]]] = [
    (
        "cost_increase",
        [
            ("get_cost_summary", {"range": "7d"}),
            ("get_cost_breakdown", {"dimension": "service", "range": "7d"}),
            ("get_anomalies", {}),
        ],
        [
            "Summarize current period spend and change vs previous period",
            "Identify the services with the largest absolute change",
            "Cross-reference detected anomalies",
        ],
    ),
    (
        "idle",
        [
            ("find_idle_resources", {"cpu_threshold": 15.0}),
            ("list_recommendations", {"status": "pending", "limit": 5}),
        ],
        [
            "Find resources with sustained low utilization and sufficient metric coverage",
            "Rank by monthly cost and open recommendations",
        ],
    ),
    (
        "top_savings",
        [
            ("list_recommendations", {"status": "pending", "limit": 10}),
            ("calculate_savings", {"recommendation_ids": []}),
        ],
        [
            "Enumerate pending recommendations sorted by savings",
            "Aggregate total identified savings",
        ],
    ),
    (
        "forecast",
        [
            ("get_cost_summary", {"range": "30d"}),
            ("forecast_spend", {"horizon": "30d"}),
        ],
        [
            "Load recent spend history",
            "Project the next 30 days using the trend plus seasonal model",
        ],
    ),
    (
        "storage",
        [
            ("get_cost_breakdown", {"dimension": "service", "range": "30d"}),
            ("list_recommendations", {"status": "pending", "limit": 5}),
        ],
        [
            "Aggregate storage cost by service",
            "Identify tiering and unattached storage opportunities",
        ],
    ),
]

KEYWORDS: dict[str, list[str]] = {
    "cost_increase": ["why", "increase", "rise", "spike", "jump", "grew", "higher"],
    "idle": ["idle", "unused", "unattached", "underutil", "stopped"],
    "top_savings": ["top", "savings", "opportunit", "optimize", "biggest"],
    "forecast": ["forecast", "project", "next month", "next 30", "predict"],
    "storage": ["storage", "s3", "blob", "disk", "volume", "bucket"],
}

PRIORITY_ORDER = ["storage", "idle", "forecast", "top_savings", "cost_increase"]


def classify(question: str) -> str:
    q = question.lower()
    for intent in PRIORITY_ORDER:
        if intent == "cost_increase":
            if ("cost" in q or "spend" in q or "bill" in q) and any(k in q for k in KEYWORDS["cost_increase"]):
                return intent
        else:
            if any(k in q for k in KEYWORDS[intent]):
                return intent
    return "generic"


def plan_for(intent: str) -> tuple[list[str], list[tuple[str, dict[str, Any]]]]:
    for name, calls, steps in INTENT_PATTERNS:
        if name == intent:
            return steps, calls
    return (
        ["Clarify the question and retrieve the minimum context needed"],
        [("get_cost_summary", {"range": "30d"})],
    )


def _resolve_llm_config(tenant: Tenant) -> dict[str, Any] | None:
    settings = get_settings()
    if not settings.llm_enabled:
        return None
    if not settings.llm_api_key:
        return None

    tenant_llm = (tenant.settings or {}).get("llm", {}) or {}
    provider = settings.llm_provider_override or tenant_llm.get("provider", "openai")
    model = settings.llm_model_override or tenant_llm.get("model", "gpt-4o-mini")
    temperature = float(tenant_llm.get("temperature", 0.2))
    max_tokens = int(tenant_llm.get("maxTokens", 2048))

    return {
        "provider": provider,
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "api_key": settings.llm_api_key,
        "base_url": settings.llm_base_url,
        "api_version": settings.llm_api_version,
        "timeout": float(settings.llm_timeout_seconds),
        "max_iterations": int(settings.llm_max_tool_iterations),
    }


def _build_provider(config: dict[str, Any]) -> LLMProvider:
    provider = get_provider(
        provider=config["provider"],
        api_key=config["api_key"],
        base_url=config.get("base_url", ""),
        api_version=config.get("api_version", ""),
    )
    if hasattr(provider, "_timeout"):
        provider._timeout = config["timeout"]
    return provider


ANSWER_TOOL_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "answer": {
            "type": "string",
            "description": "2-5 sentence direct response to the user's question.",
        },
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "severity": {"type": "string", "enum": ["info", "warning", "critical"]},
                    "title": {"type": "string"},
                    "detail": {"type": "string"},
                },
                "required": ["severity", "title", "detail"],
            },
        },
        "evidence": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "label": {"type": "string"},
                    "value": {"type": "string"},
                    "source": {"type": "string"},
                },
                "required": ["label", "value", "source"],
            },
        },
        "recommendations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "title": {"type": "string"},
                    "estimatedMonthlySavings": {"type": "number"},
                    "risk": {"type": "string", "enum": ["LOW", "MEDIUM", "HIGH", "BLOCKED"]},
                },
                "required": ["id", "title", "estimatedMonthlySavings", "risk"],
            },
        },
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "requires_human_review": {"type": "boolean"},
        "followUps": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": [
        "answer",
        "findings",
        "evidence",
        "recommendations",
        "confidence",
        "requires_human_review",
    ],
}


def _tool_specs_list() -> list[ToolSpec]:
    return [ToolSpec(name=s["name"], description=s["description"], parameters=s["parameters"]) for s in tool_specs()]


def _submit_answer_spec() -> ToolSpec:
    return ToolSpec(
        name="submit_answer",
        description=(
            "Submit the final structured answer to the user's question. "
            "Call this exactly once when you have gathered enough evidence and are ready to answer."
        ),
        parameters=ANSWER_TOOL_SCHEMA,
    )


def _parse_answer(raw: str | None) -> LLMAnswer:
    if not raw:
        raise LLMError("LLM produced no content")
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].lstrip()
    try:
        payload = json.loads(text)
    except ValueError as exc:
        raise LLMError(f"LLM content was not JSON: {exc}") from exc
    try:
        return LLMAnswer.model_validate(payload)
    except ValidationError as exc:
        raise LLMError(f"LLM output failed validation: {exc}") from exc


def _parse_answer_from_dict(payload: dict[str, Any]) -> LLMAnswer:
    try:
        return LLMAnswer.model_validate(payload)
    except ValidationError as exc:
        raise LLMError(f"submit_answer payload failed validation: {exc}") from exc


def _summarize_tool_result(result: ToolResult) -> str:
    payload = {"summary": result.summary, "data": result.data}
    text = json.dumps(payload, default=str)
    if len(text) > 1500:
        text = text[:1500] + "...[truncated]"
    return text


def run_with_llm(
    db: Session,
    tenant: Tenant,
    question: str,
    config: dict[str, Any],
    history: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    provider = _build_provider(config)
    ctx = ToolContext(db=db, tenant_id=tenant.id)
    specs = _tool_specs_list()
    catalog = {s.name: s for s in specs}

    messages: list[Message] = [Message(role="system", content=SYSTEM_PROMPT)]
    if history:
        for turn in history[-6:]:
            role = turn.get("role")
            content = turn.get("content")
            if role in {"user", "assistant"} and content:
                messages.append(Message(role=role, content=content))
    messages.append(Message(role="user", content=question))

    executed_tools: list[dict[str, Any]] = []
    plan_steps: list[str] = []
    total_input = 0
    total_output = 0
    last_model = config["model"]

    for iteration in range(config["max_iterations"]):
        is_last = iteration == config["max_iterations"] - 1
        if is_last:
            messages.append(
                Message(
                    role="system",
                    content=(
                        "You now have enough evidence. Call the `submit_answer` tool with the "
                        "final structured response. Do not call any other tool."
                    ),
                )
            )
            response = provider.chat(
                messages=messages,
                tools=[_submit_answer_spec()],
                model=config["model"],
                temperature=config["temperature"],
                max_tokens=config["max_tokens"],
                force_json=False,
                tool_choice="required",
            )
        else:
            response = provider.chat(
                messages=messages,
                tools=specs,
                model=config["model"],
                temperature=config["temperature"],
                max_tokens=config["max_tokens"],
                force_json=False,
            )
        total_input += response.input_tokens
        total_output += response.output_tokens
        last_model = response.model

        if response.tool_calls:
            if is_last:
                submit = next((tc for tc in response.tool_calls if tc.name == "submit_answer"), None)
                if submit is not None:
                    parsed = _parse_answer_from_dict(submit.args)
                    return _finalize_llm(
                        db=db,
                        tenant_id=tenant.id,
                        parsed=parsed,
                        executed_tools=executed_tools,
                        plan_steps=plan_steps or ["Answer using retrieved context"],
                        total_input=total_input,
                        total_output=total_output,
                        model=last_model,
                    )

            messages.append(
                Message(
                    role="assistant",
                    content=response.content,
                    tool_calls=response.tool_calls,
                )
            )
            for tc in response.tool_calls:
                if tc.name == "submit_answer":
                    continue
                if tc.name not in catalog:
                    result = ToolResult(summary=f"Unknown tool: {tc.name}")
                else:
                    result = execute_tool(tc.name, ctx, tc.args or {})
                executed_tools.append(
                    {
                        "id": tc.id or f"tool_{uuid.uuid4().hex[:8]}",
                        "name": tc.name,
                        "args": tc.args if isinstance(tc.args, dict) else {},
                        "result_summary": result.summary,
                        "duration_ms": result.duration_ms,
                    }
                )
                if not plan_steps:
                    plan_steps.append(f"Investigate using {tc.name}")
                messages.append(
                    Message(
                        role="tool",
                        tool_call_id=tc.id,
                        content=_summarize_tool_result(result),
                    )
                )
            continue

        parsed = _parse_answer(response.content)
        return _finalize_llm(
            db=db,
            tenant_id=tenant.id,
            parsed=parsed,
            executed_tools=executed_tools,
            plan_steps=plan_steps or ["Answer using retrieved context"],
            total_input=total_input,
            total_output=total_output,
            model=last_model,
        )

    raise LLMError("Max tool iterations reached without a final answer")


def _ground_recommendations(
    db: Session,
    tenant_id: uuid.UUID,
    refs: list[LLMRecommendationRef],
) -> list[dict[str, Any]]:
    import uuid as _uuid

    from app.models.recommendation import Recommendation

    if not refs:
        return []

    parsed_ids: list[_uuid.UUID] = []
    for r in refs:
        try:
            parsed_ids.append(_uuid.UUID(r.id))
        except (ValueError, AttributeError, TypeError):
            logger.warning("Dropping hallucinated recommendation id: %r", r.id)

    if not parsed_ids:
        return []

    rows = list(
        db.execute(
            select(Recommendation).where(
                Recommendation.tenant_id == tenant_id,
                Recommendation.id.in_(parsed_ids),
            )
        )
        .scalars()
        .all()
    )

    found_ids = {r.id for r in rows}
    for pid in parsed_ids:
        if pid not in found_ids:
            logger.warning("LLM referenced non-existent recommendation: %s", pid)

    by_id = {str(r.id): r for r in rows}
    out: list[dict[str, Any]] = []
    for ref in refs:
        real = by_id.get(ref.id)
        if real is None:
            continue
        out.append(
            {
                "id": str(real.id),
                "title": real.title,
                "estimated_monthly_savings": float(real.estimated_monthly_savings),
                "risk": real.risk,
            }
        )
    return out


def _finalize_llm(
    db: Session,
    tenant_id: uuid.UUID,
    parsed: LLMAnswer,
    executed_tools: list[dict[str, Any]],
    plan_steps: list[str],
    total_input: int,
    total_output: int,
    model: str,
) -> dict[str, Any]:
    grounded_recs = _ground_recommendations(db, tenant_id, parsed.recommendations)

    return {
        "intent": "llm",
        "plan": plan_steps,
        "tool_calls": executed_tools,
        "response": {
            "answer": parsed.answer or "No answer was produced.",
            "findings": [f.model_dump() for f in parsed.findings],
            "evidence": [e.model_dump() for e in parsed.evidence],
            "recommendations": grounded_recs,
            "confidence": float(parsed.confidence),
            "requires_human_review": bool(parsed.requires_human_review),
            "follow_ups": parsed.follow_ups,
        },
        "source": "llm",
        "usage": {
            "model": model,
            "input_tokens": total_input,
            "output_tokens": total_output,
            "estimated_cost_usd": estimate_cost_usd(model, total_input, total_output),
        },
    }


def synthesize(intent: str, question: str, results: list[ToolResult]) -> dict[str, Any]:
    def find(name_fragment: str) -> ToolResult | None:
        for r in results:
            if name_fragment in r.summary.lower():
                return r
        return None

    if intent == "cost_increase":
        summary_data = next((r.data for r in results if "spend" in r.summary.lower() or "current" in r.data), {})
        breakdown = next((r.data for r in results if r.data.get("dimension")), {})
        anomalies = next((r.data for r in results if "anomalies" in r.data), {})

        current = summary_data.get("current", 0)
        change_pct = summary_data.get("change_pct", 0)
        change_amount = summary_data.get("change_amount", 0)
        top_service = (breakdown.get("rows") or [{}])[0]

        findings = []
        if top_service.get("name"):
            findings.append(
                {
                    "severity": "critical" if top_service["change_pct"] > 20 else "warning",
                    "title": f"{top_service['name']} {top_service['change_pct']:+.1f}%",
                    "detail": f"${top_service['spend']:,.0f} in the current period.",
                }
            )
        for a in (anomalies.get("anomalies") or [])[:2]:
            findings.append(
                {
                    "severity": "warning" if a["severity"] != "high" else "critical",
                    "title": f"{a['service']} {a['delta_pct']:+.0f}%",
                    "detail": a["description"],
                }
            )

        evidence = [
            {"label": "Current spend", "value": f"${current:,.0f}", "source": "Cost records"},
            {"label": "Change", "value": f"{change_pct:+.1f}% (${change_amount:,.0f})", "source": "Cost records"},
        ]
        for row in (breakdown.get("rows") or [])[:3]:
            evidence.append(
                {
                    "label": row["name"],
                    "value": f"${row['spend']:,.0f} ({row['change_pct']:+.1f}%)",
                    "source": "Cost records",
                }
            )

        answer = (
            f"Spend is ${current:,.0f}, {change_pct:+.1f}% vs the previous period"
            + (f". The largest mover is {top_service['name']} at ${top_service['spend']:,.0f} ({top_service['change_pct']:+.1f}%)." if top_service.get("name") else ".")
        )
        return {
            "answer": answer,
            "findings": findings,
            "evidence": evidence,
            "recommendations": [],
            "confidence": 0.88,
            "requires_human_review": True,
        }

    if intent == "idle":
        idle_data = next((r.data for r in results if "candidates" in r.data), {})
        recs_data = next((r.data for r in results if "recommendations" in r.data), {})
        candidates = idle_data.get("candidates", [])
        total = idle_data.get("total_monthly_cost", 0)

        findings = []
        for c in candidates[:3]:
            findings.append(
                {
                    "severity": "warning" if c["environment"] == "production" else "info",
                    "title": f"{c['name']} · {c['cpu']}% CPU",
                    "detail": f"${c['monthly_cost']:,.0f}/mo · {c['environment']}",
                }
            )

        answer = (
            f"Found {len(candidates)} resources with sustained low utilization and adequate metric coverage, "
            f"totalling ${total:,.0f}/month in identified spend."
        )

        evidence = [
            {"label": "Candidates", "value": str(len(candidates)), "source": "FinOps engine"},
            {"label": "Identified spend", "value": f"${total:,.0f}/mo", "source": "Cost records"},
        ]

        recommendations = [
            {
                "id": r["id"],
                "title": r["title"],
                "estimated_monthly_savings": r["estimated_monthly_savings"],
                "risk": r["risk"],
            }
            for r in (recs_data.get("recommendations") or [])[:4]
        ]

        return {
            "answer": answer,
            "findings": findings,
            "evidence": evidence,
            "recommendations": recommendations,
            "confidence": 0.9,
            "requires_human_review": True,
        }

    if intent == "top_savings":
        recs_data = next((r.data for r in results if "recommendations" in r.data), {})
        recs = recs_data.get("recommendations", [])
        total = recs_data.get("total_savings", 0)
        top = recs[:3]

        findings = [
            {
                "severity": "info",
                "title": r["title"][:80],
                "detail": f"${r['estimated_monthly_savings']:,.0f}/mo · {r['risk']} risk",
            }
            for r in top
        ]

        answer = f"{len(recs)} pending recommendations total ${total:,.0f}/month in identified savings."

        evidence = [
            {"label": "Pending recommendations", "value": str(len(recs)), "source": "FinOps engine"},
            {"label": "Total savings", "value": f"${total:,.0f}/mo", "source": "Savings calculator"},
        ]

        recommendations = [
            {
                "id": r["id"],
                "title": r["title"],
                "estimated_monthly_savings": r["estimated_monthly_savings"],
                "risk": r["risk"],
            }
            for r in top
        ]

        return {
            "answer": answer,
            "findings": findings,
            "evidence": evidence,
            "recommendations": recommendations,
            "confidence": 0.9,
            "requires_human_review": False,
        }

    if intent == "forecast":
        summary_data = next((r.data for r in results if "current" in r.data), {})
        forecast_data = next((r.data for r in results if "projected_total" in r.data), {})
        projected = forecast_data.get("projected_total", 0)
        current = summary_data.get("current", 0)

        answer = f"Based on recent history, projected 30-day spend is ${projected:,.0f}."
        findings = [
            {"severity": "info", "title": "30-day projection", "detail": f"${projected:,.0f}"},
        ]
        if current > 0:
            findings.append(
                {"severity": "info", "title": "Trailing 30 days", "detail": f"${current:,.0f}"}
            )

        evidence = [
            {"label": "Projection", "value": f"${projected:,.0f}", "source": "Forecast model"},
            {"label": "Trailing 30 days", "value": f"${current:,.0f}", "source": "Cost records"},
        ]

        return {
            "answer": answer,
            "findings": findings,
            "evidence": evidence,
            "recommendations": [],
            "confidence": 0.82,
            "requires_human_review": False,
        }

    if intent == "storage":
        breakdown_data = next((r.data for r in results if "rows" in r.data), {})
        recs_data = next((r.data for r in results if "recommendations" in r.data), {})
        storage_rows = [
            r for r in (breakdown_data.get("rows") or [])
            if r["name"] in {"S3", "EBS", "Blob Storage", "Azure Disk", "Azure SQL", "RDS"}
        ][:5]

        findings = [
            {"severity": "warning", "title": r["name"], "detail": f"${r['spend']:,.0f} · {r['change_pct']:+.1f}%"}
            for r in storage_rows
        ]

        total = sum(r["spend"] for r in storage_rows)
        answer = f"Storage and data services total ${total:,.0f} in the current period."

        evidence = [
            {"label": r["name"], "value": f"${r['spend']:,.0f}", "source": "Cost records"}
            for r in storage_rows
        ]

        recommendations = [
            {
                "id": r["id"],
                "title": r["title"],
                "estimated_monthly_savings": r["estimated_monthly_savings"],
                "risk": r["risk"],
            }
            for r in (recs_data.get("recommendations") or [])
            if any(k in r["title"].lower() for k in ("storage", "s3", "volume", "blob"))
        ][:4]

        return {
            "answer": answer,
            "findings": findings,
            "evidence": evidence,
            "recommendations": recommendations,
            "confidence": 0.87,
            "requires_human_review": False,
        }

    summary_data = next((r.data for r in results if "current" in r.data), {})
    current = summary_data.get("current", 0)
    return {
        "answer": (
            f"I can investigate cost changes, idle resources, top savings, forecasts, and storage. "
            f"Current trailing spend is ${current:,.0f}. Try one of the suggested questions or rephrase with a time range and provider."
        ),
        "findings": [],
        "evidence": [
            {"label": "Trailing spend", "value": f"${current:,.0f}", "source": "Cost records"},
        ],
        "recommendations": [],
        "confidence": 0.55,
        "requires_human_review": False,
        "follow_ups": [
            "Why did compute cost increase this week?",
            "Show me our top savings opportunities.",
            "Which resources are idle?",
            "Forecast spend for the next 30 days.",
        ],
    }


def run_with_rules(db: Session, tenant: Tenant, question: str) -> dict[str, Any]:
    intent = classify(question)
    plan_steps, tool_calls = plan_for(intent)
    ctx = ToolContext(db=db, tenant_id=tenant.id)

    results: list[ToolResult] = []
    executed: list[dict[str, Any]] = []
    for name, args in tool_calls:
        result = execute_tool(name, ctx, args)
        results.append(result)
        executed.append(
            {
                "id": f"tool_{uuid.uuid4().hex[:8]}",
                "name": name,
                "args": args,
                "result_summary": result.summary,
                "duration_ms": result.duration_ms,
            }
        )

    synthesized = synthesize(intent, question, results)
    return {
        "intent": intent,
        "plan": plan_steps,
        "tool_calls": executed,
        "response": synthesized,
        "source": "rules",
        "usage": {
            "model": "rule-based-fallback",
            "input_tokens": 0,
            "output_tokens": 0,
            "estimated_cost_usd": 0.0,
        },
    }


def run_orchestrator(
    db: Session,
    tenant_id: uuid.UUID,
    question: str,
    history: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    tenant = db.get(Tenant, tenant_id)
    if tenant is None:
        raise ValueError("Tenant not found")

    config = _resolve_llm_config(tenant)
    llm_error: str | None = None

    if config is not None:
        try:
            result = run_with_llm(db, tenant, question, config, history=history)
            persist_agent_run(db, tenant_id, question, result)
            return result
        except LLMError as exc:
            llm_error = str(exc)
            logger.warning("LLM orchestrator failed, falling back to rules: %s", exc)
        except Exception as exc:
            llm_error = f"{type(exc).__name__}: {exc}"
            logger.exception("Unexpected LLM failure: %s", exc)

    result = run_with_rules(db, tenant, question)
    if llm_error:
        result["llm_error"] = llm_error
    persist_agent_run(db, tenant_id, question, result)
    return result