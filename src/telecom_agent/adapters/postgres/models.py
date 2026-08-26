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
    Uuid,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


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
