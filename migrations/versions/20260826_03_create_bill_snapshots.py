"""Create bill snapshots, line items, and message evidence.

Revision ID: 20260826_03
Revises: 20260826_02
Create Date: 2026-08-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260826_03"
down_revision: str | None = "20260826_02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "bill_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("total", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_version", sa.String(length=128), nullable=False),
        sa.Column("availability", sa.String(length=32), nullable=False),
        sa.CheckConstraint(
            "availability IN ('available')",
            name="ck_bill_snapshots_availability",
        ),
        sa.CheckConstraint(
            "char_length(currency) = 3",
            name="ck_bill_snapshots_currency_length",
        ),
        sa.CheckConstraint(
            "total >= 0",
            name="ck_bill_snapshots_nonnegative_total",
        ),
        sa.CheckConstraint(
            "period_start <= period_end",
            name="ck_bill_snapshots_period",
        ),
        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["synthetic_customers.id"],
            name="fk_bill_snapshots_customer_id_synthetic_customers",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_bill_snapshots"),
    )
    op.create_index("ix_bill_snapshots_customer_id", "bill_snapshots", ["customer_id"])

    op.create_table(
        "bill_line_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("bill_snapshot_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "amount >= 0",
            name="ck_bill_line_items_nonnegative_amount",
        ),
        sa.CheckConstraint(
            "position >= 0",
            name="ck_bill_line_items_nonnegative_position",
        ),
        sa.ForeignKeyConstraint(
            ["bill_snapshot_id"],
            ["bill_snapshots.id"],
            name="fk_bill_line_items_bill_snapshot_id_bill_snapshots",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_bill_line_items"),
        sa.UniqueConstraint(
            "bill_snapshot_id",
            "position",
            name="uq_bill_line_items_snapshot_position",
        ),
    )
    op.create_index(
        "ix_bill_line_items_bill_snapshot_id",
        "bill_line_items",
        ["bill_snapshot_id"],
    )

    op.create_table(
        "message_bill_evidence",
        sa.Column("message_id", sa.Uuid(), nullable=False),
        sa.Column("bill_snapshot_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["message_id"],
            ["messages.id"],
            name="fk_message_bill_evidence_message_id_messages",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["bill_snapshot_id"],
            ["bill_snapshots.id"],
            name="fk_message_bill_evidence_bill_snapshot_id_bill_snapshots",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "message_id",
            "bill_snapshot_id",
            name="pk_message_bill_evidence",
        ),
    )


def downgrade() -> None:
    op.drop_table("message_bill_evidence")
    op.drop_index("ix_bill_line_items_bill_snapshot_id", table_name="bill_line_items")
    op.drop_table("bill_line_items")
    op.drop_index("ix_bill_snapshots_customer_id", table_name="bill_snapshots")
    op.drop_table("bill_snapshots")
