import hashlib
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters import get_adapter
from app.config import get_settings
from app.models.audit import AuditEvent
from app.models.cloud_account import CloudAccount
from app.models.execution import Execution
from app.models.recommendation import Recommendation
from app.models.resource import Resource
from app.models.tenant import Tenant
from app.services.policy import ACTION_MAP, evaluate


class ExecutionError(Exception):
    pass


def _idempotency_key(recommendation_id: uuid.UUID, action: str, target: str, mode: str) -> str:
    if mode == "dry_run":
        return f"execution:{recommendation_id}:{action}:dry_run:{uuid.uuid4().hex[:16]}"
    digest = hashlib.sha256(target.encode("utf-8")).hexdigest()[:16]
    return f"execution:{recommendation_id}:{action}:apply:{digest}"


def _extract_target_params(rec: Recommendation, resource: Resource) -> dict:
    params: dict = {"region": resource.region, "current_type": resource.type}
    if rec.proposed_state:
        for kv in rec.proposed_state:
            key = kv.get("key", "").lower()
            value = kv.get("value", "")
            if "instance type" in key or "sku" in key:
                params["target_type"] = value
            if "tier" in key and "storage" not in key:
                params["target_type"] = value
            if "node count" in key:
                params["target_node_count"] = value
    if "target_type" not in params:
        params["target_type"] = params.get("current_type", "")
    return params


def _run_preconditions(rec: Recommendation, resource: Resource, mode: str = "apply") -> list[dict]:
    checks: list[dict] = []
    checks.append(
        {
            "name": "resource_present",
            "passed": resource is not None,
            "detail": f"resource_id={resource.id}" if resource else "resource missing",
        }
    )

    if mode == "dry_run":
        return checks

    checks.append(
        {
            "name": "recommendation_status",
            "passed": rec.status == "approved",
            "detail": f"status={rec.status}",
        }
    )
    checks.append(
        {
            "name": "evidence_present",
            "passed": len(rec.evidence) > 0,
            "detail": f"{len(rec.evidence)} evidence rows",
        }
    )
    checks.append(
        {
            "name": "metric_coverage",
            "passed": float(resource.metric_coverage) >= 0.5,
            "detail": f"coverage={float(resource.metric_coverage):.2f}",
        }
    )
    return checks


def _verify(action: str, result: dict, resource: Resource) -> dict:
    if not result.get("ok"):
        return {"passed": False, "detail": "action did not succeed"}
    after = result.get("after", {})
    expected_fields = {
        "resize_instance": "instance_type" if "instance_type" in after else "sku",
        "resize_database": "tier",
        "stop_instance": "state",
        "delete_volume": "state",
        "release_eip": "state",
        "enable_tiering": "storage_class",
    }.get(action)

    if expected_fields and expected_fields not in after:
        return {"passed": False, "detail": f"missing expected field {expected_fields}"}

    return {
        "passed": True,
        "detail": f"observed {after}",
        "resource_id": str(resource.id),
        "verified_at": datetime.now(UTC).isoformat(),
    }


def _audit(db: Session, tenant_id: uuid.UUID, action_label: str, subject: str, details: str, metadata: list[dict]) -> None:
    db.add(
        AuditEvent(
            tenant_id=tenant_id,
            at=datetime.now(UTC),
            category="execution",
            severity="info",
            actor="execution-service",
            action=action_label,
            subject=subject,
            details=details,
            event_metadata=metadata,
        )
    )


def create_execution(
    db: Session,
    tenant: Tenant,
    recommendation_id: uuid.UUID,
    mode: str = "dry_run",
) -> Execution:
    try:
        return _create_execution_inner(db, tenant, recommendation_id, mode)
    except ExecutionError:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise


def _create_execution_inner(
    db: Session,
    tenant: Tenant,
    recommendation_id: uuid.UUID,
    mode: str = "dry_run",
) -> Execution:
    stmt = select(Recommendation).where(
        Recommendation.id == recommendation_id,
        Recommendation.tenant_id == tenant.id,
    )
    rec = db.execute(stmt).scalar_one_or_none()
    if rec is None:
        raise ExecutionError("Recommendation not found")

    resource = db.get(Resource, rec.resource_id)
    if resource is None:
        raise ExecutionError("Resource not found")

    action = ACTION_MAP.get(rec.type, "unknown_action")
    params = _extract_target_params(rec, resource)
    key = _idempotency_key(rec.id, action, str(params.get("target_type", "")), mode)

    if mode == "apply":
        existing = db.execute(
            select(Execution).where(
                Execution.tenant_id == tenant.id,
                Execution.idempotency_key == key,
                Execution.mode == "apply",
                Execution.status == "completed",
            )
        ).scalar_one_or_none()
        if existing is not None:
            raise ExecutionError("An identical execution has already been applied")

    if mode == "apply":
        decision = evaluate(db, tenant, rec, resource)
    else:
        decision = evaluate(db, tenant, rec, resource)
        decision.allowed = True
        decision.reasons = ["Dry run: policy evaluated but not enforced", *decision.reasons]

    preconditions = _run_preconditions(rec, resource, mode)

    execution = Execution(
        tenant_id=tenant.id,
        recommendation_id=rec.id,
        action=action,
        mode=mode,
        status="pending",
        idempotency_key=key,
        executed_by="demo.user@acme.io",
        policy_result=decision.as_dict(),
        preconditions=preconditions,
        dry_run_result={},
        verification={},
        result={},
    )
    db.add(execution)
    db.flush()

    _audit(
        db,
        tenant.id,
        "Execution dry-run requested" if mode == "dry_run" else "Execution requested",
        f"{execution.id} · {rec.title}",
        f"action={action} mode={mode}",
        [
            {"key": "execution_id", "value": str(execution.id)},
            {"key": "recommendation_id", "value": str(rec.id)},
            {"key": "action", "value": action},
        ],
    )

    if not decision.allowed:
        execution.status = "blocked"
        execution.completed_at = datetime.now(UTC)
        execution.result = {"ok": False, "error": "blocked by policy"}
        _audit(
            db,
            tenant.id,
            "Execution blocked by policy",
            f"{execution.id} · {rec.title}",
            "; ".join(decision.reasons),
            [{"key": "reasons", "value": " | ".join(decision.reasons)}],
        )
        db.commit()
        db.refresh(execution)
        return execution

    failed = [c for c in preconditions if not c["passed"]]
    if failed:
        execution.status = "failed"
        execution.completed_at = datetime.now(UTC)
        execution.result = {"ok": False, "error": "precondition failed", "checks": failed}
        db.commit()
        db.refresh(execution)
        return execution

    execution.started_at = datetime.now(UTC)
    execution.status = "running"
    db.flush()

    account = db.get(CloudAccount, resource.cloud_account_id)
    if account is None:
        execution.status = "failed"
        execution.completed_at = datetime.now(UTC)
        execution.result = {"ok": False, "error": "cloud account missing"}
        db.commit()
        db.refresh(execution)
        return execution

    if account.disabled_at is not None:
        execution.status = "failed"
        execution.completed_at = datetime.now(UTC)
        execution.result = {"ok": False, "error": "cloud account is disabled"}
        db.commit()
        db.refresh(execution)
        return execution

    adapter = get_adapter(account.provider)

    if mode == "dry_run":
        preview = {
            "ok": True,
            "action": action,
            "resource": resource.cloud_id,
            "params": params,
            "wouldChange": {
                "before": {"type": resource.type, "status": resource.status},
                "after_type": params.get("target_type", resource.type),
            },
            "mode": "dry_run",
        }
        execution.dry_run_result = preview
        execution.result = preview
        execution.status = "completed"
        execution.completed_at = datetime.now(UTC)
        execution.rollback_reference = None
        _audit(
            db,
            tenant.id,
            "Execution dry-run completed",
            f"{execution.id} · {rec.title}",
            f"target_type={params.get('target_type', '')}",
            [{"key": "execution_id", "value": str(execution.id)}],
        )
        db.commit()
        db.refresh(execution)
        return execution

    execution.dry_run_result = {
        "ok": True,
        "action": action,
        "resource": resource.cloud_id,
        "params": params,
        "mode": "dry_run",
    }

    live_result = adapter.execute_action(
        db,
        account.id,
        resource.cloud_id,
        action,
        params,
    )
    execution.result = live_result

    if live_result.get("ok"):
        execution.status = "completed"
        execution.rollback_reference = live_result.get("rollback_reference")
        execution.verification = _verify(action, live_result, resource)
    else:
        execution.status = "failed"
        execution.verification = {"passed": False, "detail": live_result.get("error", "unknown")}

    execution.completed_at = datetime.now(UTC)

    _audit(
        db,
        tenant.id,
        "Execution completed" if live_result.get("ok") else "Execution failed",
        f"{execution.id} · {rec.title}",
        live_result.get("error") or f"action={action}",
        [
            {"key": "execution_id", "value": str(execution.id)},
            {"key": "status", "value": execution.status},
        ],
    )

    db.commit()
    db.refresh(execution)
    return execution


def rollback_execution(db: Session, tenant: Tenant, execution_id: uuid.UUID) -> Execution:
    execution = db.get(Execution, execution_id)
    if execution is None or execution.tenant_id != tenant.id:
        raise ExecutionError("Execution not found")
    if execution.mode != "apply":
        raise ExecutionError("Only apply executions can be rolled back")
    if execution.status != "completed":
        raise ExecutionError("Only completed executions can be rolled back")
    if not execution.rollback_reference:
        raise ExecutionError("This action is not reversible")

    execution.rollback_status = "completed"
    execution.rollback_at = datetime.now(UTC)
    execution.status = "rolled_back"

    _audit(
        db,
        tenant.id,
        "Execution rolled back",
        f"{execution.id}",
        f"rollback_reference={execution.rollback_reference}",
        [{"key": "execution_id", "value": str(execution.id)}],
    )

    db.commit()
    db.refresh(execution)
    return execution