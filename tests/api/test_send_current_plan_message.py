from datetime import date
from decimal import Decimal
from hashlib import sha256
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from telecom_agent.api.app import create_app
from telecom_agent.domain.conversations import Conversation
from telecom_agent.domain.messages import MessageExchange
from telecom_agent.domain.plans import CurrentPlanDetails

VALID_TOKEN = "synthetic-alice-token"
CUSTOMER_ID = UUID("10000000-0000-0000-0000-000000000001")
CONVERSATION_ID = UUID("20000000-0000-0000-0000-000000000001")


class StubCustomerIdentities:
    def find_customer_id(self, token_hash: str) -> UUID | None:
        if token_hash == sha256(VALID_TOKEN.encode()).hexdigest():
            return CUSTOMER_ID
        return None


class StubConversations:
    def __init__(self, owned: bool = True) -> None:
        self.owned = owned

    def add(self, _conversation: Conversation) -> None:
        raise AssertionError("Message submission must not create a conversation")

    def is_owned_by(self, conversation_id: UUID, customer_id: UUID) -> bool:
        assert conversation_id == CONVERSATION_ID
        assert customer_id == CUSTOMER_ID
        return self.owned


class StubCurrentPlans:
    def __init__(self, available: bool = True) -> None:
        self.available = available

    def get_current_plan(self, customer_id: UUID) -> CurrentPlanDetails | None:
        assert customer_id == CUSTOMER_ID
        if not self.available:
            return None
        return CurrentPlanDetails(
            plan_code="SYN-KDDI-5G-20",
            plan_name="Synthetic KDDI 5G 20GB",
            data_allowance_gb=20,
            recurring_charge=Decimal("4500.00"),
            currency="JPY",
            effective_from=date(2026, 8, 1),
            source_version="synthetic-kddi-v1",
        )


class RecordingExchanges:
    def __init__(self) -> None:
        self.saved: list[MessageExchange] = []

    def add(self, exchange: MessageExchange) -> None:
        self.saved.append(exchange)


class HealthyDatabase:
    def is_healthy(self) -> bool:
        return True


def build_client(
    *,
    owned: bool = True,
    plan_available: bool = True,
) -> tuple[TestClient, RecordingExchanges]:
    exchanges = RecordingExchanges()
    app = create_app(
        customer_identities=StubCustomerIdentities(),
        conversations=StubConversations(owned),
        database_health=HealthyDatabase(),
        current_plans=StubCurrentPlans(plan_available),
        exchanges=exchanges,
    )
    return TestClient(app), exchanges


def test_current_plan_message_returns_approved_grounded_exchange_contract() -> None:
    client, exchanges = build_client()

    response = client.post(
        f"/v1/conversations/{CONVERSATION_ID}/messages",
        headers={"Authorization": f"Bearer {VALID_TOKEN}"},
        json={"content": "  What is my current plan?  "},
    )

    assert response.status_code == 201
    body = response.json()
    assert set(body) == {"user_message", "assistant_message"}
    assert set(body["user_message"]) == {"id", "role", "content", "created_at"}
    assert body["user_message"]["role"] == "user"
    assert body["user_message"]["content"] == "What is my current plan?"
    assert set(body["assistant_message"]) == {
        "id",
        "role",
        "content",
        "created_at",
        "answer_status",
        "uncertain",
        "evidence",
    }
    assert body["assistant_message"]["role"] == "assistant"
    assert body["assistant_message"]["answer_status"] == "grounded"
    assert body["assistant_message"]["uncertain"] is False
    assert body["assistant_message"]["evidence"][0]["type"] == "plan_snapshot"
    assert len(exchanges.saved) == 1


def test_unavailable_plan_is_a_persisted_safe_exchange() -> None:
    client, exchanges = build_client(plan_available=False)

    response = client.post(
        f"/v1/conversations/{CONVERSATION_ID}/messages",
        headers={"Authorization": f"Bearer {VALID_TOKEN}"},
        json={"content": "What plan do I have?"},
    )

    assert response.status_code == 201
    assistant = response.json()["assistant_message"]
    assert assistant["answer_status"] == "unavailable"
    assert assistant["uncertain"] is True
    assert assistant["evidence"] == []
    assert "unavailable" in assistant["content"]
    assert len(exchanges.saved) == 1


@pytest.mark.parametrize("owned", [False])
def test_missing_or_cross_customer_conversation_returns_same_not_found(owned: bool) -> None:
    client, exchanges = build_client(owned=owned)

    response = client.post(
        f"/v1/conversations/{CONVERSATION_ID}/messages",
        headers={"Authorization": f"Bearer {VALID_TOKEN}"},
        json={"content": "What is my plan?"},
    )

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "conversation_not_found",
            "message": "Conversation not found.",
        }
    }
    assert exchanges.saved == []


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"content": ""},
        {"content": "   "},
        {"content": "x" * 2001},
    ],
)
def test_invalid_content_returns_stable_validation_error(payload: dict[str, str]) -> None:
    client, exchanges = build_client()

    response = client.post(
        f"/v1/conversations/{CONVERSATION_ID}/messages",
        headers={"Authorization": f"Bearer {VALID_TOKEN}"},
        json=payload,
    )

    assert response.status_code == 422
    assert response.json() == {
        "error": {
            "code": "invalid_message",
            "message": "Message content must contain 1 to 2000 characters.",
        }
    }
    assert exchanges.saved == []


def test_message_requires_authentication_before_conversation_access() -> None:
    client, exchanges = build_client()

    response = client.post(
        f"/v1/conversations/{CONVERSATION_ID}/messages",
        json={"content": "What is my plan?"},
    )

    assert response.status_code == 401
    assert exchanges.saved == []
