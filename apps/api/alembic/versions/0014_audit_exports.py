"""audit exports

Revision ID: 0014_audit_exports
Revises: 0013_cloud_account_disable
Create Date: 2026-10-05

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0014_audit_exports"
down_revision: Union[str, None] = "0013_cloud_account_disable"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "audit_exports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("requested_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("format", sa.String(length=16), nullable=False),
        sa.Column("storage_backend", sa.String(length=16), nullable=False),
        sa.Column("object_key", sa.String(length=600), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("record_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("filters", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="pending"),
        sa.Column("error", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_audit_exports_tenant", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["users.id"], name="fk_audit_exports_user", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_audit_exports"),
    )
    op.create_index("ix_audit_exports_tenant_id", "audit_exports", ["tenant_id"])
    op.create_index("ix_audit_exports_format", "audit_exports", ["format"])
    op.create_index("ix_audit_exports_storage_backend", "audit_exports", ["storage_backend"])
    op.create_index("ix_audit_exports_status", "audit_exports", ["status"])
    op.create_index("ix_audit_exports_created_at", "audit_exports", ["created_at"])
    op.create_index("ix_audit_exports_expires_at", "audit_exports", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_audit_exports_expires_at", table_name="audit_exports")
    op.drop_index("ix_audit_exports_created_at", table_name="audit_exports")
    op.drop_index("ix_audit_exports_status", table_name="audit_exports")
    op.drop_index("ix_audit_exports_storage_backend", table_name="audit_exports")
    op.drop_index("ix_audit_exports_format", table_name="audit_exports")
    op.drop_index("ix_audit_exports_tenant_id", table_name="audit_exports")
    op.drop_table("audit_exports")