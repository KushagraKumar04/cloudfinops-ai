"""commitments and commitment recommendations

Revision ID: 0009_commitments
Revises: 0008_kubernetes
Create Date: 2026-10-04

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0009_commitments"
down_revision: Union[str, None] = "0008_kubernetes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "commitments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("cloud_account_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=16), nullable=False),
        sa.Column("commitment_type", sa.String(length=32), nullable=False),
        sa.Column("service", sa.String(length=64), nullable=False),
        sa.Column("region", sa.String(length=64), nullable=False),
        sa.Column("term_months", sa.Integer(), nullable=False, server_default="12"),
        sa.Column("payment_option", sa.String(length=24), nullable=False, server_default="no_upfront"),
        sa.Column("monthly_cost", sa.Numeric(precision=18, scale=2), nullable=False, server_default="0"),
        sa.Column("monthly_savings", sa.Numeric(precision=18, scale=2), nullable=False, server_default="0"),
        sa.Column("hourly_commitment", sa.Numeric(precision=18, scale=4), nullable=True),
        sa.Column("instance_count", sa.Integer(), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="active"),
        sa.Column("utilization_pct", sa.Numeric(precision=5, scale=4), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="USD"),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_commitments_tenant", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["cloud_account_id"], ["cloud_accounts.id"], name="fk_commitments_cloud_account", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_commitments"),
    )
    op.create_index("ix_commitments_tenant_id", "commitments", ["tenant_id"])
    op.create_index("ix_commitments_cloud_account_id", "commitments", ["cloud_account_id"])
    op.create_index("ix_commitments_provider", "commitments", ["provider"])
    op.create_index("ix_commitments_commitment_type", "commitments", ["commitment_type"])
    op.create_index("ix_commitments_service", "commitments", ["service"])
    op.create_index("ix_commitments_region", "commitments", ["region"])
    op.create_index("ix_commitments_start_date", "commitments", ["start_date"])
    op.create_index("ix_commitments_end_date", "commitments", ["end_date"])
    op.create_index("ix_commitments_status", "commitments", ["status"])

    op.create_table(
        "commitment_recommendations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("cloud_account_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=16), nullable=False),
        sa.Column("commitment_type", sa.String(length=32), nullable=False),
        sa.Column("service", sa.String(length=64), nullable=False),
        sa.Column("region", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("summary", sa.String(length=1000), nullable=False),
        sa.Column("rationale", sa.String(length=1000), nullable=False, server_default=""),
        sa.Column("term_months", sa.Integer(), nullable=False, server_default="12"),
        sa.Column("payment_option", sa.String(length=24), nullable=False, server_default="no_upfront"),
        sa.Column("recommended_hourly_commitment", sa.Numeric(precision=18, scale=4), nullable=True),
        sa.Column("recommended_instance_count", sa.Integer(), nullable=True),
        sa.Column("estimated_monthly_cost", sa.Numeric(precision=18, scale=2), nullable=False, server_default="0"),
        sa.Column("estimated_monthly_savings", sa.Numeric(precision=18, scale=2), nullable=False, server_default="0"),
        sa.Column("estimated_annual_savings", sa.Numeric(precision=18, scale=2), nullable=False, server_default="0"),
        sa.Column("coverage_before_pct", sa.Numeric(precision=5, scale=4), nullable=False, server_default="0"),
        sa.Column("coverage_after_pct", sa.Numeric(precision=5, scale=4), nullable=False, server_default="0"),
        sa.Column("break_even_months", sa.Numeric(precision=6, scale=2), nullable=False, server_default="0"),
        sa.Column("risk", sa.String(length=16), nullable=False, server_default="LOW"),
        sa.Column("risk_reasons", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("confidence", sa.Numeric(precision=4, scale=3), nullable=False, server_default="0.75"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("evidence", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("impact", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="USD"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_commitment_recs_tenant", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["cloud_account_id"], ["cloud_accounts.id"], name="fk_commitment_recs_cloud_account", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_commitment_recommendations"),
    )
    op.create_index("ix_commitment_recommendations_tenant_id", "commitment_recommendations", ["tenant_id"])
    op.create_index("ix_commitment_recommendations_cloud_account_id", "commitment_recommendations", ["cloud_account_id"])
    op.create_index("ix_commitment_recommendations_provider", "commitment_recommendations", ["provider"])
    op.create_index("ix_commitment_recommendations_commitment_type", "commitment_recommendations", ["commitment_type"])
    op.create_index("ix_commitment_recommendations_service", "commitment_recommendations", ["service"])
    op.create_index("ix_commitment_recommendations_region", "commitment_recommendations", ["region"])
    op.create_index("ix_commitment_recommendations_risk", "commitment_recommendations", ["risk"])
    op.create_index("ix_commitment_recommendations_status", "commitment_recommendations", ["status"])
    op.create_index("ix_commitment_recommendations_created_at", "commitment_recommendations", ["created_at"])

    op.create_table(
        "commitment_approvals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("recommendation_id", sa.Uuid(), nullable=False),
        sa.Column("approver", sa.String(length=200), nullable=False),
        sa.Column("decision", sa.String(length=16), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["recommendation_id"], ["commitment_recommendations.id"], name="fk_commitment_approvals_rec", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_commitment_approvals"),
    )
    op.create_index("ix_commitment_approvals_recommendation_id", "commitment_approvals", ["recommendation_id"])


def downgrade() -> None:
    op.drop_index("ix_commitment_approvals_recommendation_id", table_name="commitment_approvals")
    op.drop_table("commitment_approvals")

    op.drop_index("ix_commitment_recommendations_created_at", table_name="commitment_recommendations")
    op.drop_index("ix_commitment_recommendations_status", table_name="commitment_recommendations")
    op.drop_index("ix_commitment_recommendations_risk", table_name="commitment_recommendations")
    op.drop_index("ix_commitment_recommendations_region", table_name="commitment_recommendations")
    op.drop_index("ix_commitment_recommendations_service", table_name="commitment_recommendations")
    op.drop_index("ix_commitment_recommendations_commitment_type", table_name="commitment_recommendations")
    op.drop_index("ix_commitment_recommendations_provider", table_name="commitment_recommendations")
    op.drop_index("ix_commitment_recommendations_cloud_account_id", table_name="commitment_recommendations")
    op.drop_index("ix_commitment_recommendations_tenant_id", table_name="commitment_recommendations")
    op.drop_table("commitment_recommendations")

    op.drop_index("ix_commitments_status", table_name="commitments")
    op.drop_index("ix_commitments_end_date", table_name="commitments")
    op.drop_index("ix_commitments_start_date", table_name="commitments")
    op.drop_index("ix_commitments_region", table_name="commitments")
    op.drop_index("ix_commitments_service", table_name="commitments")
    op.drop_index("ix_commitments_commitment_type", table_name="commitments")
    op.drop_index("ix_commitments_provider", table_name="commitments")
    op.drop_index("ix_commitments_cloud_account_id", table_name="commitments")
    op.drop_index("ix_commitments_tenant_id", table_name="commitments")
    op.drop_table("commitments")