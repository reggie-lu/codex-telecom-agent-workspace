"""Create contextual human escalations.

Revision ID: 20260826_05
Revises: 20260826_04
Create Date: 2026-08-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260826_05"
down_revision: str | None = "20260826_04"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "escalations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("next_step", sa.Text(), nullable=True),
        sa.Column("handoff_context", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.CheckConstraint(
            "status IN ('requested', 'queued', 'assigned', 'resolved', 'failed')",
            name="ck_escalations_status",
        ),
        sa.CheckConstraint(
            "char_length(reason) BETWEEN 1 AND 1000",
            name="ck_escalations_reason_length",
        ),
        sa.CheckConstraint(
            "(status = 'failed' AND next_step IS NOT NULL) OR "
            "(status <> 'failed' AND next_step IS NULL)",
            name="ck_escalations_failed_next_step",
        ),
        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["synthetic_customers.id"],
            name="fk_escalations_customer_id_synthetic_customers",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
            name="fk_escalations_conversation_id_conversations",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_escalations"),
    )
    op.create_index("ix_escalations_customer_id", "escalations", ["customer_id"])
    op.create_index("ix_escalations_conversation_id", "escalations", ["conversation_id"])
    op.create_index(
        "uq_escalations_active_conversation",
        "escalations",
        ["conversation_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('requested', 'queued', 'assigned')"),
    )


def downgrade() -> None:
    op.drop_index("uq_escalations_active_conversation", table_name="escalations")
    op.drop_index("ix_escalations_conversation_id", table_name="escalations")
    op.drop_index("ix_escalations_customer_id", table_name="escalations")
    op.drop_table("escalations")
