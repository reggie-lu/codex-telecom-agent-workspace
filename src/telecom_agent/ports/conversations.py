from typing import Protocol
from uuid import UUID

from telecom_agent.domain.conversations import Conversation, ConversationHistory
from telecom_agent.ports.messages import ConversationAccessRepository


class ConversationRepository(Protocol):
    def add(self, conversation: Conversation) -> None: ...


class ConversationHistoryRepository(Protocol):
    def get_history(
        self,
        conversation_id: UUID,
        customer_id: UUID,
    ) -> ConversationHistory | None: ...


class ConversationStore(
    ConversationRepository,
    ConversationAccessRepository,
    ConversationHistoryRepository,
    Protocol,
):
    pass


class CustomerIdentityRepository(Protocol):
    def find_customer_id(self, token_hash: str) -> UUID | None: ...
