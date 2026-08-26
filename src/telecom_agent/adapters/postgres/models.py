from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import text


class Base(DeclarativeBase):
    pass


class SyntheticCustomerRecord(Base):
    __tablename__ = "synthetic_customers"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ConversationRecord(Base):
    __tablename__ = "conversations"
    __table_args__ = (
        CheckConstraint("status IN ('open')", name="ck_conversations_status"),
        Index("ix_conversations_customer_id", "customer_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    customer_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("synthetic_customers.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PlanSnapshotRecord(Base):
    __tablename__ = "plan_snapshots"
    __table_args__ = (
        CheckConstraint("data_allowance_gb > 0", name="ck_plan_snapshots_positive_data"),
        CheckConstraint("recurring_charge >= 0", name="ck_plan_snapshots_nonnegative_charge"),
        CheckConstraint("char_length(currency) = 3", name="ck_plan_snapshots_currency_length"),
        CheckConstraint("availability IN ('available')", name="ck_plan_snapshots_availability"),
        Index("ix_plan_snapshots_customer_id", "customer_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    customer_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("synthetic_customers.id", ondelete="CASCADE"),
        nullable=False,
    )
    plan_code: Mapped[str] = mapped_column(String(64), nullable=False)
    plan_name: Mapped[str] = mapped_column(Text, nullable=False)
    data_allowance_gb: Mapped[int] = mapped_column(Integer, nullable=False)
    recurring_charge: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_version: Mapped[str] = mapped_column(String(128), nullable=False)
    availability: Mapped[str] = mapped_column(String(32), nullable=False)


class MessageRecord(Base):
    __tablename__ = "messages"
    __table_args__ = (
        CheckConstraint("role IN ('user', 'assistant')", name="ck_messages_role"),
        CheckConstraint(
            "answer_status IS NULL OR answer_status IN ('grounded', 'unavailable', 'unsupported')",
            name="ck_messages_answer_status",
        ),
        CheckConstraint(
            "(role = 'user' AND answer_status IS NULL AND uncertain IS NULL) OR "
            "(role = 'assistant' AND answer_status IS NOT NULL AND uncertain IS NOT NULL)",
            name="ck_messages_role_metadata",
        ),
        Index("ix_messages_conversation_id_created_at", "conversation_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    conversation_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    answer_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    uncertain: Mapped[bool | None] = mapped_column(Boolean, nullable=True)


class MessagePlanEvidenceRecord(Base):
    __tablename__ = "message_plan_evidence"

    message_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("messages.id", ondelete="CASCADE"),
        primary_key=True,
    )
    plan_snapshot_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("plan_snapshots.id", ondelete="CASCADE"),
        primary_key=True,
    )


class BillSnapshotRecord(Base):
    __tablename__ = "bill_snapshots"
    __table_args__ = (
        CheckConstraint("period_start <= period_end", name="ck_bill_snapshots_period"),
        CheckConstraint("total >= 0", name="ck_bill_snapshots_nonnegative_total"),
        CheckConstraint("char_length(currency) = 3", name="ck_bill_snapshots_currency_length"),
        CheckConstraint("availability IN ('available')", name="ck_bill_snapshots_availability"),
        Index("ix_bill_snapshots_customer_id", "customer_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    customer_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("synthetic_customers.id", ondelete="CASCADE"),
        nullable=False,
    )
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_version: Mapped[str] = mapped_column(String(128), nullable=False)
    availability: Mapped[str] = mapped_column(String(32), nullable=False)


class BillLineItemRecord(Base):
    __tablename__ = "bill_line_items"
    __table_args__ = (
        CheckConstraint("amount >= 0", name="ck_bill_line_items_nonnegative_amount"),
        CheckConstraint("position >= 0", name="ck_bill_line_items_nonnegative_position"),
        UniqueConstraint(
            "bill_snapshot_id",
            "position",
            name="uq_bill_line_items_snapshot_position",
        ),
        Index("ix_bill_line_items_bill_snapshot_id", "bill_snapshot_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    bill_snapshot_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("bill_snapshots.id", ondelete="CASCADE"),
        nullable=False,
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)


class MessageBillEvidenceRecord(Base):
    __tablename__ = "message_bill_evidence"

    message_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("messages.id", ondelete="CASCADE"),
        primary_key=True,
    )
    bill_snapshot_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("bill_snapshots.id", ondelete="CASCADE"),
        primary_key=True,
    )


class ChargeEvidenceSnapshotRecord(Base):
    __tablename__ = "charge_evidence_snapshots"
    __table_args__ = (
        CheckConstraint("amount >= 0", name="ck_charge_evidence_nonnegative_amount"),
        CheckConstraint("char_length(currency) = 3", name="ck_charge_evidence_currency_length"),
        CheckConstraint("state IN ('confirmed', 'stale')", name="ck_charge_evidence_state"),
        Index("ix_charge_evidence_customer_id", "customer_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    customer_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("synthetic_customers.id", ondelete="CASCADE"),
        nullable=False,
    )
    line_item_code: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    occurred_on: Mapped[date] = mapped_column(Date, nullable=False)
    location: Mapped[str] = mapped_column(Text, nullable=False)
    service_name: Mapped[str] = mapped_column(Text, nullable=False)
    trigger: Mapped[str] = mapped_column(Text, nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_version: Mapped[str] = mapped_column(String(128), nullable=False)


class MessageChargeEvidenceRecord(Base):
    __tablename__ = "message_charge_evidence"

    message_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("messages.id", ondelete="CASCADE"),
        primary_key=True,
    )
    charge_snapshot_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("charge_evidence_snapshots.id", ondelete="CASCADE"),
        primary_key=True,
    )


class EscalationRecord(Base):
    __tablename__ = "escalations"
    __table_args__ = (
        CheckConstraint(
            "status IN ('requested', 'queued', 'assigned', 'resolved', 'failed')",
            name="ck_escalations_status",
        ),
        CheckConstraint(
            "char_length(reason) BETWEEN 1 AND 1000",
            name="ck_escalations_reason_length",
        ),
        CheckConstraint(
            "(status = 'failed' AND next_step IS NOT NULL) OR "
            "(status <> 'failed' AND next_step IS NULL)",
            name="ck_escalations_failed_next_step",
        ),
        Index("ix_escalations_customer_id", "customer_id"),
        Index("ix_escalations_conversation_id", "conversation_id"),
        Index(
            "uq_escalations_active_conversation",
            "conversation_id",
            unique=True,
            postgresql_where=text("status IN ('requested', 'queued', 'assigned')"),
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    customer_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("synthetic_customers.id", ondelete="CASCADE"),
        nullable=False,
    )
    conversation_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    next_step: Mapped[str | None] = mapped_column(Text, nullable=True)
    handoff_context: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
