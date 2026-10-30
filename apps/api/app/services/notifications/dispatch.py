import uuid
from datetime import UTC, datetime
from typing import Any, Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.notification import Notification, NotificationRule
from app.services.notifications.base import Notifier, SendResult
from app.services.notifications.email import EmailNotifier
from app.services.notifications.webhook import WebhookNotifier

EVENT_TYPES: dict[str, str] = {
    "cost.anomaly.detected": "Cost anomaly detected",
    "budget.breach.risk": "Budget breach risk",
    "recommendation.created": "Recommendation created",
    "recommendation.high_risk": "High-risk recommendation",
    "policy.blocked": "Policy blocked an action",
    "commitment.expiring": "Commitment expiring soon",
    "kubernetes.over_provisioned": "Kubernetes workload over-provisioned",
    "test": "Test notification",
}

SEVERITY_ORDER: dict[str, int] = {"info": 0, "warning": 1, "critical": 2}


def _resolve_notifier(channel: str) -> Notifier:
    if channel == "email":
        return EmailNotifier()
    if channel == "webhook":
        return WebhookNotifier()
    raise ValueError(f"Unsupported channel: {channel}")


_notifier_factory: Callable[[str], Notifier] = _resolve_notifier


def set_notifier_factory(factory: Callable[[str], Notifier] | None) -> None:
    global _notifier_factory
    _notifier_factory = factory or _resolve_notifier


def list_rules(db: Session, tenant_id: uuid.UUID) -> list[NotificationRule]:
    stmt = (
        select(NotificationRule)
        .where(NotificationRule.tenant_id == tenant_id)
        .order_by(NotificationRule.created_at.asc())
    )
    return list(db.execute(stmt).scalars().all())


def list_deliveries(
    db: Session,
    tenant_id: uuid.UUID,
    status: str | None = None,
    event_type: str | None = None,
    unread_only: bool = False,
    limit: int = 100,
) -> list[Notification]:
    stmt = select(Notification).where(Notification.tenant_id == tenant_id)
    if status and status != "all":
        stmt = stmt.where(Notification.status == status)
    if event_type and event_type != "all":
        stmt = stmt.where(Notification.event_type == event_type)
    if unread_only:
        stmt = stmt.where(Notification.read_at.is_(None))
    stmt = stmt.order_by(Notification.created_at.desc()).limit(limit)
    return list(db.execute(stmt).scalars().all())


def count_unread(db: Session, tenant_id: uuid.UUID) -> int:
    from sqlalchemy import func as _func

    stmt = select(_func.count(Notification.id)).where(
        Notification.tenant_id == tenant_id,
        Notification.read_at.is_(None),
    )
    return int(db.execute(stmt).scalar() or 0)


def mark_read(db: Session, tenant_id: uuid.UUID, notification_id: uuid.UUID) -> Notification | None:
    notification = db.get(Notification, notification_id)
    if notification is None or notification.tenant_id != tenant_id:
        return None
    if notification.read_at is None:
        notification.read_at = datetime.now(UTC)
        db.commit()
        db.refresh(notification)
    return notification


def mark_all_read(db: Session, tenant_id: uuid.UUID) -> int:
    stmt = select(Notification).where(
        Notification.tenant_id == tenant_id,
        Notification.read_at.is_(None),
    )
    rows = list(db.execute(stmt).scalars().all())
    now = datetime.now(UTC)
    for row in rows:
        row.read_at = now
    db.commit()
    return len(rows)


def _matching_rules(
    db: Session,
    tenant_id: uuid.UUID,
    event_type: str,
    severity: str,
) -> list[NotificationRule]:
    stmt = select(NotificationRule).where(
        NotificationRule.tenant_id == tenant_id,
        NotificationRule.enabled.is_(True),
        NotificationRule.event_type == event_type,
    )
    rules = list(db.execute(stmt).scalars().all())
    sev_rank = SEVERITY_ORDER.get(severity, 0)
    return [r for r in rules if SEVERITY_ORDER.get(r.min_severity, 0) <= sev_rank]


def _deliver(
    db: Session,
    tenant_id: uuid.UUID,
    rule: NotificationRule | None,
    event_type: str,
    severity: str,
    subject: str,
    body: str,
    event_metadata: dict[str, Any] | None = None,
) -> Notification:
    destination = dict(rule.destination) if rule else {}
    channel = rule.channel if rule else "email"

    try:
        notifier = _notifier_factory(channel)
        result: SendResult = notifier.send(destination, subject, body)
        status = result.status
        error = result.error
        duration_ms = result.duration_ms
    except Exception as exc:
        status = "failed"
        error = str(exc)[:480]
        duration_ms = 0

    delivery = Notification(
        tenant_id=tenant_id,
        rule_id=rule.id if rule else None,
        event_type=event_type,
        severity=severity,
        channel=channel,
        subject=subject[:300],
        body=body[:4000],
        destination=destination,
        event_metadata=event_metadata or {},
        status=status,
        error=error,
        attempt=1,
        duration_ms=duration_ms,
    )
    db.add(delivery)

    if rule is not None:
        rule.last_fired_at = datetime.now(UTC)
        rule.fire_count = (rule.fire_count or 0) + 1

    db.flush()
    return delivery


def dispatch_event(
    db: Session,
    tenant_id: uuid.UUID,
    event_type: str,
    severity: str,
    subject: str,
    body: str,
    metadata: dict[str, Any] | None = None,
    commit: bool = True,
) -> list[Notification]:
    rules = _matching_rules(db, tenant_id, event_type, severity)
    if not rules:
        if commit:
            db.commit()
        return []

    out: list[Notification] = []
    for rule in rules:
        out.append(_deliver(db, tenant_id, rule, event_type, severity, subject, body, metadata))
    if commit:
        db.commit()
    return out


def dispatch_test(
    db: Session,
    tenant_id: uuid.UUID,
    rule: NotificationRule,
) -> Notification:
    subject = f"[Test] {rule.name}"
    body = (
        f"This is a test notification from CloudFinOps AI.\n\n"
        f"Rule: {rule.name}\n"
        f"Event type: {rule.event_type}\n"
        f"Channel: {rule.channel}\n"
    )
    delivery = _deliver(
        db,
        tenant_id,
        rule,
        "test",
        "info",
        subject,
        body,
        {"test": True, "rule_id": str(rule.id)},
    )
    db.commit()
    return delivery