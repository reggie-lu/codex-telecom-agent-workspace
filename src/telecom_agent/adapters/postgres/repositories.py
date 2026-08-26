from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from telecom_agent.adapters.postgres.models import (
    ConversationRecord,
    MessagePlanEvidenceRecord,
    MessageRecord,
    PlanSnapshotRecord,
    SyntheticCustomerRecord,
)
from telecom_agent.domain.conversations import Conversation
from telecom_agent.domain.messages import MessageExchange


class SqlAlchemyCustomerIdentityRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def find_customer_id(self, token_hash: str) -> UUID | None:
        with self._session_factory() as session:
            return session.scalar(
                select(SyntheticCustomerRecord.id).where(
                    SyntheticCustomerRecord.token_hash == token_hash
                )
            )


class SqlAlchemyConversationRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def add(self, conversation: Conversation) -> None:
        with self._session_factory.begin() as session:
            session.add(
                ConversationRecord(
                    id=conversation.id,
                    customer_id=conversation.customer_id,
                    status=conversation.status.value,
                    created_at=conversation.created_at,
                )
            )

    def is_owned_by(self, conversation_id: UUID, customer_id: UUID) -> bool:
        with self._session_factory() as session:
            return (
                session.scalar(
                    select(ConversationRecord.id).where(
                        ConversationRecord.id == conversation_id,
                        ConversationRecord.customer_id == customer_id,
                    )
                )
                is not None
            )


class SqlAlchemyMessageExchangeRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def add(self, exchange: MessageExchange) -> None:
        with self._session_factory.begin() as session:
            if exchange.plan_snapshot is not None:
                snapshot = exchange.plan_snapshot
                session.add(
                    PlanSnapshotRecord(
                        id=snapshot.id,
                        customer_id=snapshot.customer_id,
                        plan_code=snapshot.plan_code,
                        plan_name=snapshot.plan_name,
                        data_allowance_gb=snapshot.data_allowance_gb,
                        recurring_charge=snapshot.recurring_charge,
                        currency=snapshot.currency,
                        effective_from=snapshot.effective_from,
                        retrieved_at=snapshot.retrieved_at,
                        source_version=snapshot.source_version,
                        availability=snapshot.availability.value,
                    )
                )

            for message in (exchange.user_message, exchange.assistant_message):
                session.add(
                    MessageRecord(
                        id=message.id,
                        conversation_id=message.conversation_id,
                        role=message.role.value,
                        content=message.content,
                        created_at=message.created_at,
                        answer_status=(
                            message.answer_status.value
                            if message.answer_status is not None
                            else None
                        ),
                        uncertain=message.uncertain,
                    )
                )

            session.flush()
            for evidence in exchange.assistant_message.evidence:
                session.add(
                    MessagePlanEvidenceRecord(
                        message_id=exchange.assistant_message.id,
                        plan_snapshot_id=evidence.id,
                    )
                )
