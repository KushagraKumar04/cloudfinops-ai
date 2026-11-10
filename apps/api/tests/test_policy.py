from decimal import Decimal

from app.models.recommendation import Recommendation
from app.models.resource import Resource
from app.services.policy import ACTION_MAP, evaluate


def _make_rec(db_session, tenant, account_id, *, status="approved", risk="MEDIUM", rec_type="compute.rightsizing", environment="production"):
    resource = Resource(
        tenant_id=tenant.id,
        cloud_account_id=account_id,
        provider="AWS",
        cloud_id="i-policy-test",
        name="policy-test",
        type="EC2 m5.4xlarge",
        service="EC2",
        region="us-east-1",
        environment=environment,
        status="running",
        metric_coverage=Decimal("0.95"),
        monthly_cost=Decimal("100"),
    )
    db_session.add(resource)
    db_session.flush()

    rec = Recommendation(
        tenant_id=tenant.id,
        resource_id=resource.id,
        type=rec_type,
        type_label="Test",
        title="Test recommendation",
        summary="Summary",
        status=status,
        risk=risk,
        risk_reasons=[],
        confidence=Decimal("0.9"),
        current_monthly_cost=Decimal("100"),
        estimated_monthly_cost=Decimal("50"),
        estimated_monthly_savings=Decimal("50"),
        calculation_basis=["basis"],
        current_state=[{"key": "a", "value": "1"}],
        proposed_state=[{"key": "a", "value": "2"}],
        impact={},
        implementation_plan=["step"],
    )
    db_session.add(rec)
    db_session.flush()
    return rec, resource


def test_action_map_known_types():
    assert ACTION_MAP["compute.rightsizing"] == "resize_instance"
    assert ACTION_MAP["storage.unattached"] == "delete_volume"
    assert ACTION_MAP["network.unused_eip"] == "release_eip"


def test_blocked_recommendation(client, seeded_tenant, db_session):
    from app.models.cloud_account import CloudAccount
    from sqlalchemy import select

    account = db_session.execute(select(CloudAccount)).scalars().first()
    rec, resource = _make_rec(db_session, seeded_tenant, account.id, risk="BLOCKED")

    decision = evaluate(db_session, seeded_tenant, rec, resource)
    assert decision.allowed is False
    assert any("BLOCKED" in r for r in decision.reasons)


def test_unapproved_recommendation_blocked(client, seeded_tenant, db_session):
    from app.models.cloud_account import CloudAccount
    from sqlalchemy import select

    account = db_session.execute(select(CloudAccount)).scalars().first()
    rec, resource = _make_rec(db_session, seeded_tenant, account.id, status="pending")

    decision = evaluate(db_session, seeded_tenant, rec, resource)
    assert decision.allowed is False
    assert any("approved" in r for r in decision.reasons)