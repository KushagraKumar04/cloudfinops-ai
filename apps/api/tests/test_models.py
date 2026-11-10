import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from app.models.anomaly import Anomaly
from app.models.audit import AuditEvent
from app.models.budget import Budget
from app.models.chat import AgentRun, ChatSession, ToolCall
from app.models.cost import CostRecord
from app.models.execution import Approval, Execution
from app.models.metric import MetricRecord
from app.models.price import PriceRecord
from app.models.recommendation import Recommendation, RecommendationEvidence
from app.models.resource import Resource


def test_resource_persistence(db_session, seeded_tenant):
    from app.models.cloud_account import CloudAccount
    from sqlalchemy import select

    account = db_session.execute(select(CloudAccount)).scalars().first()
    resource = Resource(
        tenant_id=seeded_tenant.id,
        cloud_account_id=account.id,
        provider="AWS",
        cloud_id="i-test",
        name="test-instance",
        type="EC2 m5.large",
        service="EC2",
        region="us-east-1",
        environment="production",
        status="running",
        application="test",
        owner="tester",
        tags=[{"key": "env", "value": "prod"}],
        utilization={"cpu": 10},
        series={"cpu": [10, 12, 11]},
        metric_coverage=Decimal("0.95"),
        monthly_cost=Decimal("100"),
    )
    db_session.add(resource)
    db_session.commit()

    fetched = db_session.execute(select(Resource).where(Resource.name == "test-instance")).scalar_one()
    assert fetched.provider == "AWS"
    assert float(fetched.monthly_cost) == 100.0
    assert fetched.tags[0]["key"] == "env"


def test_cost_record_persistence(db_session, seeded_tenant):
    from app.models.cloud_account import CloudAccount
    from sqlalchemy import select

    account = db_session.execute(select(CloudAccount)).scalars().first()
    record = CostRecord(
        tenant_id=seeded_tenant.id,
        cloud_account_id=account.id,
        date=date.today(),
        provider="AWS",
        service="EC2",
        region="us-east-1",
        cost=Decimal("19.33"),
        currency="USD",
        usage_quantity=Decimal("1"),
        usage_unit="day",
        tags={},
    )
    db_session.add(record)
    db_session.commit()

    fetched = db_session.execute(select(CostRecord)).scalar_one()
    assert float(fetched.cost) == 19.33


def test_recommendation_with_evidence(db_session, seeded_tenant):
    from app.models.cloud_account import CloudAccount
    from sqlalchemy import select

    account = db_session.execute(select(CloudAccount)).scalars().first()
    resource = Resource(
        tenant_id=seeded_tenant.id,
        cloud_account_id=account.id,
        provider="AWS",
        cloud_id="i-rec-test",
        name="rec-test",
        type="EC2 m5.large",
        service="EC2",
        region="us-east-1",
        environment="production",
        status="running",
    )
    db_session.add(resource)
    db_session.flush()

    rec = Recommendation(
        tenant_id=seeded_tenant.id,
        resource_id=resource.id,
        type="compute.rightsizing",
        type_label="Compute rightsizing",
        title="Test recommendation",
        summary="A summary",
        status="pending",
        risk="LOW",
        risk_reasons=["Test reason"],
        confidence=Decimal("0.9"),
        current_monthly_cost=Decimal("100"),
        estimated_monthly_cost=Decimal("50"),
        estimated_monthly_savings=Decimal("50"),
        calculation_basis=["basis 1"],
        current_state=[{"key": "a", "value": "1"}],
        proposed_state=[{"key": "a", "value": "2"}],
        impact={"availability": "none"},
        implementation_plan=["step 1", "step 2"],
    )
    db_session.add(rec)
    db_session.flush()

    db_session.add(
        RecommendationEvidence(
            recommendation_id=rec.id,
            position=0,
            label="Avg CPU",
            value="12%",
            source="CloudWatch",
        )
    )
    db_session.commit()

    fetched = db_session.execute(select(Recommendation)).scalar_one()
    assert len(fetched.evidence) == 1
    assert fetched.evidence[0].label == "Avg CPU"


def test_execution_idempotency_key_unique(db_session, seeded_tenant):
    from app.models.cloud_account import CloudAccount
    from sqlalchemy import select
    import pytest
    from sqlalchemy.exc import IntegrityError

    account = db_session.execute(select(CloudAccount)).scalars().first()
    resource = Resource(
        tenant_id=seeded_tenant.id,
        cloud_account_id=account.id,
        provider="AWS",
        cloud_id="i-exec-test",
        name="exec-test",
        type="EC2 m5.large",
        service="EC2",
        region="us-east-1",
        environment="production",
        status="running",
    )
    db_session.add(resource)
    db_session.flush()

    rec = Recommendation(
        tenant_id=seeded_tenant.id,
        resource_id=resource.id,
        type="storage.unattached",
        type_label="Unattached storage",
        title="T",
        summary="S",
        status="approved",
        risk="LOW",
        risk_reasons=[],
        confidence=Decimal("1"),
        current_monthly_cost=Decimal("10"),
        estimated_monthly_cost=Decimal("0"),
        estimated_monthly_savings=Decimal("10"),
        calculation_basis=[],
        current_state=[],
        proposed_state=[],
        impact={},
        implementation_plan=[],
    )
    db_session.add(rec)
    db_session.flush()

    db_session.add(
        Execution(
            tenant_id=seeded_tenant.id,
            recommendation_id=rec.id,
            action="delete",
            status="pending",
            idempotency_key="execution:test:1",
            result={},
        )
    )
    db_session.commit()

    db_session.add(
        Execution(
            tenant_id=seeded_tenant.id,
            recommendation_id=rec.id,
            action="delete",
            status="pending",
            idempotency_key="execution:test:1",
            result={},
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_audit_event_persistence(db_session, seeded_tenant):
    event = AuditEvent(
        tenant_id=seeded_tenant.id,
        at=datetime.now(UTC),
        category="recommendation",
        severity="info",
        actor="tester",
        action="Tested",
        subject="test",
        details="Testing audit",
        event_metadata=[{"key": "k", "value": "v"}],
    )
    db_session.add(event)
    db_session.commit()
    assert event.id is not None


def test_agent_run_and_tool_calls(db_session, seeded_tenant):
    from sqlalchemy import select

    session = ChatSession(tenant_id=seeded_tenant.id, title="Test chat")
    db_session.add(session)
    db_session.flush()

    run = AgentRun(
        session_id=session.id,
        user_message="Why did cost increase?",
        plan=["step 1"],
        response={"answer": "test"},
        model="gpt-4o-mini",
        input_tokens=100,
        output_tokens=50,
        estimated_cost=Decimal("0.001"),
        latency_ms=1200,
    )
    db_session.add(run)
    db_session.flush()

    db_session.add(
        ToolCall(
            agent_run_id=run.id,
            name="get_cost_summary",
            args={"range": "7d"},
            result_summary="$32k",
            duration_ms=180,
        )
    )
    db_session.commit()

    fetched = db_session.execute(select(AgentRun)).scalar_one()
    assert fetched.user_message == "Why did cost increase?"


def test_metric_and_price_records(db_session, seeded_tenant):
    from app.models.cloud_account import CloudAccount
    from sqlalchemy import select

    account = db_session.execute(select(CloudAccount)).scalars().first()
    resource = Resource(
        tenant_id=seeded_tenant.id,
        cloud_account_id=account.id,
        provider="AWS",
        cloud_id="i-metric-test",
        name="metric-test",
        type="EC2 m5.large",
        service="EC2",
        region="us-east-1",
        environment="production",
        status="running",
    )
    db_session.add(resource)
    db_session.flush()

    db_session.add(
        MetricRecord(
            tenant_id=seeded_tenant.id,
            resource_id=resource.id,
            timestamp=datetime.now(UTC),
            metric_name="cpu",
            metric_value=Decimal("12.5"),
            unit="percent",
        )
    )
    db_session.add(
        PriceRecord(
            provider="AWS",
            resource_type="m5.large",
            region="us-east-1",
            price=Decimal("0.096"),
            unit="hour",
            effective_from=date.today(),
        )
    )
    db_session.commit()

    assert db_session.execute(select(MetricRecord)).scalar_one().metric_name == "cpu"
    assert float(db_session.execute(select(PriceRecord)).scalar_one().price) == 0.096


def test_anomaly_and_budget(db_session, seeded_tenant):
    from app.models.cloud_account import CloudAccount
    from sqlalchemy import select

    account = db_session.execute(select(CloudAccount)).scalars().first()
    db_session.add(
        Anomaly(
            tenant_id=seeded_tenant.id,
            cloud_account_id=account.id,
            detected_at=datetime.now(UTC),
            provider="AWS",
            service="EC2",
            delta_pct=Decimal("42"),
            delta_amount=Decimal("3820"),
            baseline_value=Decimal("9100"),
            observed_value=Decimal("12920"),
            description="Test",
            severity="high",
        )
    )
    db_session.add(
        Budget(
            tenant_id=seeded_tenant.id,
            name="Test budget",
            amount=Decimal("10000"),
            currency="USD",
            period="monthly",
            scope="all",
        )
    )
    db_session.commit()

    assert db_session.execute(select(Anomaly)).scalar_one().severity == "high"
    assert float(db_session.execute(select(Budget)).scalar_one().amount) == 10000.0


def test_approval_linked_to_recommendation(db_session, seeded_tenant):
    from app.models.cloud_account import CloudAccount
    from sqlalchemy import select

    account = db_session.execute(select(CloudAccount)).scalars().first()
    resource = Resource(
        tenant_id=seeded_tenant.id,
        cloud_account_id=account.id,
        provider="AWS",
        cloud_id="i-appr-test",
        name="appr-test",
        type="EC2 m5.large",
        service="EC2",
        region="us-east-1",
        environment="production",
        status="running",
    )
    db_session.add(resource)
    db_session.flush()

    rec = Recommendation(
        tenant_id=seeded_tenant.id,
        resource_id=resource.id,
        type="storage.unattached",
        type_label="Unattached storage",
        title="T",
        summary="S",
        status="pending",
        risk="LOW",
        risk_reasons=[],
        confidence=Decimal("1"),
        current_monthly_cost=Decimal("10"),
        estimated_monthly_cost=Decimal("0"),
        estimated_monthly_savings=Decimal("10"),
        calculation_basis=[],
        current_state=[],
        proposed_state=[],
        impact={},
        implementation_plan=[],
    )
    db_session.add(rec)
    db_session.flush()

    db_session.add(
        Approval(
            recommendation_id=rec.id,
            approver="tester@acme.io",
            decision="approve",
            reason="looks good",
        )
    )
    db_session.commit()

    fetched = db_session.execute(select(Recommendation)).scalar_one()
    assert len(fetched.approvals) == 1
    assert fetched.approvals[0].decision == "approve"