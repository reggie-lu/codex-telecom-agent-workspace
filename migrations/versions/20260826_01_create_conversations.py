"""Create synthetic customers and conversations.

Revision ID: 20260826_01
Revises:
Create Date: 2026-08-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260826_01"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "synthetic_customers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_synthetic_customers"),
        sa.UniqueConstraint("token_hash", name="uq_synthetic_customers_token_hash"),
    )
    op.create_table(
        "conversations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('open')", name="ck_conversations_status"),
        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["synthetic_customers.id"],
            name="fk_conversations_customer_id_synthetic_customers",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_conversations"),
    )
    op.create_index("ix_conversations_customer_id", "conversations", ["customer_id"])


def downgrade() -> None:
    op.drop_index("ix_conversations_customer_id", table_name="conversations")
    op.drop_table("conversations")
    op.drop_table("synthetic_customers")
