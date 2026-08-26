from datetime import UTC, datetime
from uuid import UUID

import pytest

from telecom_agent.domain.conversations import Conversation, ConversationStatus
from telecom_agent.services.create_conversation import CreateConversationService


class RecordingConversationRepository:
    def __init__(self) -> None:
        self.saved: list[Conversation] = []

    def add(self, conversation: Conversation) -> None:
        self.saved.append(conversation)


class FailingConversationRepository:
    def add(self, conversation: Conversation) -> None:
        raise RuntimeError("database unavailable")


def test_create_conversation_starts_open_conversation_for_customer() -> None:
    customer_id = UUID("10000000-0000-0000-0000-000000000001")
    conversation_id = UUID("20000000-0000-0000-0000-000000000001")
    created_at = datetime(2026, 8, 26, 10, 30, tzinfo=UTC)
    repository = RecordingConversationRepository()
    service = CreateConversationService(
        repository=repository,
        id_factory=lambda: conversation_id,
        clock=lambda: created_at,
    )

    result = service.execute(customer_id=customer_id)

    assert result == Conversation(
        id=conversation_id,
        customer_id=customer_id,
        status=ConversationStatus.OPEN,
        created_at=created_at,
    )
    assert repository.saved == [result]


def test_create_conversation_does_not_report_success_when_persistence_fails() -> None:
    service = CreateConversationService(repository=FailingConversationRepository())

    with pytest.raises(RuntimeError, match="database unavailable"):
        service.execute(customer_id=UUID("10000000-0000-0000-0000-000000000001"))
