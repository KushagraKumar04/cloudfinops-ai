"""cloud account disabled_at

Revision ID: 0013_cloud_account_disable
Revises: 0012_invitations
Create Date: 2026-10-05

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0013_cloud_account_disable"
down_revision: Union[str, None] = "0012_invitations"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "cloud_accounts",
        sa.Column("disabled_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("cloud_accounts", "disabled_at")