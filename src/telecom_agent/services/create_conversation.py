from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID, uuid4

from telecom_agent.domain.conversations import Conversation, ConversationStatus
from telecom_agent.ports.conversations import ConversationRepository


class CreateConversationService:
    def __init__(
        self,
        repository: ConversationRepository,
        id_factory: Callable[[], UUID] = uuid4,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._repository = repository
        self._id_factory = id_factory
        self._clock = clock

    def execute(self, customer_id: UUID) -> Conversation:
        conversation = Conversation(
            id=self._id_factory(),
            customer_id=customer_id,
            status=ConversationStatus.OPEN,
            created_at=self._clock(),
        )
        self._repository.add(conversation)
        return conversation
