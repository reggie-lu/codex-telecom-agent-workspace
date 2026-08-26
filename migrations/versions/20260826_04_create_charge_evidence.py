"""Create charge evidence snapshots and message evidence.

Revision ID: 20260826_04
Revises: 20260826_03
Create Date: 2026-08-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260826_04"
down_revision: str | None = "20260826_03"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "charge_evidence_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("line_item_code", sa.String(length=64), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("occurred_on", sa.Date(), nullable=False),
        sa.Column("location", sa.Text(), nullable=False),
        sa.Column("service_name", sa.Text(), nullable=False),
        sa.Column("trigger", sa.Text(), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_version", sa.String(length=128), nullable=False),
        sa.CheckConstraint(
            "amount >= 0",
            name="ck_charge_evidence_nonnegative_amount",
        ),
        sa.CheckConstraint(
            "char_length(currency) = 3",
            name="ck_charge_evidence_currency_length",
        ),
        sa.CheckConstraint(
            "state IN ('confirmed', 'stale')",
            name="ck_charge_evidence_state",
        ),
        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["synthetic_customers.id"],
            name="fk_charge_evidence_customer_id_synthetic_customers",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_charge_evidence_snapshots"),
    )
    op.create_index(
        "ix_charge_evidence_customer_id",
        "charge_evidence_snapshots",
        ["customer_id"],
    )

    op.create_table(
        "message_charge_evidence",
        sa.Column("message_id", sa.Uuid(), nullable=False),
        sa.Column("charge_snapshot_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["message_id"],
            ["messages.id"],
            name="fk_message_charge_evidence_message_id_messages",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["charge_snapshot_id"],
            ["charge_evidence_snapshots.id"],
            name="fk_message_charge_evidence_charge_snapshot_id_charge_evidence",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "message_id",
            "charge_snapshot_id",
            name="pk_message_charge_evidence",
        ),
    )


def downgrade() -> None:
    op.drop_table("message_charge_evidence")
    op.drop_index("ix_charge_evidence_customer_id", table_name="charge_evidence_snapshots")
    op.drop_table("charge_evidence_snapshots")
