"""chat messages and session metadata

Revision ID: 0006_chat_messages
Revises: 0005_execution_fields
Create Date: 2026-09-27

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006_chat_messages"
down_revision: Union[str, None] = "0005_execution_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "chat_sessions",
        sa.Column("message_count", sa.Integer(), nullable=False, server_default="0"),
    )

    op.create_table(
        "chat_messages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("content", sa.String(length=8000), nullable=False, server_default=""),
        sa.Column("response_payload", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("plan", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("tool_calls", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("source", sa.String(length=16), nullable=False, server_default="rules"),
        sa.Column("intent", sa.String(length=32), nullable=False, server_default="generic"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["chat_sessions.id"],
            name="fk_chat_messages_session_id_chat_sessions",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_chat_messages"),
    )
    op.create_index("ix_chat_messages_session_id", "chat_messages", ["session_id"])
    op.create_index("ix_chat_messages_role", "chat_messages", ["role"])
    op.create_index("ix_chat_messages_created_at", "chat_messages", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_chat_messages_created_at", table_name="chat_messages")
    op.drop_index("ix_chat_messages_role", table_name="chat_messages")
    op.drop_index("ix_chat_messages_session_id", table_name="chat_messages")
    op.drop_table("chat_messages")
    op.drop_column("chat_sessions", "message_count")