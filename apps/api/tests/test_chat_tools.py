from datetime import date, timedelta
from decimal import Decimal

from app.ai.tools import ToolContext, execute_tool
from app.models.cost import CostRecord
from app.models.resource import Resource


def _seed_cost_data(db_session, tenant, account_id):
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
        db_session.add(
            CostRecord(
                tenant_id=tenant.id,
                cloud_account_id=account_id,
                date=d,
                provider="AWS",
                service="RDS",
                region="us-east-1",
                cost=Decimal("50"),
                currency="USD",
                usage_quantity=Decimal("1"),
                usage_unit="day",
                tags={},
            )
        )
    db_session.commit()


def test_get_cost_summary_tool(client, seeded_tenant, db_session):
    from app.models.cloud_account import CloudAccount
    from sqlalchemy import select

    account = db_session.execute(select(CloudAccount)).scalars().first()
    _seed_cost_data(db_session, seeded_tenant, account.id)

    ctx = ToolContext(db_session, seeded_tenant.id)
    result = execute_tool("get_cost_summary", ctx, {"range": "7d"})
    assert result.data["current"] > 0
    assert result.duration_ms >= 0


def test_get_cost_breakdown_tool(client, seeded_tenant, db_session):
    from app.models.cloud_account import CloudAccount
    from sqlalchemy import select

    account = db_session.execute(select(CloudAccount)).scalars().first()
    _seed_cost_data(db_session, seeded_tenant, account.id)

    ctx = ToolContext(db_session, seeded_tenant.id)
    result = execute_tool("get_cost_breakdown", ctx, {"dimension": "service"})
    rows = result.data["rows"]
    assert len(rows) == 2
    assert rows[0]["name"] == "EC2"


def test_find_idle_resources_tool(client, seeded_tenant, db_session):
    from app.models.cloud_account import CloudAccount
    from sqlalchemy import select

    account = db_session.execute(select(CloudAccount)).scalars().first()
    db_session.add(
        Resource(
            tenant_id=seeded_tenant.id,
            cloud_account_id=account.id,
            provider="AWS",
            cloud_id="i-idle",
            name="idle",
            type="EC2 m5.large",
            service="EC2",
            region="us-east-1",
            environment="staging",
            status="running",
            utilization={"cpu": 5},
            metric_coverage=Decimal("0.9"),
            monthly_cost=Decimal("50"),
        )
    )
    db_session.commit()

    ctx = ToolContext(db_session, seeded_tenant.id)
    result = execute_tool("find_idle_resources", ctx, {"cpu_threshold": 15})
    assert len(result.data["candidates"]) == 1


def test_list_recommendations_tool(client, seeded_tenant, db_session):
    ctx = ToolContext(db_session, seeded_tenant.id)
    result = execute_tool("list_recommendations", ctx, {"status": "pending"})
    assert "recommendations" in result.data


def test_unknown_tool(client, seeded_tenant, db_session):
    ctx = ToolContext(db_session, seeded_tenant.id)
    result = execute_tool("does_not_exist", ctx, {})
    assert "Unknown" in result.summary