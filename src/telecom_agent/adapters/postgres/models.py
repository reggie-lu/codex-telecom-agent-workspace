from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, Uuid
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
