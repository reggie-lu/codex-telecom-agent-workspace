from datetime import UTC, datetime
from hashlib import sha256
from uuid import UUID

from fastapi.testclient import TestClient

from telecom_agent.api.app import create_app
from telecom_agent.domain.conversations import Conversation, ConversationHistory, ConversationStatus
from telecom_agent.domain.escalations import Escalation, HandoffOutcome
from telecom_agent.services.errors import ActiveEscalationExistsError
from tests.fakes import DeterministicAnswerGenerator

VALID_TOKEN = "synthetic-alice-token"
CUSTOMER_ID = UUID("10000000-0000-0000-0000-000000000001")
CONVERSATION_ID = UUID("20000000-0000-0000-0000-000000000001")
ESCALATION_ID = UUID("30000000-0000-0000-0000-000000000001")
NOW = datetime(2026, 8, 26, 20, 0, tzinfo=UTC)


class Identities:
    def find_customer_id(self, token_hash: str) -> UUID | None:
        return CUSTOMER_ID if token_hash == sha256(VALID_TOKEN.encode()).hexdigest() else None


class Conversations:
    def __init__(self, exists: bool = True) -> None:
        self.exists = exists

    def add(self, _conversation: Conversation) -> None:
        raise AssertionError

    def is_owned_by(self, _conversation_id: UUID, _customer_id: UUID) -> bool:
        raise AssertionError

    def get_history(self, conversation_id: UUID, customer_id: UUID) -> ConversationHistory | None:
        assert conversation_id == CONVERSATION_ID
        assert customer_id == CUSTOMER_ID
        if not self.exists:
            return None
        return ConversationHistory(CONVERSATION_ID, ConversationStatus.OPEN, NOW, ())


class Escalations:
    def __init__(self, duplicate: bool = False) -> None:
        self.duplicate = duplicate
        self.value: Escalation | None = None

    def add_requested(self, escalation: Escalation) -> None:
        if self.duplicate:
            raise ActiveEscalationExistsError
        self.value = escalation

    def update(self, escalation: Escalation) -> None:
        self.value = escalation

    def get_owned(self, escalation_id: UUID, customer_id: UUID) -> Escalation | None:
        assert customer_id == CUSTOMER_ID
        if self.value is not None and escalation_id == self.value.id:
            return self.value
        return None


class Handoff:
    def submit(self, _escalation: Escalation) -> HandoffOutcome:
        return HandoffOutcome.ACCEPTED


class HealthyDatabase:
    def is_healthy(self) -> bool:
        return True


class UnusedPlans:
    def get_current_plan(self, _customer_id: UUID) -> None:
        return None


class UnusedExchanges:
    def add(self, _exchange: object) -> None:
        raise AssertionError


def client(*, exists: bool = True, duplicate: bool = False) -> TestClient:
    return TestClient(
        create_app(
            customer_identities=Identities(),
            conversations=Conversations(exists),
            escalations=Escalations(duplicate),
            handoff=Handoff(),
            database_health=HealthyDatabase(),
            current_plans=UnusedPlans(),
            answer_generator=DeterministicAnswerGenerator(),
            exchanges=UnusedExchanges(),
        )
    )


def test_create_and_get_escalation_return_minimal_public_resource() -> None:
    api = client()
    headers = {"Authorization": f"Bearer {VALID_TOKEN}"}
    created = api.post(
        f"/v1/conversations/{CONVERSATION_ID}/escalations",
        headers=headers,
        json={"reason": "  I do not recognize this roaming charge.  "},
    )

    assert created.status_code == 201
    body = created.json()
    assert set(body) == {
        "id", "conversation_id", "reason", "status", "created_at", "updated_at", "next_step"
    }
    assert body["conversation_id"] == str(CONVERSATION_ID)
    assert body["reason"] == "I do not recognize this roaming charge."
    assert body["status"] == "queued"
    assert body["next_step"] is None
    assert "handoff_context" not in body

    fetched = api.get(f"/v1/escalations/{body['id']}", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json() == body


def test_invalid_reason_uses_stable_error() -> None:
    response = client().post(
        f"/v1/conversations/{CONVERSATION_ID}/escalations",
        headers={"Authorization": f"Bearer {VALID_TOKEN}"},
        json={"reason": "   "},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_escalation_reason"


def test_duplicate_active_escalation_returns_conflict() -> None:
    response = client(duplicate=True).post(
        f"/v1/conversations/{CONVERSATION_ID}/escalations",
        headers={"Authorization": f"Bearer {VALID_TOKEN}"},
        json={"reason": "Please help."},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "escalation_already_active"


def test_missing_conversation_and_escalation_use_scoped_not_found_errors() -> None:
    headers = {"Authorization": f"Bearer {VALID_TOKEN}"}
    missing_conversation = client(exists=False).post(
        f"/v1/conversations/{CONVERSATION_ID}/escalations",
        headers=headers,
        json={"reason": "Please help."},
    )
    missing_escalation = client().get(f"/v1/escalations/{ESCALATION_ID}", headers=headers)
    assert missing_conversation.json()["error"]["code"] == "conversation_not_found"
    assert missing_escalation.status_code == 404
    assert missing_escalation.json()["error"]["code"] == "escalation_not_found"


def test_escalation_routes_require_authentication() -> None:
    assert client().post(
        f"/v1/conversations/{CONVERSATION_ID}/escalations",
        json={"reason": "Please help."},
    ).status_code == 401
    assert client().get(f"/v1/escalations/{ESCALATION_ID}").status_code == 401
