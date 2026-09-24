"""tenant settings json

Revision ID: 0003_tenant_settings
Revises: 0002_canonical
Create Date: 2026-09-24

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_tenant_settings"
down_revision: Union[str, None] = "0002_canonical"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tenants", sa.Column("settings", sa.JSON(), nullable=False, server_default="{}"))


def downgrade() -> None:
    op.drop_column("tenants", "settings")