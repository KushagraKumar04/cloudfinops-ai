import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.ai.tools import ToolContext, ToolResult, execute_tool
from app.models.agent_helpers import persist_agent_run


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
            if ("cost" in q or "spend" in q or "bill" in q) and any(
                k in q for k in KEYWORDS["cost_increase"]
            ):
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

        answer = (
            f"{len(recs)} pending recommendations total ${total:,.0f}/month in identified savings."
        )

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
                {
                    "severity": "info",
                    "title": "Trailing 30 days",
                    "detail": f"${current:,.0f}",
                }
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
            {
                "severity": "warning",
                "title": r["name"],
                "detail": f"${r['spend']:,.0f} · {r['change_pct']:+.1f}%",
            }
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
            if "storage" in r["title"].lower() or "s3" in r["title"].lower() or "volume" in r["title"].lower() or "blob" in r["title"].lower()
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
            f'I can investigate cost changes, idle resources, top savings, forecasts, and storage. '
            f'Current trailing spend is ${current:,.0f}. Try one of the suggested questions or rephrase with a time range and provider.'
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


class Orchestrator:
    def __init__(self, db: Session, tenant_id: uuid.UUID) -> None:
        self.db = db
        self.tenant_id = tenant_id
        self.ctx = ToolContext(db=db, tenant_id=tenant_id)

    def run(self, question: str) -> dict[str, Any]:
        intent = classify(question)
        plan_steps, tool_calls = plan_for(intent)

        results: list[ToolResult] = []
        executed: list[dict[str, Any]] = []
        for name, args in tool_calls:
            result = execute_tool(name, self.ctx, args)
            results.append(result)
            executed.append(
                {
                    "id": f"tool_{uuid.uuid4().hex[:8]}",
                    "name": name,
                    "args": _sanitize_args(args),
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
        }


def _sanitize_args(args: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in args.items():
        if isinstance(v, (str, int, float, bool)) or v is None:
            out[k] = v
        else:
            out[k] = str(v)
    return out


def run_orchestrator(db: Session, tenant_id: uuid.UUID, question: str) -> dict[str, Any]:
    orch = Orchestrator(db=db, tenant_id=tenant_id)
    result = orch.run(question)
    persist_agent_run(db, tenant_id, question, result)
    return result