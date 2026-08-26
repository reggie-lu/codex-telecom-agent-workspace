"""Create messages and plan snapshots.

Revision ID: 20260826_02
Revises: 20260826_01
Create Date: 2026-08-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260826_02"
down_revision: str | None = "20260826_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "plan_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("plan_code", sa.String(length=64), nullable=False),
        sa.Column("plan_name", sa.Text(), nullable=False),
        sa.Column("data_allowance_gb", sa.Integer(), nullable=False),
        sa.Column("recurring_charge", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_version", sa.String(length=128), nullable=False),
        sa.Column("availability", sa.String(length=32), nullable=False),
        sa.CheckConstraint(
            "availability IN ('available')",
            name="ck_plan_snapshots_availability",
        ),
        sa.CheckConstraint(
            "char_length(currency) = 3",
            name="ck_plan_snapshots_currency_length",
        ),
        sa.CheckConstraint(
            "recurring_charge >= 0",
            name="ck_plan_snapshots_nonnegative_charge",
        ),
        sa.CheckConstraint(
            "data_allowance_gb > 0",
            name="ck_plan_snapshots_positive_data",
        ),
        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["synthetic_customers.id"],
            name="fk_plan_snapshots_customer_id_synthetic_customers",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_plan_snapshots"),
    )
    op.create_index("ix_plan_snapshots_customer_id", "plan_snapshots", ["customer_id"])

    op.create_table(
        "messages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("answer_status", sa.String(length=32), nullable=True),
        sa.Column("uncertain", sa.Boolean(), nullable=True),
        sa.CheckConstraint(
            "answer_status IS NULL OR answer_status IN ('grounded', 'unavailable', 'unsupported')",
            name="ck_messages_answer_status",
        ),
        sa.CheckConstraint("role IN ('user', 'assistant')", name="ck_messages_role"),
        sa.CheckConstraint(
            "(role = 'user' AND answer_status IS NULL AND uncertain IS NULL) OR "
            "(role = 'assistant' AND answer_status IS NOT NULL AND uncertain IS NOT NULL)",
            name="ck_messages_role_metadata",
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
            name="fk_messages_conversation_id_conversations",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_messages"),
    )
    op.create_index(
        "ix_messages_conversation_id_created_at",
        "messages",
        ["conversation_id", "created_at"],
    )

    op.create_table(
        "message_plan_evidence",
        sa.Column("message_id", sa.Uuid(), nullable=False),
        sa.Column("plan_snapshot_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["message_id"],
            ["messages.id"],
            name="fk_message_plan_evidence_message_id_messages",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["plan_snapshot_id"],
            ["plan_snapshots.id"],
            name="fk_message_plan_evidence_plan_snapshot_id_plan_snapshots",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "message_id",
            "plan_snapshot_id",
            name="pk_message_plan_evidence",
        ),
    )


def downgrade() -> None:
    op.drop_table("message_plan_evidence")
    op.drop_index("ix_messages_conversation_id_created_at", table_name="messages")
    op.drop_table("messages")
    op.drop_index("ix_plan_snapshots_customer_id", table_name="plan_snapshots")
    op.drop_table("plan_snapshots")
