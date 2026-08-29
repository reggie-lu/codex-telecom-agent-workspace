"""Create plan comparison snapshots, offers, and message evidence.

Revision ID: 20260829_06
Revises: 20260826_05
Create Date: 2026-08-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260829_06"
down_revision: str | None = "20260826_05"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "plan_comparison_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("current_plan_code", sa.String(length=64), nullable=False),
        sa.Column("current_plan_name", sa.Text(), nullable=False),
        sa.Column("current_data_allowance_gb", sa.Integer(), nullable=False),
        sa.Column("current_recurring_charge", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("current_effective_from", sa.Date(), nullable=False),
        sa.Column("catalog_as_of", sa.Date(), nullable=False),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_version", sa.String(length=128), nullable=False),
        sa.Column("eligibility_verified", sa.Boolean(), nullable=False),
        sa.CheckConstraint(
            "current_data_allowance_gb > 0",
            name="ck_plan_comparison_snapshots_positive_data",
        ),
        sa.CheckConstraint(
            "current_recurring_charge >= 0",
            name="ck_plan_comparison_snapshots_nonnegative_charge",
        ),
        sa.CheckConstraint(
            "char_length(currency) = 3",
            name="ck_plan_comparison_snapshots_currency_length",
        ),
        sa.CheckConstraint(
            "eligibility_verified = false",
            name="ck_plan_comparison_snapshots_unverified_eligibility",
        ),
        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["synthetic_customers.id"],
            name="fk_plan_comparison_snapshots_customer_id_synthetic_customers",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_plan_comparison_snapshots"),
    )
    op.create_index(
        "ix_plan_comparison_snapshots_customer_id",
        "plan_comparison_snapshots",
        ["customer_id"],
    )

    op.create_table(
        "plan_comparison_offers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("comparison_snapshot_id", sa.Uuid(), nullable=False),
        sa.Column("plan_code", sa.String(length=64), nullable=False),
        sa.Column("plan_name", sa.Text(), nullable=False),
        sa.Column("data_allowance_gb", sa.Integer(), nullable=False),
        sa.Column("recurring_charge", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("recurring_charge_delta", sa.Numeric(12, 2), nullable=False),
        sa.Column("data_allowance_delta_gb", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "data_allowance_gb > 0",
            name="ck_plan_comparison_offers_positive_data",
        ),
        sa.CheckConstraint(
            "recurring_charge >= 0",
            name="ck_plan_comparison_offers_nonnegative_charge",
        ),
        sa.CheckConstraint(
            "char_length(currency) = 3",
            name="ck_plan_comparison_offers_currency_length",
        ),
        sa.CheckConstraint(
            "position >= 0",
            name="ck_plan_comparison_offers_nonnegative_position",
        ),
        sa.ForeignKeyConstraint(
            ["comparison_snapshot_id"],
            ["plan_comparison_snapshots.id"],
            name="fk_plan_comparison_offers_snapshot_id_plan_comparison_snapshots",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_plan_comparison_offers"),
        sa.UniqueConstraint(
            "comparison_snapshot_id",
            "position",
            name="uq_plan_comparison_offers_snapshot_position",
        ),
        sa.UniqueConstraint(
            "comparison_snapshot_id",
            "plan_code",
            name="uq_plan_comparison_offers_snapshot_plan_code",
        ),
    )
    op.create_index(
        "ix_plan_comparison_offers_snapshot_id",
        "plan_comparison_offers",
        ["comparison_snapshot_id"],
    )

    op.create_table(
        "message_plan_comparison_evidence",
        sa.Column("message_id", sa.Uuid(), nullable=False),
        sa.Column("comparison_snapshot_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["message_id"],
            ["messages.id"],
            name="fk_message_plan_comparison_evidence_message_id_messages",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["comparison_snapshot_id"],
            ["plan_comparison_snapshots.id"],
            name="fk_message_plan_comparison_evidence_snapshot_id_snapshots",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "message_id",
            "comparison_snapshot_id",
            name="pk_message_plan_comparison_evidence",
        ),
    )


def downgrade() -> None:
    op.drop_table("message_plan_comparison_evidence")
    op.drop_index(
        "ix_plan_comparison_offers_snapshot_id",
        table_name="plan_comparison_offers",
    )
    op.drop_table("plan_comparison_offers")
    op.drop_index(
        "ix_plan_comparison_snapshots_customer_id",
        table_name="plan_comparison_snapshots",
    )
    op.drop_table("plan_comparison_snapshots")
