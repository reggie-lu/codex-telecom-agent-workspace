from hashlib import sha256
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from telecom_agent.api.app import create_app
from telecom_agent.domain.conversations import Conversation, ConversationHistory
from tests.fakes import DeterministicAnswerGenerator, UnusedEscalations, UnusedHandoff

VALID_TOKEN = "synthetic-alice-token"
CUSTOMER_ID = UUID("10000000-0000-0000-0000-000000000001")


class StubCustomerIdentityRepository:
    def __init__(self) -> None:
        self.customer_ids_by_token_hash = {sha256(VALID_TOKEN.encode()).hexdigest(): CUSTOMER_ID}

    def find_customer_id(self, token_hash: str) -> UUID | None:
        return self.customer_ids_by_token_hash.get(token_hash)


class RecordingConversationRepository:
    def __init__(self) -> None:
        self.saved: list[Conversation] = []

    def add(self, conversation: Conversation) -> None:
        self.saved.append(conversation)

    def is_owned_by(self, _conversation_id: UUID, _customer_id: UUID) -> bool:
        return False

    def get_history(
        self,
        _conversation_id: UUID,
        _customer_id: UUID,
    ) -> ConversationHistory | None:
        raise AssertionError("Conversation creation must not retrieve history")


class UnusedCurrentPlans:
    def get_current_plan(self, _customer_id: UUID) -> None:
        return None


class UnusedExchanges:
    def add(self, _exchange: object) -> None:
        raise AssertionError("Conversation creation must not persist messages")


class HealthyDatabase:
    def is_healthy(self) -> bool:
        return True


@pytest.fixture
def repository() -> RecordingConversationRepository:
    return RecordingConversationRepository()


@pytest.fixture
def client(repository: RecordingConversationRepository) -> TestClient:
    app = create_app(
        customer_identities=StubCustomerIdentityRepository(),
        conversations=repository,
        escalations=UnusedEscalations(),
        handoff=UnusedHandoff(),
        database_health=HealthyDatabase(),
        current_plans=UnusedCurrentPlans(),
        answer_generator=DeterministicAnswerGenerator(),
        exchanges=UnusedExchanges(),
    )
    return TestClient(app)


def test_create_conversation_returns_approved_contract(
    client: TestClient,
    repository: RecordingConversationRepository,
) -> None:
    response = client.post(
        "/v1/conversations",
        headers={"Authorization": f"Bearer {VALID_TOKEN}"},
    )

    assert response.status_code == 201
    assert set(response.json()) == {"id", "status", "created_at"}
    assert response.json()["status"] == "open"
    assert response.json()["created_at"].endswith("Z")
    assert len(repository.saved) == 1
    assert repository.saved[0].customer_id == CUSTOMER_ID


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Authorization": "Bearer invalid-token"},
    ],
)
def test_create_conversation_rejects_missing_or_invalid_token(
    client: TestClient,
    repository: RecordingConversationRepository,
    headers: dict[str, str],
) -> None:
    response = client.post("/v1/conversations", headers=headers)

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"
    assert response.json() == {
        "error": {
            "code": "unauthorized",
            "message": "A valid synthetic bearer token is required.",
        }
    }
    assert repository.saved == []


def test_repeated_requests_create_distinct_conversations(
    client: TestClient,
    repository: RecordingConversationRepository,
) -> None:
    headers = {"Authorization": f"Bearer {VALID_TOKEN}"}

    first = client.post("/v1/conversations", headers=headers)
    second = client.post("/v1/conversations", headers=headers)

    assert first.status_code == second.status_code == 201
    assert first.json()["id"] != second.json()["id"]
    assert len(repository.saved) == 2
