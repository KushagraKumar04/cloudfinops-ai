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
