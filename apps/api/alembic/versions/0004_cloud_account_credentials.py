"""cloud account credential fields

Revision ID: 0004_credentials
Revises: 0003_tenant_settings
Create Date: 2026-09-24

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004_credentials"
down_revision: Union[str, None] = "0003_tenant_settings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("cloud_accounts", sa.Column("external_id", sa.String(length=128), nullable=True))
    op.add_column("cloud_accounts", sa.Column("client_id", sa.String(length=128), nullable=True))
    op.add_column("cloud_accounts", sa.Column("encrypted_client_secret", sa.String(length=1024), nullable=True))
    op.add_column(
        "cloud_accounts",
        sa.Column("connection_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("cloud_accounts", sa.Column("connection_error", sa.String(length=500), nullable=True))
    op.create_index("ix_cloud_accounts_external_id", "cloud_accounts", ["external_id"])


def downgrade() -> None:
    op.drop_index("ix_cloud_accounts_external_id", table_name="cloud_accounts")
    op.drop_column("cloud_accounts", "connection_error")
    op.drop_column("cloud_accounts", "connection_verified")
    op.drop_column("cloud_accounts", "encrypted_client_secret")
    op.drop_column("cloud_accounts", "client_id")
    op.drop_column("cloud_accounts", "external_id")