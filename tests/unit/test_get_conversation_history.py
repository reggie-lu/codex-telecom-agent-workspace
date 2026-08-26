from datetime import UTC, datetime
from uuid import UUID

import pytest

from telecom_agent.domain.conversations import ConversationHistory, ConversationStatus
from telecom_agent.domain.messages import Message, MessageRole
from telecom_agent.services.errors import ConversationNotFoundError
from telecom_agent.services.get_conversation_history import GetConversationHistoryService

CUSTOMER_ID = UUID("10000000-0000-0000-0000-000000000001")
CONVERSATION_ID = UUID("20000000-0000-0000-0000-000000000001")
CREATED_AT = datetime(2026, 8, 26, 9, 40, tzinfo=UTC)


class StubHistories:
    def __init__(self, history: ConversationHistory | None) -> None:
        self.history = history
        self.requests: list[tuple[UUID, UUID]] = []

    def get_history(
        self,
        conversation_id: UUID,
        customer_id: UUID,
    ) -> ConversationHistory | None:
        self.requests.append((conversation_id, customer_id))
        return self.history


def test_get_history_returns_owned_conversation_without_mutation() -> None:
    history = ConversationHistory(
        id=CONVERSATION_ID,
        status=ConversationStatus.OPEN,
        created_at=CREATED_AT,
        messages=(
            Message(
                id=UUID("30000000-0000-0000-0000-000000000001"),
                conversation_id=CONVERSATION_ID,
                role=MessageRole.USER,
                content="What is my latest bill?",
                created_at=CREATED_AT,
            ),
        ),
    )
    repository = StubHistories(history)

    result = GetConversationHistoryService(repository).execute(
        customer_id=CUSTOMER_ID,
        conversation_id=CONVERSATION_ID,
    )

    assert result is history
    assert repository.requests == [(CONVERSATION_ID, CUSTOMER_ID)]


def test_missing_or_cross_customer_history_uses_privacy_preserving_not_found() -> None:
    repository = StubHistories(None)

    with pytest.raises(ConversationNotFoundError):
        GetConversationHistoryService(repository).execute(
            customer_id=CUSTOMER_ID,
            conversation_id=CONVERSATION_ID,
        )

    assert repository.requests == [(CONVERSATION_ID, CUSTOMER_ID)]
