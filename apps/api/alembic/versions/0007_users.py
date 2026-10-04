"""users and team members

Revision ID: 0007_users
Revises: 0006_chat_messages
Create Date: 2026-10-03

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0007_users"
down_revision: Union[str, None] = "0006_chat_messages"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_superuser", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "team_members",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(length=24), nullable=False, server_default="owner"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_team_members_user_id_users", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_team_members_tenant_id_tenants", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_team_members"),
        sa.UniqueConstraint("user_id", "tenant_id", name="uq_team_members_user_tenant"),
    )
    op.create_index("ix_team_members_user_id", "team_members", ["user_id"])
    op.create_index("ix_team_members_tenant_id", "team_members", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_team_members_tenant_id", table_name="team_members")
    op.drop_index("ix_team_members_user_id", table_name="team_members")
    op.drop_table("team_members")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")