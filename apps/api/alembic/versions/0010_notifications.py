"""notifications and rules

Revision ID: 0010_notifications
Revises: 0009_commitments
Create Date: 2026-10-04

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0010_notifications"
down_revision: Union[str, None] = "0009_commitments"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "notification_rules",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("channel", sa.String(length=16), nullable=False),
        sa.Column("destination", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("min_severity", sa.String(length=16), nullable=False, server_default="info"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_fired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fire_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_notification_rules_tenant", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_notification_rules"),
        sa.UniqueConstraint("tenant_id", "name", name="uq_notification_rule_tenant_name"),
    )
    op.create_index("ix_notification_rules_tenant_id", "notification_rules", ["tenant_id"])
    op.create_index("ix_notification_rules_event_type", "notification_rules", ["event_type"])
    op.create_index("ix_notification_rules_channel", "notification_rules", ["channel"])
    op.create_index("ix_notification_rules_enabled", "notification_rules", ["enabled"])

    op.create_table(
        "notifications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("rule_id", sa.Uuid(), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("channel", sa.String(length=16), nullable=False),
        sa.Column("subject", sa.String(length=300), nullable=False),
        sa.Column("body", sa.String(length=4000), nullable=False, server_default=""),
        sa.Column("destination", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("event_metadata", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("error", sa.String(length=500), nullable=True),
        sa.Column("attempt", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("duration_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_notifications_tenant", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["rule_id"], ["notification_rules.id"], name="fk_notifications_rule", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_notifications"),
    )
    op.create_index("ix_notifications_tenant_id", "notifications", ["tenant_id"])
    op.create_index("ix_notifications_rule_id", "notifications", ["rule_id"])
    op.create_index("ix_notifications_event_type", "notifications", ["event_type"])
    op.create_index("ix_notifications_severity", "notifications", ["severity"])
    op.create_index("ix_notifications_channel", "notifications", ["channel"])
    op.create_index("ix_notifications_status", "notifications", ["status"])
    op.create_index("ix_notifications_created_at", "notifications", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_notifications_created_at", table_name="notifications")
    op.drop_index("ix_notifications_status", table_name="notifications")
    op.drop_index("ix_notifications_channel", table_name="notifications")
    op.drop_index("ix_notifications_severity", table_name="notifications")
    op.drop_index("ix_notifications_event_type", table_name="notifications")
    op.drop_index("ix_notifications_rule_id", table_name="notifications")
    op.drop_index("ix_notifications_tenant_id", table_name="notifications")
    op.drop_table("notifications")

    op.drop_index("ix_notification_rules_enabled", table_name="notification_rules")
    op.drop_index("ix_notification_rules_channel", table_name="notification_rules")
    op.drop_index("ix_notification_rules_event_type", table_name="notification_rules")
    op.drop_index("ix_notification_rules_tenant_id", table_name="notification_rules")
    op.drop_table("notification_rules")