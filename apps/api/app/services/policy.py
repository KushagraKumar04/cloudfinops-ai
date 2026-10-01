from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.models.recommendation import Recommendation
from app.models.resource import Resource
from app.models.tenant import Tenant


ACTION_MAP: dict[str, str] = {
    "compute.rightsizing": "resize_instance",
    "compute.idle": "stop_instance",
    "storage.unattached": "delete_volume",
    "storage.tiering": "enable_tiering",
    "network.unused_eip": "release_eip",
    "database.rightsizing": "resize_database",
}


@dataclass
class PolicyDecision:
    allowed: bool
    risk: str
    reasons: list[str] = field(default_factory=list)
    requires_approval: bool = True
    block_auto_execution: bool = False
    requires_security_review: bool = False
    action: str = ""

    def as_dict(self) -> dict:
        return {
            "allowed": self.allowed,
            "risk": self.risk,
            "reasons": list(self.reasons),
            "requiresApproval": self.requires_approval,
            "blockAutoExecution": self.block_auto_execution,
            "requiresSecurityReview": self.requires_security_review,
            "action": self.action,
        }


def _enabled_policies(tenant: Tenant) -> dict[str, dict]:
    settings = tenant.settings or {}
    out: dict[str, dict] = {}
    for p in settings.get("policies", []):
        if p.get("enabled"):
            out[p["id"]] = p
    return out


def _matches(resource: Resource, rec: Recommendation, policy_id: str) -> bool:
    env = (resource.environment or "").lower()
    rec_type = (rec.type or "").lower()
    action = ACTION_MAP.get(rec.type, "")

    if policy_id == "production.allow_auto_execution":
        return env == "production"
    if policy_id == "database.require_approval":
        return "database" in rec_type or action == "resize_database"
    if policy_id == "network.require_security_review":
        return "network" in rec_type or action == "release_eip"
    if policy_id == "delete_resource.require_approval":
        return action in {"delete_volume", "release_eip"}
    if policy_id == "max_monthly_savings_claim.require_evidence":
        return float(rec.estimated_monthly_savings) > 0
    return False


def evaluate(
    db: Session,
    tenant: Tenant,
    recommendation: Recommendation,
    resource: Resource,
) -> PolicyDecision:
    action = ACTION_MAP.get(recommendation.type, "unknown_action")
    decision = PolicyDecision(
        allowed=True,
        risk=recommendation.risk,
        action=action,
    )

    if recommendation.risk == "BLOCKED":
        decision.allowed = False
        decision.reasons.append("Recommendation is marked BLOCKED")
        return decision

    if recommendation.status != "approved":
        decision.allowed = False
        decision.reasons.append(f"Recommendation status is {recommendation.status}, must be approved")
        return decision

    if not recommendation.evidence:
        decision.allowed = False
        decision.reasons.append("Missing evidence")
        return decision

    if float(resource.metric_coverage) < 0.5 and action in {"resize_instance", "resize_database", "stop_instance"}:
        decision.allowed = False
        decision.reasons.append("Insufficient metric coverage for a compute or database change")
        return decision

    for policy_id, policy in _enabled_policies(tenant).items():
        if not _matches(resource, recommendation, policy_id):
            continue

        if policy.get("blockAutoExecution"):
            decision.block_auto_execution = True
            decision.requires_approval = True
            decision.reasons.append(f"Policy {policy_id}: automatic execution blocked")

        if policy.get("requiresApproval"):
            decision.requires_approval = True
            decision.reasons.append(f"Policy {policy_id}: explicit approval required")

        if "security" in policy_id:
            decision.requires_security_review = True
            decision.reasons.append(f"Policy {policy_id}: security review required")

    if decision.block_auto_execution and decision.requires_approval:
        decision.allowed = False
        decision.reasons.append("Execution is gated by policy; human approval is recorded but auto execution is disabled")

    if not decision.reasons:
        decision.reasons.append("No blocking policies")

    return decision