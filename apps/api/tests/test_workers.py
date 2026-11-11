from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from app.config import get_settings
from app.workers.queue import enqueue_task


def _sample_task(value: int) -> int:
    return value * 2


def test_enqueue_runs_inline_when_disabled(monkeypatch):
    monkeypatch.setenv("WORKER_ENABLED", "false")
    get_settings.cache_clear()
    try:
        result = enqueue_task(_sample_task, 21)
        assert result == 42
    finally:
        get_settings.cache_clear()


def test_enqueue_uses_queue_when_enabled(monkeypatch):
    monkeypatch.setenv("WORKER_ENABLED", "true")
    get_settings.cache_clear()

    fake_queue = MagicMock()
    fake_job = MagicMock(id="job-1")
    fake_queue.enqueue.return_value = fake_job

    try:
        with patch("app.workers.queue.get_queue", return_value=fake_queue):
            result = enqueue_task(_sample_task, 7)
        assert result is fake_job
        fake_queue.enqueue.assert_called_once()
        call_kwargs = fake_queue.enqueue.call_args.kwargs
        assert "job_timeout" in call_kwargs
        assert "result_ttl" in call_kwargs
    finally:
        get_settings.cache_clear()


def test_sync_job_runs_ingestion(monkeypatch, seeded_tenant, db_session):
    from sqlalchemy import select

    from app.models.cloud_account import CloudAccount

    monkeypatch.setenv("WORKER_ENABLED", "false")
    get_settings.cache_clear()
    try:
        account = db_session.execute(select(CloudAccount)).scalars().first()

        from app.workers.tasks import sync_cloud_account_job

        result = sync_cloud_account_job(str(account.id))

        assert "resources_fetched" in result
        assert "costs_inserted" in result
    finally:
        get_settings.cache_clear()


def test_audit_export_job_completes(monkeypatch, seeded_tenant, db_session):
    from app.models.audit import AuditEvent
    from app.services.audit_export import reserve_export
    from app.services.audit_storage import reset_storage
    from app.workers.tasks import create_audit_export_job

    monkeypatch.setenv("WORKER_ENABLED", "false")
    monkeypatch.setenv("AUDIT_EXPORT_BACKEND", "local")
    monkeypatch.setenv("AUDIT_EXPORT_LOCAL_ROOT", "/tmp/cloudfinops-audit-test")
    get_settings.cache_clear()
    reset_storage()

    try:
        db_session.add(
            AuditEvent(
                tenant_id=seeded_tenant.id,
                at=datetime.now(UTC),
                category="recommendation",
                severity="info",
                actor="tester",
                action="Action",
                subject="Subject",
                details="details",
                event_metadata=[],
            )
        )
        db_session.commit()

        export = reserve_export(db_session, seeded_tenant, None, "csv", None, None, None, None, None)

        result = create_audit_export_job(
            str(export.id),
            str(seeded_tenant.id),
            None,
            "csv",
            None,
            None,
            None,
            None,
            None,
        )

        assert result["status"] == "completed"
        assert result["records"] >= 1
    finally:
        get_settings.cache_clear()
        reset_storage()