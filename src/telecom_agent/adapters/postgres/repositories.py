from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from telecom_agent.adapters.postgres.models import ConversationRecord, SyntheticCustomerRecord
from telecom_agent.domain.conversations import Conversation


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
