from uuid import UUID

from telecom_agent.domain.conversations import ConversationHistory
from telecom_agent.ports.conversations import ConversationHistoryRepository
from telecom_agent.services.errors import ConversationNotFoundError


class GetConversationHistoryService:
    def __init__(self, repository: ConversationHistoryRepository) -> None:
        self._repository = repository

    def execute(self, *, customer_id: UUID, conversation_id: UUID) -> ConversationHistory:
        history = self._repository.get_history(conversation_id, customer_id)
        if history is None:
            raise ConversationNotFoundError
        return history
