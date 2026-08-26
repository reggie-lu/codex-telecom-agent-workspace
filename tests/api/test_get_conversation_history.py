from datetime import UTC, datetime
from hashlib import sha256
from uuid import UUID

from fastapi.testclient import TestClient

from telecom_agent.api.app import create_app
from telecom_agent.domain.conversations import (
    Conversation,
    ConversationHistory,
    ConversationStatus,
)
from telecom_agent.domain.messages import (
    AnswerStatus,
    EvidenceReference,
    EvidenceType,
    Message,
    MessageRole,
)
from tests.fakes import DeterministicAnswerGenerator, UnusedEscalations, UnusedHandoff

VALID_TOKEN = "synthetic-alice-token"
CUSTOMER_ID = UUID("10000000-0000-0000-0000-000000000001")
CONVERSATION_ID = UUID("20000000-0000-0000-0000-000000000001")
CREATED_AT = datetime(2026, 8, 26, 9, 45, tzinfo=UTC)


class StubCustomerIdentities:
    def find_customer_id(self, token_hash: str) -> UUID | None:
        if token_hash == sha256(VALID_TOKEN.encode()).hexdigest():
            return CUSTOMER_ID
        return None


class StubConversations:
    def __init__(self, history: ConversationHistory | None) -> None:
        self.history = history

    def add(self, _conversation: Conversation) -> None:
        raise AssertionError("History retrieval must not create a conversation")

    def is_owned_by(self, _conversation_id: UUID, _customer_id: UUID) -> bool:
        raise AssertionError("History retrieval uses the scoped read operation")

    def get_history(
        self,
        conversation_id: UUID,
        customer_id: UUID,
    ) -> ConversationHistory | None:
        assert conversation_id == CONVERSATION_ID
        assert customer_id == CUSTOMER_ID
        return self.history


class HealthyDatabase:
    def is_healthy(self) -> bool:
        return True


class UnusedCurrentPlans:
    def get_current_plan(self, _customer_id: UUID) -> None:
        raise AssertionError("History retrieval must not query current plan data")


class UnusedExchanges:
    def add(self, _exchange: object) -> None:
        raise AssertionError("History retrieval must not persist messages")


def history() -> ConversationHistory:
    return ConversationHistory(
        id=CONVERSATION_ID,
        status=ConversationStatus.OPEN,
        created_at=CREATED_AT,
        messages=(
            Message(
                id=UUID("30000000-0000-0000-0000-000000000001"),
                conversation_id=CONVERSATION_ID,
                role=MessageRole.USER,
                content="Why is my latest bill higher?",
                created_at=CREATED_AT,
            ),
            Message(
                id=UUID("40000000-0000-0000-0000-000000000001"),
                conversation_id=CONVERSATION_ID,
                role=MessageRole.ASSISTANT,
                content="A grounded explanation.",
                created_at=datetime(2026, 8, 26, 9, 45, 1, tzinfo=UTC),
                answer_status=AnswerStatus.GROUNDED,
                uncertain=False,
                evidence=(
                    EvidenceReference(
                        EvidenceType.PLAN_SNAPSHOT,
                        UUID("50000000-0000-0000-0000-000000000001"),
                    ),
                    EvidenceReference(
                        EvidenceType.BILL_SNAPSHOT,
                        UUID("50000000-0000-0000-0000-000000000002"),
                    ),
                    EvidenceReference(
                        EvidenceType.CHARGE_SNAPSHOT,
                        UUID("50000000-0000-0000-0000-000000000003"),
                    ),
                ),
            ),
        ),
    )


def build_client(stored_history: ConversationHistory | None) -> TestClient:
    return TestClient(
        create_app(
            customer_identities=StubCustomerIdentities(),
            conversations=StubConversations(stored_history),
            escalations=UnusedEscalations(),
            handoff=UnusedHandoff(),
            database_health=HealthyDatabase(),
            current_plans=UnusedCurrentPlans(),
            answer_generator=DeterministicAnswerGenerator(),
            exchanges=UnusedExchanges(),
        )
    )


def test_get_conversation_returns_complete_ordered_message_history() -> None:
    response = build_client(history()).get(
        f"/v1/conversations/{CONVERSATION_ID}",
        headers={"Authorization": f"Bearer {VALID_TOKEN}"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": str(CONVERSATION_ID),
        "status": "open",
        "created_at": "2026-08-26T09:45:00Z",
        "messages": [
            {
                "id": "30000000-0000-0000-0000-000000000001",
                "role": "user",
                "content": "Why is my latest bill higher?",
                "created_at": "2026-08-26T09:45:00Z",
            },
            {
                "id": "40000000-0000-0000-0000-000000000001",
                "role": "assistant",
                "content": "A grounded explanation.",
                "created_at": "2026-08-26T09:45:01Z",
                "answer_status": "grounded",
                "uncertain": False,
                "evidence": [
                    {
                        "type": "plan_snapshot",
                        "id": "50000000-0000-0000-0000-000000000001",
                    },
                    {
                        "type": "bill_snapshot",
                        "id": "50000000-0000-0000-0000-000000000002",
                    },
                    {
                        "type": "charge_snapshot",
                        "id": "50000000-0000-0000-0000-000000000003",
                    },
                ],
            },
        ],
    }


def test_get_empty_conversation_returns_empty_message_list() -> None:
    empty = ConversationHistory(
        id=CONVERSATION_ID,
        status=ConversationStatus.OPEN,
        created_at=CREATED_AT,
        messages=(),
    )

    response = build_client(empty).get(
        f"/v1/conversations/{CONVERSATION_ID}",
        headers={"Authorization": f"Bearer {VALID_TOKEN}"},
    )

    assert response.status_code == 200
    assert response.json()["messages"] == []


def test_missing_or_cross_customer_conversation_returns_same_not_found() -> None:
    response = build_client(None).get(
        f"/v1/conversations/{CONVERSATION_ID}",
        headers={"Authorization": f"Bearer {VALID_TOKEN}"},
    )

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "conversation_not_found",
            "message": "Conversation not found.",
        }
    }


def test_get_conversation_requires_authentication() -> None:
    response = build_client(history()).get(f"/v1/conversations/{CONVERSATION_ID}")

    assert response.status_code == 401
