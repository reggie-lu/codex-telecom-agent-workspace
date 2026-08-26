from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from telecom_agent.api.app import create_app
from telecom_agent.domain.conversations import Conversation
from tests.fakes import DeterministicAnswerGenerator


class UnusedCustomerIdentities:
    def find_customer_id(self, _token_hash: str) -> UUID | None:
        return None


class UnusedConversations:
    def add(self, _conversation: Conversation) -> None:
        raise AssertionError("The health endpoint must not access conversations")

    def is_owned_by(self, _conversation_id: UUID, _customer_id: UUID) -> bool:
        raise AssertionError("The health endpoint must not access conversations")


class UnusedCurrentPlans:
    def get_current_plan(self, _customer_id: UUID) -> None:
        raise AssertionError("The health endpoint must not access plans")


class UnusedExchanges:
    def add(self, _exchange: object) -> None:
        raise AssertionError("The health endpoint must not access messages")


class StubDatabaseHealth:
    def __init__(self, healthy: bool) -> None:
        self.healthy = healthy

    def is_healthy(self) -> bool:
        return self.healthy


@pytest.mark.parametrize(
    ("healthy", "expected_status", "expected_body"),
    [
        (True, 200, {"status": "ok", "database": "ok"}),
        (
            False,
            503,
            {"status": "unavailable", "database": "unavailable"},
        ),
    ],
)
def test_health_reports_only_approved_database_status(
    healthy: bool,
    expected_status: int,
    expected_body: dict[str, str],
) -> None:
    app = create_app(
        customer_identities=UnusedCustomerIdentities(),
        conversations=UnusedConversations(),
        database_health=StubDatabaseHealth(healthy),
        current_plans=UnusedCurrentPlans(),
        answer_generator=DeterministicAnswerGenerator(),
        exchanges=UnusedExchanges(),
    )

    response = TestClient(app).get("/health")

    assert response.status_code == expected_status
    assert response.json() == expected_body
    assert set(response.json()) == {"status", "database"}


def test_health_openapi_documents_unavailable_response() -> None:
    app = create_app(
        customer_identities=UnusedCustomerIdentities(),
        conversations=UnusedConversations(),
        database_health=StubDatabaseHealth(True),
        current_plans=UnusedCurrentPlans(),
        answer_generator=DeterministicAnswerGenerator(),
        exchanges=UnusedExchanges(),
    )

    schema = TestClient(app).get("/openapi.json").json()

    responses = schema["paths"]["/health"]["get"]["responses"]
    assert "200" in responses
    assert responses["503"]["description"] == "PostgreSQL is unavailable"
