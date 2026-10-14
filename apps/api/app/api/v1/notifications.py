import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_tenant, require_permission
from app.services.permissions import Permission
from app.db.session import get_db
from app.models.notification import Notification, NotificationRule
from app.models.tenant import Tenant
from app.schemas.notification import (
    DispatchIn,
    NotificationListOut,
    NotificationOut,
    RuleIn,
    RuleListOut,
    RuleOut,
    RuleUpdate,
)
from app.services.notifications import (
    EVENT_TYPES,
    count_unread,
    dispatch_event,
    dispatch_test,
    list_deliveries,
    list_rules,
    mark_all_read,
    mark_read,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=NotificationListOut)
def list_notifications(
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    status: str | None = Query(default=None),
    event_type: str | None = Query(default=None),
    unread_only: bool = Query(default=False),
    limit: int = Query(default=100, ge=1, le=500),
) -> NotificationListOut:
    rows = list_deliveries(
        db,
        tenant.id,
        status=status,
        event_type=event_type,
        unread_only=unread_only,
        limit=limit,
    )
    items = [NotificationOut.model_validate(r) for r in rows]

    totals_stmt = (
        select(Notification.status, func.count(Notification.id))
        .where(Notification.tenant_id == tenant.id)
        .group_by(Notification.status)
    )
    totals = {status_: int(count) for status_, count in db.execute(totals_stmt).all()}
    unread = count_unread(db, tenant.id)
    return NotificationListOut(items=items, total=len(items), unread=unread, totals=totals)


@router.post("/{notification_id}/read", response_model=NotificationOut)
def mark_notification_read(
    notification_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> NotificationOut:
    notification = mark_read(db, tenant.id, notification_id)
    if notification is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    return NotificationOut.model_validate(notification)


@router.post("/read-all", response_model=dict)
def mark_all_notifications_read(
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> dict:
    count = mark_all_read(db, tenant.id)
    return {"markedRead": count}


@router.get("/rules", response_model=RuleListOut)
def list_notification_rules(
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> RuleListOut:
    rows = list_rules(db, tenant.id)
    items = [RuleOut.model_validate(r) for r in rows]
    return RuleListOut(items=items, total=len(items), event_types=EVENT_TYPES)


@router.post(
    "/rules",
    response_model=RuleOut,
    status_code=201,
    dependencies=[Depends(require_permission(Permission.MANAGE_NOTIFICATIONS))],
)
def create_rule(
    payload: RuleIn,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> RuleOut:
    if payload.event_type not in EVENT_TYPES:
        raise HTTPException(status_code=422, detail=f"Unknown event_type: {payload.event_type}")

    existing = db.execute(
        select(NotificationRule).where(
            NotificationRule.tenant_id == tenant.id,
            NotificationRule.name == payload.name,
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=409, detail="Rule name already exists")

    rule = NotificationRule(
        tenant_id=tenant.id,
        name=payload.name,
        description=payload.description,
        event_type=payload.event_type,
        channel=payload.channel,
        destination=payload.destination,
        min_severity=payload.min_severity,
        enabled=payload.enabled,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return RuleOut.model_validate(rule)


@router.put(
    "/rules/{rule_id}",
    response_model=RuleOut,
    dependencies=[Depends(require_permission(Permission.MANAGE_NOTIFICATIONS))],
)
def update_rule(
    rule_id: uuid.UUID,
    payload: RuleUpdate,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> RuleOut:
    rule = db.get(NotificationRule, rule_id)
    if rule is None or rule.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Rule not found")

    if payload.event_type is not None and payload.event_type not in EVENT_TYPES:
        raise HTTPException(status_code=422, detail=f"Unknown event_type: {payload.event_type}")

    for field in ("name", "description", "event_type", "channel", "destination", "min_severity", "enabled"):
        value = getattr(payload, field)
        if value is not None:
            setattr(rule, field, value)

    db.commit()
    db.refresh(rule)
    return RuleOut.model_validate(rule)


@router.delete(
    "/rules/{rule_id}",
    status_code=204,
    dependencies=[Depends(require_permission(Permission.MANAGE_NOTIFICATIONS))],
)
def delete_rule(
    rule_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> None:
    rule = db.get(NotificationRule, rule_id)
    if rule is None or rule.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Rule not found")
    db.delete(rule)
    db.commit()
    return None


@router.post(
    "/rules/{rule_id}/test",
    response_model=NotificationOut,
    dependencies=[Depends(require_permission(Permission.MANAGE_NOTIFICATIONS))],
)
def test_rule(
    rule_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> NotificationOut:
    rule = db.get(NotificationRule, rule_id)
    if rule is None or rule.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Rule not found")
    delivery = dispatch_test(db, tenant.id, rule)
    return NotificationOut.model_validate(delivery)


@router.post(
    "/dispatch",
    response_model=NotificationListOut,
    dependencies=[Depends(require_permission(Permission.MANAGE_NOTIFICATIONS))],
)
def dispatch(
    payload: DispatchIn,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> NotificationListOut:
    if payload.event_type not in EVENT_TYPES:
        raise HTTPException(status_code=422, detail=f"Unknown event_type: {payload.event_type}")
    deliveries = dispatch_event(
        db,
        tenant.id,
        payload.event_type,
        payload.severity,
        payload.subject,
        payload.body,
        metadata=payload.metadata,
    )
    items = [NotificationOut.model_validate(d) for d in deliveries]
    return NotificationListOut(items=items, total=len(items), totals={})