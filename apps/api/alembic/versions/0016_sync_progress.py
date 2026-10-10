"""cloud account sync progress

Revision ID: 0016_sync_progress
Revises: 0015_password_reset
Create Date: 2026-10-06

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0016_sync_progress"
down_revision: Union[str, None] = "0015_password_reset"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("cloud_accounts", sa.Column("sync_phase", sa.String(length=32), nullable=True))
    op.add_column("cloud_accounts", sa.Column("sync_progress_pct", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("cloud_accounts", sa.Column("sync_started_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("cloud_accounts", sa.Column("sync_completed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("cloud_accounts", sa.Column("sync_error_count", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("cloud_accounts", "sync_error_count")
    op.drop_column("cloud_accounts", "sync_completed_at")
    op.drop_column("cloud_accounts", "sync_started_at")
    op.drop_column("cloud_accounts", "sync_progress_pct")
    op.drop_column("cloud_accounts", "sync_phase")