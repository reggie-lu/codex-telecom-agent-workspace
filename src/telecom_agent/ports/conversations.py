from typing import Protocol
from uuid import UUID

from telecom_agent.domain.conversations import Conversation


class ConversationRepository(Protocol):
    def add(self, conversation: Conversation) -> None: ...


class CustomerIdentityRepository(Protocol):
    def find_customer_id(self, token_hash: str) -> UUID | None: ...
