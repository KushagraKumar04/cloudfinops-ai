"""execution detail fields

Revision ID: 0005_execution_fields
Revises: 0004_credentials
Create Date: 2026-09-27

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005_execution_fields"
down_revision: Union[str, None] = "0004_credentials"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("executions", sa.Column("tenant_id", sa.Uuid(), nullable=True))
    op.add_column("executions", sa.Column("mode", sa.String(length=16), nullable=False, server_default="dry_run"))
    op.add_column("executions", sa.Column("executed_by", sa.String(length=200), nullable=False, server_default=""))
    op.add_column("executions", sa.Column("policy_result", sa.JSON(), nullable=False, server_default="{}"))
    op.add_column("executions", sa.Column("preconditions", sa.JSON(), nullable=False, server_default="[]"))
    op.add_column("executions", sa.Column("dry_run_result", sa.JSON(), nullable=False, server_default="{}"))
    op.add_column("executions", sa.Column("verification", sa.JSON(), nullable=False, server_default="{}"))
    op.add_column("executions", sa.Column("rollback_status", sa.String(length=24), nullable=True))
    op.add_column("executions", sa.Column("rollback_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_executions_tenant_id", "executions", ["tenant_id"])
    op.create_foreign_key(
        "fk_executions_tenant_id_tenants",
        "executions",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("fk_executions_tenant_id_tenants", "executions", type_="foreignkey")
    op.drop_index("ix_executions_tenant_id", table_name="executions")
    op.drop_column("executions", "rollback_at")
    op.drop_column("executions", "rollback_status")
    op.drop_column("executions", "verification")
    op.drop_column("executions", "dry_run_result")
    op.drop_column("executions", "preconditions")
    op.drop_column("executions", "policy_result")
    op.drop_column("executions", "executed_by")
    op.drop_column("executions", "mode")
    op.drop_column("executions", "tenant_id")