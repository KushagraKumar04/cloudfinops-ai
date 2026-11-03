from datetime import date, timedelta
from decimal import Decimal

from app.models.audit import AuditEvent
from app.models.chat import AgentRun, ToolCall
from app.models.cost import CostRecord


def _seed(db_session, tenant, account_id):
    today = date.today()
    for i in range(30):
        d = today - timedelta(days=i)
        db_session.add(
            CostRecord(
                tenant_id=tenant.id,
                cloud_account_id=account_id,
                date=d,
                provider="AWS",
                service="EC2",
                region="us-east-1",
                cost=Decimal("100"),
                currency="USD",
                usage_quantity=Decimal("1"),
                usage_unit="day",
                tags={},
            )
        )
    db_session.commit()


def test_chat_empty_message(client, seeded_tenant):
    r = client.post("/api/v1/chat", json={"message": "   "})
    assert r.status_code == 422


def test_chat_cost_increase(client, seeded_tenant, db_session):
    from app.models.cloud_account import CloudAccount
    from sqlalchemy import select

    account = db_session.execute(select(CloudAccount)).scalars().first()
    _seed(db_session, seeded_tenant, account.id)

    r = client.post("/api/v1/chat", json={"message": "Why did compute cost increase this week?"})
    assert r.status_code == 200
    body = r.json()
    assert body["source"] == "rules"
    assert body["intent"] == "cost_increase"
    assert len(body["plan"]) > 0
    assert len(body["toolCalls"]) > 0
    assert "answer" in body
    assert body["confidence"] > 0


def test_chat_idle(client, seeded_tenant):
    r = client.post("/api/v1/chat", json={"message": "Which resources are idle?"})
    assert r.status_code == 200
    assert r.json()["intent"] == "idle"


def test_chat_top_savings(client, seeded_tenant):
    r = client.post("/api/v1/chat", json={"message": "Show me our top savings opportunities."})
    assert r.status_code == 200
    assert r.json()["intent"] == "top_savings"


def test_chat_forecast(client, seeded_tenant):
    r = client.post("/api/v1/chat", json={"message": "Forecast spend for the next 30 days."})
    assert r.status_code == 200
    assert r.json()["intent"] == "forecast"


def test_chat_storage(client, seeded_tenant):
    r = client.post("/api/v1/chat", json={"message": "Why is storage cost increasing?"})
    assert r.status_code == 200
    assert r.json()["intent"] == "storage"


def test_chat_generic(client, seeded_tenant):
    r = client.post("/api/v1/chat", json={"message": "Hello"})
    assert r.status_code == 200
    body = r.json()
    assert body["intent"] == "generic"
    assert body["followUps"] is not None
    assert len(body["followUps"]) >= 1


def test_chat_persists_agent_run(client, seeded_tenant, db_session):
    from sqlalchemy import select

    client.post("/api/v1/chat", json={"message": "Why did cost increase this week?"})

    runs = list(db_session.execute(select(AgentRun)).scalars().all())
    assert len(runs) == 1
    assert runs[0].user_message == "Why did cost increase this week?"

    tool_calls = list(db_session.execute(select(ToolCall)).scalars().all())
    assert len(tool_calls) >= 1


def test_chat_writes_audit_event(client, seeded_tenant, db_session):
    from sqlalchemy import select

    client.post("/api/v1/chat", json={"message": "Why did cost increase?"})

    events = list(db_session.execute(select(AuditEvent)).scalars().all())
    assert any(e.action == "Chat run completed" for e in events)