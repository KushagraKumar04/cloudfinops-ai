"""canonical domain model

Revision ID: 0002_canonical
Revises: 0001_initial
Create Date: 2026-09-24

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_canonical"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "resources",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("cloud_account_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=16), nullable=False),
        sa.Column("cloud_id", sa.String(length=500), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("type", sa.String(length=120), nullable=False),
        sa.Column("service", sa.String(length=64), nullable=False),
        sa.Column("region", sa.String(length=64), nullable=False),
        sa.Column("environment", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("application", sa.String(length=120), nullable=False, server_default="unknown"),
        sa.Column("owner", sa.String(length=120), nullable=False, server_default="unassigned"),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("utilization", sa.JSON(), nullable=False),
        sa.Column("series", sa.JSON(), nullable=False),
        sa.Column("metric_coverage", sa.Numeric(precision=4, scale=3), nullable=False, server_default="0"),
        sa.Column("monthly_cost", sa.Numeric(precision=18, scale=2), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="USD"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_resources_tenant_id_tenants", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["cloud_account_id"], ["cloud_accounts.id"], name="fk_resources_cloud_account_id_cloud_accounts", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_resources"),
    )
    op.create_index("ix_resources_tenant_id", "resources", ["tenant_id"])
    op.create_index("ix_resources_cloud_account_id", "resources", ["cloud_account_id"])
    op.create_index("ix_resources_provider", "resources", ["provider"])
    op.create_index("ix_resources_cloud_id", "resources", ["cloud_id"])
    op.create_index("ix_resources_service", "resources", ["service"])
    op.create_index("ix_resources_region", "resources", ["region"])
    op.create_index("ix_resources_environment", "resources", ["environment"])
    op.create_index("ix_resources_status", "resources", ["status"])

    op.create_table(
        "cost_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("cloud_account_id", sa.Uuid(), nullable=False),
        sa.Column("resource_id", sa.Uuid(), nullable=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("provider", sa.String(length=16), nullable=False),
        sa.Column("service", sa.String(length=64), nullable=False),
        sa.Column("region", sa.String(length=64), nullable=False),
        sa.Column("cost", sa.Numeric(precision=18, scale=4), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="USD"),
        sa.Column("usage_quantity", sa.Numeric(precision=18, scale=4), nullable=False, server_default="0"),
        sa.Column("usage_unit", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_cost_records_tenant_id_tenants", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["cloud_account_id"], ["cloud_accounts.id"], name="fk_cost_records_cloud_account_id_cloud_accounts", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["resource_id"], ["resources.id"], name="fk_cost_records_resource_id_resources", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_cost_records"),
    )
    op.create_index("ix_cost_records_tenant_id", "cost_records", ["tenant_id"])
    op.create_index("ix_cost_records_cloud_account_id", "cost_records", ["cloud_account_id"])
    op.create_index("ix_cost_records_resource_id", "cost_records", ["resource_id"])
    op.create_index("ix_cost_records_date", "cost_records", ["date"])
    op.create_index("ix_cost_records_provider", "cost_records", ["provider"])
    op.create_index("ix_cost_records_service", "cost_records", ["service"])
    op.create_index("ix_cost_records_region", "cost_records", ["region"])

    op.create_table(
        "metric_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("resource_id", sa.Uuid(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metric_name", sa.String(length=64), nullable=False),
        sa.Column("metric_value", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("unit", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_metric_records_tenant_id_tenants", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["resource_id"], ["resources.id"], name="fk_metric_records_resource_id_resources", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_metric_records"),
    )
    op.create_index("ix_metric_records_tenant_id", "metric_records", ["tenant_id"])
    op.create_index("ix_metric_records_resource_id", "metric_records", ["resource_id"])
    op.create_index("ix_metric_records_timestamp", "metric_records", ["timestamp"])
    op.create_index("ix_metric_records_metric_name", "metric_records", ["metric_name"])

    op.create_table(
        "price_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=16), nullable=False),
        sa.Column("resource_type", sa.String(length=120), nullable=False),
        sa.Column("region", sa.String(length=64), nullable=False),
        sa.Column("price", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("unit", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="USD"),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_price_records"),
    )
    op.create_index("ix_price_records_provider", "price_records", ["provider"])
    op.create_index("ix_price_records_resource_type", "price_records", ["resource_type"])
    op.create_index("ix_price_records_region", "price_records", ["region"])

    op.create_table(
        "budgets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="USD"),
        sa.Column("period", sa.String(length=16), nullable=False, server_default="monthly"),
        sa.Column("scope", sa.String(length=32), nullable=False, server_default="all"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_budgets_tenant_id_tenants", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_budgets"),
    )
    op.create_index("ix_budgets_tenant_id", "budgets", ["tenant_id"])

    op.create_table(
        "anomalies",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("cloud_account_id", sa.Uuid(), nullable=False),
        sa.Column("resource_id", sa.Uuid(), nullable=True),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("provider", sa.String(length=16), nullable=False),
        sa.Column("service", sa.String(length=64), nullable=False),
        sa.Column("delta_pct", sa.Numeric(precision=8, scale=2), nullable=False),
        sa.Column("delta_amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("baseline_value", sa.Numeric(precision=18, scale=2), nullable=False, server_default="0"),
        sa.Column("observed_value", sa.Numeric(precision=18, scale=2), nullable=False, server_default="0"),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_anomalies_tenant_id_tenants", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["cloud_account_id"], ["cloud_accounts.id"], name="fk_anomalies_cloud_account_id_cloud_accounts", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["resource_id"], ["resources.id"], name="fk_anomalies_resource_id_resources", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_anomalies"),
    )
    op.create_index("ix_anomalies_tenant_id", "anomalies", ["tenant_id"])
    op.create_index("ix_anomalies_cloud_account_id", "anomalies", ["cloud_account_id"])
    op.create_index("ix_anomalies_resource_id", "anomalies", ["resource_id"])
    op.create_index("ix_anomalies_detected_at", "anomalies", ["detected_at"])
    op.create_index("ix_anomalies_provider", "anomalies", ["provider"])
    op.create_index("ix_anomalies_service", "anomalies", ["service"])
    op.create_index("ix_anomalies_severity", "anomalies", ["severity"])

    op.create_table(
        "recommendations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("resource_id", sa.Uuid(), nullable=False),
        sa.Column("type", sa.String(length=64), nullable=False),
        sa.Column("type_label", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("summary", sa.String(length=1000), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("risk", sa.String(length=16), nullable=False),
        sa.Column("risk_reasons", sa.JSON(), nullable=False),
        sa.Column("confidence", sa.Numeric(precision=4, scale=3), nullable=False),
        sa.Column("current_monthly_cost", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("estimated_monthly_cost", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("estimated_monthly_savings", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="USD"),
        sa.Column("calculation_basis", sa.JSON(), nullable=False),
        sa.Column("current_state", sa.JSON(), nullable=False),
        sa.Column("proposed_state", sa.JSON(), nullable=False),
        sa.Column("impact", sa.JSON(), nullable=False),
        sa.Column("implementation_plan", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_recommendations_tenant_id_tenants", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["resource_id"], ["resources.id"], name="fk_recommendations_resource_id_resources", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_recommendations"),
    )
    op.create_index("ix_recommendations_tenant_id", "recommendations", ["tenant_id"])
    op.create_index("ix_recommendations_resource_id", "recommendations", ["resource_id"])
    op.create_index("ix_recommendations_type", "recommendations", ["type"])
    op.create_index("ix_recommendations_status", "recommendations", ["status"])
    op.create_index("ix_recommendations_risk", "recommendations", ["risk"])
    op.create_index("ix_recommendations_savings", "recommendations", ["estimated_monthly_savings"])
    op.create_index("ix_recommendations_created_at", "recommendations", ["created_at"])

    op.create_table(
        "recommendation_evidence",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("recommendation_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.Column("value", sa.String(length=200), nullable=False),
        sa.Column("source", sa.String(length=120), nullable=False),
        sa.ForeignKeyConstraint(["recommendation_id"], ["recommendations.id"], name="fk_recommendation_evidence_recommendation_id_recommendations", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_recommendation_evidence"),
    )
    op.create_index("ix_recommendation_evidence_recommendation_id", "recommendation_evidence", ["recommendation_id"])

    op.create_table(
        "approvals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("recommendation_id", sa.Uuid(), nullable=False),
        sa.Column("approver", sa.String(length=200), nullable=False),
        sa.Column("decision", sa.String(length=16), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["recommendation_id"], ["recommendations.id"], name="fk_approvals_recommendation_id_recommendations", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_approvals"),
    )
    op.create_index("ix_approvals_recommendation_id", "approvals", ["recommendation_id"])

    op.create_table(
        "executions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("recommendation_id", sa.Uuid(), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("idempotency_key", sa.String(length=200), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("result", sa.JSON(), nullable=False),
        sa.Column("rollback_reference", sa.String(length=300), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["recommendation_id"], ["recommendations.id"], name="fk_executions_recommendation_id_recommendations", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_executions"),
        sa.UniqueConstraint("idempotency_key", name="uq_executions_idempotency_key"),
    )
    op.create_index("ix_executions_recommendation_id", "executions", ["recommendation_id"])
    op.create_index("ix_executions_status", "executions", ["status"])
    op.create_index("ix_executions_idempotency_key", "executions", ["idempotency_key"])

    op.create_table(
        "audit_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("actor", sa.String(length=200), nullable=False),
        sa.Column("action", sa.String(length=200), nullable=False),
        sa.Column("subject", sa.String(length=300), nullable=False),
        sa.Column("details", sa.String(length=1000), nullable=False),
        sa.Column("event_metadata", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_audit_events_tenant_id_tenants", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_audit_events"),
    )
    op.create_index("ix_audit_events_tenant_id", "audit_events", ["tenant_id"])
    op.create_index("ix_audit_events_at", "audit_events", ["at"])
    op.create_index("ix_audit_events_category", "audit_events", ["category"])
    op.create_index("ix_audit_events_severity", "audit_events", ["severity"])

    op.create_table(
        "chat_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False, server_default="New conversation"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_chat_sessions_tenant_id_tenants", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_chat_sessions"),
    )
    op.create_index("ix_chat_sessions_tenant_id", "chat_sessions", ["tenant_id"])

    op.create_table(
        "agent_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=True),
        sa.Column("user_message", sa.String(length=2000), nullable=False),
        sa.Column("plan", sa.JSON(), nullable=False),
        sa.Column("response", sa.JSON(), nullable=False),
        sa.Column("model", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("estimated_cost", sa.Numeric(precision=10, scale=6), nullable=False, server_default="0"),
        sa.Column("latency_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["chat_sessions.id"], name="fk_agent_runs_session_id_chat_sessions", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_agent_runs"),
    )
    op.create_index("ix_agent_runs_session_id", "agent_runs", ["session_id"])

    op.create_table(
        "tool_calls",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("agent_run_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("args", sa.JSON(), nullable=False),
        sa.Column("result_summary", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("duration_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["agent_run_id"], ["agent_runs.id"], name="fk_tool_calls_agent_run_id_agent_runs", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_tool_calls"),
    )
    op.create_index("ix_tool_calls_agent_run_id", "tool_calls", ["agent_run_id"])
    op.create_index("ix_tool_calls_name", "tool_calls", ["name"])


def downgrade() -> None:
    op.drop_index("ix_tool_calls_name", table_name="tool_calls")
    op.drop_index("ix_tool_calls_agent_run_id", table_name="tool_calls")
    op.drop_table("tool_calls")

    op.drop_index("ix_agent_runs_session_id", table_name="agent_runs")
    op.drop_table("agent_runs")

    op.drop_index("ix_chat_sessions_tenant_id", table_name="chat_sessions")
    op.drop_table("chat_sessions")

    op.drop_index("ix_audit_events_severity", table_name="audit_events")
    op.drop_index("ix_audit_events_category", table_name="audit_events")
    op.drop_index("ix_audit_events_at", table_name="audit_events")
    op.drop_index("ix_audit_events_tenant_id", table_name="audit_events")
    op.drop_table("audit_events")

    op.drop_index("ix_executions_idempotency_key", table_name="executions")
    op.drop_index("ix_executions_status", table_name="executions")
    op.drop_index("ix_executions_recommendation_id", table_name="executions")
    op.drop_table("executions")

    op.drop_index("ix_approvals_recommendation_id", table_name="approvals")
    op.drop_table("approvals")

    op.drop_index("ix_recommendation_evidence_recommendation_id", table_name="recommendation_evidence")
    op.drop_table("recommendation_evidence")

    op.drop_index("ix_recommendations_created_at", table_name="recommendations")
    op.drop_index("ix_recommendations_savings", table_name="recommendations")
    op.drop_index("ix_recommendations_risk", table_name="recommendations")
    op.drop_index("ix_recommendations_status", table_name="recommendations")
    op.drop_index("ix_recommendations_type", table_name="recommendations")
    op.drop_index("ix_recommendations_resource_id", table_name="recommendations")
    op.drop_index("ix_recommendations_tenant_id", table_name="recommendations")
    op.drop_table("recommendations")

    op.drop_index("ix_anomalies_severity", table_name="anomalies")
    op.drop_index("ix_anomalies_service", table_name="anomalies")
    op.drop_index("ix_anomalies_provider", table_name="anomalies")
    op.drop_index("ix_anomalies_detected_at", table_name="anomalies")
    op.drop_index("ix_anomalies_resource_id", table_name="anomalies")
    op.drop_index("ix_anomalies_cloud_account_id", table_name="anomalies")
    op.drop_index("ix_anomalies_tenant_id", table_name="anomalies")
    op.drop_table("anomalies")

    op.drop_index("ix_budgets_tenant_id", table_name="budgets")
    op.drop_table("budgets")

    op.drop_index("ix_price_records_region", table_name="price_records")
    op.drop_index("ix_price_records_resource_type", table_name="price_records")
    op.drop_index("ix_price_records_provider", table_name="price_records")
    op.drop_table("price_records")

    op.drop_index("ix_metric_records_metric_name", table_name="metric_records")
    op.drop_index("ix_metric_records_timestamp", table_name="metric_records")
    op.drop_index("ix_metric_records_resource_id", table_name="metric_records")
    op.drop_index("ix_metric_records_tenant_id", table_name="metric_records")
    op.drop_table("metric_records")

    op.drop_index("ix_cost_records_region", table_name="cost_records")
    op.drop_index("ix_cost_records_service", table_name="cost_records")
    op.drop_index("ix_cost_records_provider", table_name="cost_records")
    op.drop_index("ix_cost_records_date", table_name="cost_records")
    op.drop_index("ix_cost_records_resource_id", table_name="cost_records")
    op.drop_index("ix_cost_records_cloud_account_id", table_name="cost_records")
    op.drop_index("ix_cost_records_tenant_id", table_name="cost_records")
    op.drop_table("cost_records")

    op.drop_index("ix_resources_status", table_name="resources")
    op.drop_index("ix_resources_environment", table_name="resources")
    op.drop_index("ix_resources_region", table_name="resources")
    op.drop_index("ix_resources_service", table_name="resources")
    op.drop_index("ix_resources_cloud_id", table_name="resources")
    op.drop_index("ix_resources_provider", table_name="resources")
    op.drop_index("ix_resources_cloud_account_id", table_name="resources")
    op.drop_index("ix_resources_tenant_id", table_name="resources")
    op.drop_table("resources")