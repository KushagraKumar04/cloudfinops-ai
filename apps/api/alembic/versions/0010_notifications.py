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

