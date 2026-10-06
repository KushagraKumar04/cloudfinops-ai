import csv
import io
import json
import uuid
from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse, StreamingResponse
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_tenant, get_current_user
from app.config import get_settings
from app.db.session import get_db
from app.models.audit import AuditEvent
from app.models.audit_export import AuditExport
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.audit import AuditEventOut, AuditListOut
from app.schemas.audit_export import (
    AuditExportCleanupOut,
    AuditExportCreateIn,
    AuditExportListOut,
    AuditExportOut,
)
from app.services.audit_export import (
    cleanup_expired,
    delete_export,
    download_url,
    get_export,
    list_exports,
)
from app.services.audit_storage import LocalStorage, StorageError, get_storage

router = APIRouter(prefix="/audit", tags=["audit"])


def _build_query(
    tenant: Tenant,
    q: str | None,
    category: str | None,
    severity: str | None,
    start: date | None,
    end: date | None,
):
    stmt = select(AuditEvent).where(AuditEvent.tenant_id == tenant.id)
    if q:
        term = f"%{q.strip().lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(AuditEvent.action).like(term),
                func.lower(AuditEvent.subject).like(term),
                func.lower(AuditEvent.actor).like(term),
                func.lower(AuditEvent.details).like(term),
            )
        )
    if category and category != "all":
        stmt = stmt.where(AuditEvent.category == category)
    if severity and severity != "all":
        stmt = stmt.where(AuditEvent.severity == severity)
    if start is not None:
        stmt = stmt.where(AuditEvent.at >= datetime.combine(start, datetime.min.time()))
    if end is not None:
        stmt = stmt.where(AuditEvent.at <= datetime.combine(end, datetime.max.time()))
    return stmt


@router.get("", response_model=AuditListOut)
def list_audit_events(
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    q: str | None = Query(default=None),
    category: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    start: date | None = Query(default=None),
    end: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> AuditListOut:
    stmt = _build_query(tenant, q, category, severity, start, end)
    rows = list(db.execute(stmt).scalars().all())
    rows.sort(key=lambda e: e.at, reverse=True)

    total = len(rows)
    start_idx = (page - 1) * page_size
    page_rows = rows[start_idx : start_idx + page_size]

    items = [AuditEventOut.model_validate(e) for e in page_rows]
    return AuditListOut(items=items, total=total, page=page, page_size=page_size)


def _csv_escape(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    if any(c in text for c in [",", '"', "\n", "\r"]):
        return '"' + text.replace('"', '""') + '"'
    return text


def _stream_csv(rows: list[AuditEvent]) -> StreamingResponse:
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
    filename = f"audit-{date.today().isoformat()}.csv"
    return StreamingResponse(
        iter([payload]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _stream_json(rows: list[AuditEvent]) -> StreamingResponse:
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
    filename = f"audit-{date.today().isoformat()}.json"
    return StreamingResponse(
        iter([json.dumps(payload, indent=2)]),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _to_export_out(export) -> AuditExportOut:
    out = AuditExportOut.model_validate(export)
    out.download_url = download_url(export)
    return out


@router.post("/exports", response_model=AuditExportOut, status_code=201)
def create_audit_export(
    payload: AuditExportCreateIn,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
) -> AuditExportOut:
    from app.services.audit_export import reserve_export
    from app.workers import create_audit_export_job, enqueue_task

    export = reserve_export(
        db,
        tenant,
        user.id if user else None,
        payload.format,
        payload.q,
        payload.category,
        payload.severity,
        payload.start,
        payload.end,
    )

    export_id = export.id

    enqueue_task(
        create_audit_export_job,
        str(export_id),
        str(tenant.id),
        str(user.id) if user else None,
        payload.format,
        payload.q,
        payload.category,
        payload.severity,
        payload.start.isoformat() if payload.start else None,
        payload.end.isoformat() if payload.end else None,
    )

    db.expire_all()
    fresh = db.get(AuditExport, export_id)
    if fresh is None or fresh.tenant_id != tenant.id or fresh.deleted_at is not None:
        raise HTTPException(status_code=500, detail="Export disappeared after enqueue")
    return _to_export_out(fresh)


@router.get("/exports", response_model=AuditExportListOut)
def list_audit_exports(
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> AuditExportListOut:
    rows = list_exports(db, tenant)
    items = [_to_export_out(r) for r in rows]
    return AuditExportListOut(items=items, total=len(items))


@router.post("/exports/cleanup", response_model=AuditExportCleanupOut)
def cleanup_audit_exports(
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> AuditExportCleanupOut:
    removed = cleanup_expired(db, tenant)
    return AuditExportCleanupOut(removed=removed)


@router.get("/exports/download")
def download_audit_export(
    key: str = Query(min_length=1, max_length=600),
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> StreamingResponse:
    prefix = f"{tenant.id}/"
    if not key.startswith(prefix):
        raise HTTPException(status_code=404, detail="Export not found")

    export_stmt = select(AuditExport).where(
        AuditExport.tenant_id == tenant.id,
        AuditExport.object_key == key,
        AuditExport.deleted_at.is_(None),
    )
    export = db.execute(export_stmt).scalar_one_or_none()
    if export is None or export.status != "completed":
        raise HTTPException(status_code=404, detail="Export not found")

    storage = get_storage()
    if not isinstance(storage, LocalStorage):
        raise HTTPException(status_code=404, detail="Direct download only available for local storage")

    try:
        payload = storage.read(key)
    except StorageError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    filename = f"audit-{export.created_at.date().isoformat()}.{export.format}"
    content_type = "text/csv" if export.format == "csv" else "application/json"
    return StreamingResponse(
        iter([payload]),
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/exports/{export_id}", response_model=AuditExportOut)
def get_audit_export(
    export_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> AuditExportOut:
    export = get_export(db, tenant, export_id)
    if export is None:
        raise HTTPException(status_code=404, detail="Export not found")
    return _to_export_out(export)


@router.delete("/exports/{export_id}", status_code=204)
def delete_audit_export(
    export_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> None:
    if not delete_export(db, tenant, export_id):
        raise HTTPException(status_code=404, detail="Export not found")
    return None


@router.get("/export")
def export_audit_events(
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    format: str = Query(default="csv", pattern="^(csv|json)$"),
    q: str | None = Query(default=None),
    category: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    start: date | None = Query(default=None),
    end: date | None = Query(default=None),
):
    settings = get_settings()
    if settings.audit_export_backend.strip().lower() != "local":
        raise HTTPException(
            status_code=400,
            detail="Use POST /audit/exports to create a stored export with this backend",
        )

    stmt = _build_query(tenant, q, category, severity, start, end)
    rows = list(db.execute(stmt).scalars().all())
    rows.sort(key=lambda e: e.at, reverse=True)

    if format == "json":
        return _stream_json(rows)
    return _stream_csv(rows)