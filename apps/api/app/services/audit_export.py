import csv
import io
import json
import uuid
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.audit import AuditEvent
from app.models.audit_export import AuditExport
from app.models.tenant import Tenant
from app.services.audit_storage import (
    StorageError,
    build_object_key,
    get_storage,
)


class AuditExportError(Exception):
    pass


def _now() -> datetime:
    return datetime.now(UTC)


def _collect_events(
    db: Session,
    tenant: Tenant,
    q: str | None,
    category: str | None,
    severity: str | None,
    start: date | None,
    end: date | None,
    limit: int,
) -> list[AuditEvent]:
    from app.api.v1.audit import _build_query

    stmt = _build_query(tenant, q, category, severity, start, end)
    rows = list(db.execute(stmt).scalars().all())
    rows.sort(key=lambda e: e.at, reverse=True)
    return rows[:limit]


def _render_csv(rows: list[AuditEvent]) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer, quoting=csv.QUOTE_MINIMAL)
    writer.writerow(["at", "category", "severity", "actor", "action", "subject", "details", "metadata"])
    for event in rows:
        metadata = "; ".join(f"{m.get('key')}={m.get('value')}" for m in (event.event_metadata or []))
        writer.writerow(
            [
                event.at.isoformat(),
                event.category,
                event.severity,
                event.actor,
                event.action,
                event.subject,
                event.details,
                metadata,
            ]
        )
    payload = buffer.getvalue()
    buffer.close()
    return payload.encode("utf-8")


def _render_json(rows: list[AuditEvent]) -> bytes:
    payload = [
        {
            "at": e.at.isoformat(),
            "category": e.category,
            "severity": e.severity,
            "actor": e.actor,
            "action": e.action,
            "subject": e.subject,
            "details": e.details,
            "metadata": e.event_metadata or [],
        }
        for e in rows
    ]
    return json.dumps(payload, indent=2).encode("utf-8")


def reserve_export(
    db: Session,
    tenant: Tenant,
    user_id: uuid.UUID | None,
    fmt: str,
    q: str | None,
    category: str | None,
    severity: str | None,
    start: date | None,
    end: date | None,
) -> AuditExport:
    settings = get_settings()
    export_id = uuid.uuid4()
    object_key = build_object_key(tenant.id, export_id, fmt)

    export = AuditExport(
        id=export_id,
        tenant_id=tenant.id,
        requested_by_user_id=user_id,
        format=fmt,
        storage_backend=settings.audit_export_backend.strip().lower(),
        object_key=object_key,
        status="pending",
        filters={
            "q": q,
            "category": category,
            "severity": severity,
            "start": start.isoformat() if start else None,
            "end": end.isoformat() if end else None,
        },
        expires_at=_now() + timedelta(days=settings.audit_export_retention_days),
    )
    db.add(export)
    db.commit()
    db.refresh(export)
    return export


def run_pending_export(
    db: Session,
    tenant: Tenant,
    export_id: uuid.UUID,
    user_id: uuid.UUID | None,
    fmt: str,
    q: str | None,
    category: str | None,
    severity: str | None,
    start: date | None,
    end: date | None,
) -> AuditExport:
    settings = get_settings()
    export = db.get(AuditExport, export_id)
    if export is None:
        raise AuditExportError("Export not found")
    if export.tenant_id != tenant.id:
        raise AuditExportError("Tenant mismatch")
    if export.status not in {"pending", "failed"}:
        return export

    export.status = "running"
    export.error = None
    db.commit()

    try:
        rows = _collect_events(
            db,
            tenant,
            q,
            category,
            severity,
            start,
            end,
            settings.audit_export_max_records,
        )
        payload = _render_csv(rows) if fmt == "csv" else _render_json(rows)

        storage = get_storage()
        stored = storage.put(export.object_key, payload)

        export.storage_backend = stored.backend
        export.size_bytes = stored.size_bytes
        export.record_count = len(rows)
        export.status = "completed"
        export.completed_at = _now()
    except StorageError as exc:
        export.status = "failed"
        export.error = str(exc)[:480]
        export.completed_at = _now()
    except Exception as exc:
        export.status = "failed"
        export.error = str(exc)[:480]
        export.completed_at = _now()

    db.commit()
    db.refresh(export)
    return export


def create_export(
    db: Session,
    tenant: Tenant,
    user_id: uuid.UUID | None,
    fmt: str,
    q: str | None,
    category: str | None,
    severity: str | None,
    start: date | None,
    end: date | None,
) -> AuditExport:
    export = reserve_export(db, tenant, user_id, fmt, q, category, severity, start, end)
    return run_pending_export(
        db,
        tenant,
        export.id,
        user_id,
        fmt,
        q,
        category,
        severity,
        start,
        end,
    )


def list_exports(db: Session, tenant: Tenant, limit: int = 50) -> list[AuditExport]:
    stmt = (
        select(AuditExport)
        .where(
            AuditExport.tenant_id == tenant.id,
            AuditExport.deleted_at.is_(None),
        )
        .order_by(AuditExport.created_at.desc())
        .limit(limit)
    )
    return list(db.execute(stmt).scalars().all())


def get_export(db: Session, tenant: Tenant, export_id: uuid.UUID) -> AuditExport | None:
    export = db.get(AuditExport, export_id)
    if export is None or export.tenant_id != tenant.id or export.deleted_at is not None:
        return None
    return export


def download_url(export: AuditExport) -> str | None:
    if export.status != "completed":
        return None
    settings = get_settings()
    try:
        storage = get_storage()
        return storage.signed_url(export.object_key, settings.audit_export_signed_url_ttl_seconds)
    except StorageError:
        return None


def delete_export(db: Session, tenant: Tenant, export_id: uuid.UUID) -> bool:
    export = get_export(db, tenant, export_id)
    if export is None:
        return False

    try:
        storage = get_storage()
        storage.delete(export.object_key)
    except StorageError:
        pass

    export.deleted_at = _now()
    db.commit()
    return True


def cleanup_expired(db: Session, tenant: Tenant | None = None) -> int:
    now = _now()
    stmt = select(AuditExport).where(
        AuditExport.deleted_at.is_(None),
        AuditExport.expires_at <= now,
    )
    if tenant is not None:
        stmt = stmt.where(AuditExport.tenant_id == tenant.id)
    rows = list(db.execute(stmt).scalars().all())

    storage = get_storage()
    removed = 0
    for export in rows:
        try:
            storage.delete(export.object_key)
        except StorageError:
            pass
        export.deleted_at = now
        removed += 1
    db.commit()
    return removed