import os
import uuid
from datetime import UTC, datetime, timedelta

os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["MOCK_ADAPTERS"] = "true"
os.environ["ENCRYPTION_KEY"] = "ZmFrZS1rZXktZm9yLXRlc3RzLW9ubHktMzJieXRlcyE="
os.environ["LLM_ENABLED"] = "false"
os.environ["AUTH_DISABLED"] = "true"
os.environ["DEMO_MODE"] = "false"
os.environ["WORKER_ENABLED"] = "false"
os.environ["JWT_SECRET"] = "test-secret-for-pytest-only-must-be-32-bytes-or-more"
os.environ.pop("LLM_API_KEY", None)
os.environ.pop("LLM_BASE_URL", None)
os.environ.pop("LLM_PROVIDER_OVERRIDE", None)
os.environ.pop("LLM_MODEL_OVERRIDE", None)

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.cloud_account import CloudAccount
from app.models.tenant import Tenant

get_settings.cache_clear()

AWS_PROD_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
AZ_PROD_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")


@pytest.fixture()
def db_session():
    from app.db.session import set_session_factory

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    db = SessionLocal()

    set_session_factory(SessionLocal)
    try:
        yield db
    finally:
        set_session_factory(None)
        db.close()
        Base.metadata.drop_all(engine)


@pytest.fixture()
def seeded_tenant(db_session: Session) -> Tenant:
    tenant = Tenant(slug="demo", name="Demo Tenant")
    db_session.add(tenant)
    db_session.commit()
    db_session.refresh(tenant)

    aws = CloudAccount(
        id=AWS_PROD_ID,
        tenant_id=tenant.id,
        provider="AWS",
        name="AWS Production",
        account_identifier="123456789012",
        environment="production",
        status="connected",
        role_arn="arn:aws:iam::123456789012:role/CloudFinOpsReadOnly",
        regions=["us-east-1", "us-west-2"],
        read_only=True,
        execution_role_configured=False,
        coverage={
            "billing": {"enabled": True, "last_sync_at": None},
            "inventory": {"enabled": True, "last_sync_at": None},
            "metrics": {"enabled": True, "last_sync_at": None},
        },
        resource_count=812,
        monthly_spend=98200,
        connection_verified=True,
    )
    azure = CloudAccount(
        id=AZ_PROD_ID,
        tenant_id=tenant.id,
        provider="Azure",
        name="Azure Production",
        account_identifier="sub-9f2c-1a4e",
        environment="production",
        status="connected",
        subscription_id="9f2c-1a4e-8b7d-2c1f",
        tenant_external_id="acme.onmicrosoft.com",
        regions=["centralindia"],
        read_only=True,
        execution_role_configured=False,
        coverage={
            "billing": {"enabled": True, "last_sync_at": None},
            "inventory": {"enabled": True, "last_sync_at": None},
            "metrics": {"enabled": True, "last_sync_at": None},
        },
        resource_count=396,
        monthly_spend=55920,
        connection_verified=True,
    )
    db_session.add_all([aws, azure])
    db_session.commit()
    return tenant


@pytest.fixture()
def client(db_session: Session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()