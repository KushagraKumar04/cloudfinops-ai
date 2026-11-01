import logging
import uuid

from app.db.session import create_session

logger = logging.getLogger("app.workers.tasks")


def sync_cloud_account_job(cloud_account_id: str) -> dict:
    from app.services.ingestion import IngestionService

    db = create_session()
    try:
        service = IngestionService(db)
        result = service.sync_account(uuid.UUID(cloud_account_id))
        return result.as_dict()
    except Exception as exc:
        logger.exception("sync_cloud_account_job failed for %s", cloud_account_id)
        raise exc
    finally:
        db.close()


def create_audit_export_job(
    export_id: str,
    tenant_id: str,
    user_id: str | None,
    fmt: str,
    q: str | None,
    category: str | None,
    severity: str | None,
    start_iso: str | None,
    end_iso: str | None,
) -> dict:
    from datetime import date

    from app.models.tenant import Tenant
    from app.services.audit_export import run_pending_export

    db = create_session()
    try:
        tenant = db.get(Tenant, uuid.UUID(tenant_id))
        if tenant is None:
            raise RuntimeError("Tenant not found")

        start = date.fromisoformat(start_iso) if start_iso else None
        end = date.fromisoformat(end_iso) if end_iso else None
        export = run_pending_export(
            db,
            tenant,
            uuid.UUID(export_id),
            uuid.UUID(user_id) if user_id else None,
            fmt,
            q,
            category,
            severity,
            start,
            end,
        )
        return {"id": str(export.id), "status": export.status, "records": export.record_count}
    except Exception as exc:
        logger.exception("create_audit_export_job failed for %s", export_id)
        raise exc
    finally:
        db.close()