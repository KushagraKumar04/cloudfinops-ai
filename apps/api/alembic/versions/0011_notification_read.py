"""notification read_at

Revision ID: 0011_notification_read
Revises: 0010_notifications
Create Date: 2026-10-04

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0011_notification_read"
down_revision: Union[str, None] = "0010_notifications"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None
