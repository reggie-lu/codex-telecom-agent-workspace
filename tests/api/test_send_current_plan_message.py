from datetime import date
from decimal import Decimal
from hashlib import sha256
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from telecom_agent.api.app import create_app
from telecom_agent.domain.bills import BillLineItem, LatestBillDetails
from telecom_agent.domain.charges import ChargeEvidenceDetails, ChargeEvidenceState
from telecom_agent.domain.conversations import Conversation, ConversationHistory
from telecom_agent.domain.messages import MessageExchange
from telecom_agent.domain.plans import CurrentPlanDetails
from tests.fakes import DeterministicAnswerGenerator, UnusedEscalations, UnusedHandoff

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

    def get_history(
        self,
        _conversation_id: UUID,
        _customer_id: UUID,
    ) -> ConversationHistory | None:
        raise AssertionError("Message submission must not retrieve history")


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


class StubLatestBills:
    def __init__(self, available: bool = True) -> None:
        self.available = available

    def get_latest_bill(self, customer_id: UUID) -> LatestBillDetails | None:
        assert customer_id == CUSTOMER_ID
        if not self.available:
            return None
        return LatestBillDetails(
            period_start=date(2026, 7, 1),
            period_end=date(2026, 7, 31),
            total=Decimal("6930.00"),
            currency="JPY",
            line_items=(
                BillLineItem("monthly_service", "Monthly mobile service", Decimal("4500.00")),
                BillLineItem("domestic_calls", "Domestic calls", Decimal("600.00")),
                BillLineItem("roaming_data", "International roaming data", Decimal("1200.00")),
                BillLineItem("taxes_fees", "Taxes and fees", Decimal("630.00")),
            ),
            source_version="synthetic-kddi-bill-v1",
        )


class StubChargeEvidence:
    def __init__(self, available: bool = True) -> None:
        self.available = available

    def get_charge_evidence(
        self,
        customer_id: UUID,
        line_item_code: str,
    ) -> ChargeEvidenceDetails | None:
        assert customer_id == CUSTOMER_ID
        assert line_item_code == "roaming_data"
        if not self.available:
            return None
        return ChargeEvidenceDetails(
            line_item_code="roaming_data",
            description="International roaming data",
            amount=Decimal("1200.00"),
            currency="JPY",
            occurred_on=date(2026, 7, 18),
            location="United States",
            service_name="Synthetic KDDI Overseas Data Day Pass",
            trigger="automatically activated when the device used mobile data while roaming",
            state=ChargeEvidenceState.CONFIRMED,
            source_version="synthetic-kddi-charge-v1",
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
    bill_available: bool = True,
    charge_evidence_available: bool = True,
) -> tuple[TestClient, RecordingExchanges]:
    exchanges = RecordingExchanges()
    app = create_app(
        customer_identities=StubCustomerIdentities(),
        conversations=StubConversations(owned),
        escalations=UnusedEscalations(),
        handoff=UnusedHandoff(),
        database_health=HealthyDatabase(),
        current_plans=StubCurrentPlans(plan_available),
        latest_bills=StubLatestBills(bill_available),
        charge_evidence=StubChargeEvidence(charge_evidence_available),
        answer_generator=DeterministicAnswerGenerator(),
        exchanges=exchanges,
    )
    return TestClient(app), exchanges


def test_latest_bill_message_returns_grounded_bill_evidence() -> None:
    client, exchanges = build_client()

    response = client.post(
        f"/v1/conversations/{CONVERSATION_ID}/messages",
        headers={"Authorization": f"Bearer {VALID_TOKEN}"},
        json={"content": "Show me my latest bill"},
    )

    assert response.status_code == 201
    assistant = response.json()["assistant_message"]
    assert assistant["answer_status"] == "grounded"
    assert assistant["uncertain"] is False
    assert assistant["evidence"][0]["type"] == "bill_snapshot"
    assert "July 1–31, 2026" in assistant["content"]
    assert "JPY 6,930" in assistant["content"]
    assert "International roaming data — JPY 1,200" in assistant["content"]
    assert exchanges.saved[0].bill_snapshot is not None


def test_unavailable_latest_bill_returns_safe_persisted_exchange() -> None:
    client, exchanges = build_client(bill_available=False)

    response = client.post(
        f"/v1/conversations/{CONVERSATION_ID}/messages",
        headers={"Authorization": f"Bearer {VALID_TOKEN}"},
        json={"content": "What is my latest bill?"},
    )

    assert response.status_code == 201
    assistant = response.json()["assistant_message"]
    assert assistant["answer_status"] == "unavailable"
    assert assistant["uncertain"] is True
    assert assistant["evidence"] == []
    assert "6,930" not in assistant["content"]
    assert len(exchanges.saved) == 1


def test_unexpected_charge_message_returns_bill_and_charge_evidence() -> None:
    client, exchanges = build_client()

    response = client.post(
        f"/v1/conversations/{CONVERSATION_ID}/messages",
        headers={"Authorization": f"Bearer {VALID_TOKEN}"},
        json={"content": "Why is my latest bill higher?"},
    )

    assert response.status_code == 201
    assistant = response.json()["assistant_message"]
    assert assistant["answer_status"] == "grounded"
    assert assistant["uncertain"] is False
    assert [evidence["type"] for evidence in assistant["evidence"]] == [
        "bill_snapshot",
        "charge_snapshot",
    ]
    assert "JPY 1,200" in assistant["content"]
    assert "United States" in assistant["content"]
    assert "July 18, 2026" in assistant["content"]
    assert exchanges.saved[0].charge_snapshot is not None


def test_missing_charge_evidence_returns_uncertain_bill_grounded_limitation() -> None:
    client, exchanges = build_client(charge_evidence_available=False)

    response = client.post(
        f"/v1/conversations/{CONVERSATION_ID}/messages",
        headers={"Authorization": f"Bearer {VALID_TOKEN}"},
        json={"content": "What is the unexpected charge?"},
    )

    assert response.status_code == 201
    assistant = response.json()["assistant_message"]
    assert assistant["answer_status"] == "unavailable"
    assert assistant["uncertain"] is True
    assert [evidence["type"] for evidence in assistant["evidence"]] == ["bill_snapshot"]
    assert "supporting usage data is unavailable" in assistant["content"]
    assert "United States" not in assistant["content"]
    assert exchanges.saved[0].charge_snapshot is None


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
