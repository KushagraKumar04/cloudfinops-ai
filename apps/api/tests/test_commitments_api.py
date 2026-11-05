import uuid
from datetime import date, timedelta
from decimal import Decimal

from app.models.commitment import Commitment, CommitmentRecommendation
from app.models.cost import CostRecord


def _seed_costs(db_session, tenant, account_id):
    for i in range(30):
        d = date.today() - timedelta(days=i)
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
                service="S3",
                region="us-east-1",
                cost=Decimal("50"),
                currency="USD",
                usage_quantity=Decimal("1"),
                usage_unit="day",
                tags={},
            )
        )
    db_session.commit()


def _seed_commitments(db_session, tenant, account_id):
    db_session.add(
        Commitment(
            tenant_id=tenant.id,
            cloud_account_id=account_id,
            provider="AWS",
            commitment_type="reserved_instance",
            service="EC2",
            region="us-east-1",
            term_months=12,
            payment_option="no_upfront",
            monthly_cost=Decimal("900"),
            monthly_savings=Decimal("280"),
            instance_count=4,
            start_date=date.today() - timedelta(days=100),
            end_date=date.today() + timedelta(days=265),
            status="active",
            utilization_pct=Decimal("0.95"),
        )
    )
    db_session.commit()


def _seed_recommendation(db_session, tenant, account_id):
    rec = CommitmentRecommendation(
        tenant_id=tenant.id,
        cloud_account_id=account_id,
        provider="AWS",
        commitment_type="savings_plan",
        service="Compute",
        region="us-east-1",
        title="Increase Compute Savings Plan",
        summary="Raise commitment to $2/hr",
        rationale="Stable compute baseline",
        term_months=12,
        payment_option="no_upfront",
        recommended_hourly_commitment=Decimal("2.0"),
        estimated_monthly_cost=Decimal("1460"),
        estimated_monthly_savings=Decimal("310"),
        estimated_annual_savings=Decimal("3720"),
        coverage_before_pct=Decimal("0.42"),
        coverage_after_pct=Decimal("0.71"),
        break_even_months=Decimal("0.0"),
        risk="LOW",
        risk_reasons=["Flexible across services"],
        confidence=Decimal("0.92"),
        status="pending",
        evidence=[{"label": "Eligible spend", "value": "$5,020", "source": "Cost records"}],
        impact={"financial": "17% discount", "operational": "No lock-in", "risk": "Low"},
    )
    db_session.add(rec)
    db_session.commit()
    return rec


def test_summary_empty(client, seeded_tenant):
    r = client.get("/api/v1/commitments/summary")
    assert r.status_code == 200
    body = r.json()
    assert body["coveragePct"] == 0
    assert body["activeCommitments"] == 0


def test_summary_with_data(client, seeded_tenant, db_session):
    from app.models.cloud_account import CloudAccount
    from sqlalchemy import select

    account = db_session.execute(select(CloudAccount)).scalars().first()
    _seed_costs(db_session, seeded_tenant, account.id)
    _seed_commitments(db_session, seeded_tenant, account.id)

    r = client.get("/api/v1/commitments/summary")
    assert r.status_code == 200
    body = r.json()
    assert body["coveredMonthlySpend"] == 900.0
    assert body["activeCommitments"] == 1
    assert body["realizedMonthlySavings"] == 280.0
    assert body["coveragePct"] > 0


def test_list_commitments(client, seeded_tenant, db_session):
    from app.models.cloud_account import CloudAccount
    from sqlalchemy import select

    account = db_session.execute(select(CloudAccount)).scalars().first()
    _seed_commitments(db_session, seeded_tenant, account.id)

    r = client.get("/api/v1/commitments")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    assert body["items"][0]["service"] == "EC2"


def test_list_recommendations(client, seeded_tenant, db_session):
    from app.models.cloud_account import CloudAccount
    from sqlalchemy import select

    account = db_session.execute(select(CloudAccount)).scalars().first()
    _seed_recommendation(db_session, seeded_tenant, account.id)

    r = client.get("/api/v1/commitments/recommendations")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    assert body["items"][0]["title"] == "Increase Compute Savings Plan"
    assert body["totals"]["pending"] == 1
    assert body["totals"]["pending_savings"] == 310.0


def test_get_recommendation(client, seeded_tenant, db_session):
    from app.models.cloud_account import CloudAccount
    from sqlalchemy import select

    account = db_session.execute(select(CloudAccount)).scalars().first()
    rec = _seed_recommendation(db_session, seeded_tenant, account.id)

    r = client.get(f"/api/v1/commitments/recommendations/{rec.id}")
    assert r.status_code == 200
    assert r.json()["title"] == "Increase Compute Savings Plan"


def test_approve_recommendation(client, seeded_tenant, db_session):
    from app.models.cloud_account import CloudAccount
    from sqlalchemy import select

    account = db_session.execute(select(CloudAccount)).scalars().first()
    rec = _seed_recommendation(db_session, seeded_tenant, account.id)

    r = client.post(f"/api/v1/commitments/recommendations/{rec.id}/approve", json={})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "approved"
    assert len(body["history"]) == 1


def test_reject_requires_reason(client, seeded_tenant, db_session):
    from app.models.cloud_account import CloudAccount
    from sqlalchemy import select

    account = db_session.execute(select(CloudAccount)).scalars().first()
    rec = _seed_recommendation(db_session, seeded_tenant, account.id)

    r = client.post(f"/api/v1/commitments/recommendations/{rec.id}/reject", json={"reason": ""})
    assert r.status_code == 422


def test_defer_recommendation(client, seeded_tenant, db_session):
    from app.models.cloud_account import CloudAccount
    from sqlalchemy import select

    account = db_session.execute(select(CloudAccount)).scalars().first()
    rec = _seed_recommendation(db_session, seeded_tenant, account.id)

    r = client.post(f"/api/v1/commitments/recommendations/{rec.id}/defer", json={"reason": "waiting"})
    assert r.status_code == 200
    assert r.json()["status"] == "deferred"


def test_unknown_recommendation_404(client, seeded_tenant):
    r = client.get(f"/api/v1/commitments/recommendations/{uuid.uuid4()}")
    assert r.status_code == 404


def test_decide_non_pending_409(client, seeded_tenant, db_session):
    from app.models.cloud_account import CloudAccount
    from sqlalchemy import select

    account = db_session.execute(select(CloudAccount)).scalars().first()
    rec = _seed_recommendation(db_session, seeded_tenant, account.id)

    client.post(f"/api/v1/commitments/recommendations/{rec.id}/approve", json={})
    second = client.post(f"/api/v1/commitments/recommendations/{rec.id}/approve", json={})
    assert second.status_code == 409