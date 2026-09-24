"""initial tenants and cloud_accounts

Revision ID: 0001_initial
Revises:
Create Date: 2026-09-24

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_tenants"),
        sa.UniqueConstraint("slug", name="uq_tenants_slug"),
    )
    op.create_index("ix_tenants_slug", "tenants", ["slug"])

    op.create_table(
        "cloud_accounts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=16), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("account_identifier", sa.String(length=120), nullable=False),
        sa.Column("environment", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="connected"),
        sa.Column("role_arn", sa.String(length=255), nullable=True),
        sa.Column("subscription_id", sa.String(length=120), nullable=True),
        sa.Column("tenant_external_id", sa.String(length=180), nullable=True),
        sa.Column("regions", sa.JSON(), nullable=False),
        sa.Column("read_only", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("execution_role_configured", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_sync_status", sa.String(length=16), nullable=True),
        sa.Column("last_sync_message", sa.String(length=500), nullable=True),
        sa.Column("coverage", sa.JSON(), nullable=False),
        sa.Column("resource_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("monthly_spend", sa.Numeric(precision=18, scale=2), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="USD"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_cloud_accounts_tenant_id_tenants", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_cloud_accounts"),
    )
    op.create_index("ix_cloud_accounts_tenant_id", "cloud_accounts", ["tenant_id"])
    op.create_index("ix_cloud_accounts_provider", "cloud_accounts", ["provider"])
    op.create_index("ix_cloud_accounts_environment", "cloud_accounts", ["environment"])


def downgrade() -> None:
    op.drop_index("ix_cloud_accounts_environment", table_name="cloud_accounts")
    op.drop_index("ix_cloud_accounts_provider", table_name="cloud_accounts")
    op.drop_index("ix_cloud_accounts_tenant_id", table_name="cloud_accounts")
    op.drop_table("cloud_accounts")
    op.drop_index("ix_tenants_slug", table_name="tenants")
    op.drop_table("tenants")