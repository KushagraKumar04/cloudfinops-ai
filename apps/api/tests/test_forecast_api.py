from datetime import date, timedelta
from decimal import Decimal

from app.models.budget import Budget
from app.models.cost import CostRecord


def _seed_costs(db_session, tenant, account_id, days=90):
    today = date.today()
    for i in range(days):
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
        Budget(
            tenant_id=tenant.id,
            name="Test budget",
            amount=Decimal("10000"),
            currency="USD",
            period="monthly",
            scope="all",
        )
    )
    db_session.commit()


def test_forecast_summary(client, seeded_tenant, db_session):
    from app.models.cloud_account import CloudAccount
    from sqlalchemy import select

    account = db_session.execute(select(CloudAccount)).scalars().first()
    _seed_costs(db_session, seeded_tenant, account.id)

    r = client.get("/api/v1/forecasts/summary", params={"horizon": "30d"})
    assert r.status_code == 200
    body = r.json()
    assert body["budget"] == 10000.0
    assert "monthEndProjection" in body
    assert body["trendDirection"] in {"up", "down", "flat"}


def test_forecast_series(client, seeded_tenant, db_session):
    from app.models.cloud_account import CloudAccount
    from sqlalchemy import select

    account = db_session.execute(select(CloudAccount)).scalars().first()
    _seed_costs(db_session, seeded_tenant, account.id)

    r = client.get("/api/v1/forecasts/series", params={"horizon": "30d"})
    assert r.status_code == 200
    body = r.json()
    actual_points = [p for p in body if p["actual"] is not None]
    forecast_points = [p for p in body if p["forecast"] is not None]
    assert len(actual_points) == 90
    assert len(forecast_points) == 30


def test_forecast_by_service(client, seeded_tenant, db_session):
    from app.models.cloud_account import CloudAccount
    from sqlalchemy import select

    account = db_session.execute(select(CloudAccount)).scalars().first()
    _seed_costs(db_session, seeded_tenant, account.id)

    r = client.get("/api/v1/forecasts/by-service")
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    assert body[0]["name"] == "EC2"


def test_forecast_scenarios(client, seeded_tenant, db_session):
    from app.models.cloud_account import CloudAccount
    from sqlalchemy import select

    account = db_session.execute(select(CloudAccount)).scalars().first()
    _seed_costs(db_session, seeded_tenant, account.id)

    r = client.get("/api/v1/forecasts/scenarios")
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 4
    ids = {s["id"] for s in body}
    assert "sc_compute_20" in ids
    assert "sc_no_action" in ids