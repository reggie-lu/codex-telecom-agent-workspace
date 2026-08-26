import os
from collections.abc import Iterator
from typing import Any, cast
from uuid import UUID

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, delete, inspect, select
from sqlalchemy.orm import Session, sessionmaker

from telecom_agent.adapters.postgres.models import (
    ConversationRecord,
    EscalationRecord,
    SyntheticCustomerRecord,
)
from telecom_agent.adapters.postgres.seeding import seed_synthetic_customer
from telecom_agent.adapters.sambanova.current_plan_answers import SambaNovaSettings
from telecom_agent.api.composition import create_postgres_app
from telecom_agent.development import DEVELOPMENT_CUSTOMER
from telecom_agent.domain.escalations import Escalation, HandoffOutcome
from tests.fakes import DeterministicAnswerGenerator

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
SETTINGS = SambaNovaSettings("https://example.invalid/v1", "MiniMax-M3", "test-key")
pytestmark = pytest.mark.skipif(
    TEST_DATABASE_URL is None,
    reason="TEST_DATABASE_URL is required for PostgreSQL integration tests",
)


class FailedHandoff:
    def submit(self, _escalation: Escalation) -> HandoffOutcome:
        return HandoffOutcome.FAILED


@pytest.fixture(scope="module")
def migrated_engine() -> Iterator[Engine]:
    assert TEST_DATABASE_URL is not None
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    engine = create_engine(TEST_DATABASE_URL)
    try:
        yield engine
    finally:
        engine.dispose()
        command.downgrade(config, "base")


@pytest.fixture
def session_factory(migrated_engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(migrated_engine, expire_on_commit=False)


@pytest.fixture(autouse=True)
def clean_records(session_factory: sessionmaker[Session]) -> Iterator[None]:
    with session_factory.begin() as session:
        session.execute(delete(EscalationRecord))
        session.execute(delete(ConversationRecord))
        session.execute(delete(SyntheticCustomerRecord))
    yield


def test_migration_and_composed_api_preserve_context_and_prevent_duplicates(
    migrated_engine: Engine,
    session_factory: sessionmaker[Session],
) -> None:
    assert "escalations" in inspect(migrated_engine).get_table_names()
    seed_synthetic_customer(session_factory, DEVELOPMENT_CUSTOMER)
    assert TEST_DATABASE_URL is not None
    api = TestClient(
        create_postgres_app(
            TEST_DATABASE_URL,
            SETTINGS,
            answer_generator=DeterministicAnswerGenerator(),
        )
    )
    headers = {"Authorization": f"Bearer {DEVELOPMENT_CUSTOMER.raw_token}"}
    conversation_id = api.post("/v1/conversations", headers=headers).json()["id"]
    message = api.post(
        f"/v1/conversations/{conversation_id}/messages",
        headers=headers,
        json={"content": "Why is my latest bill higher?"},
    )
    assert message.status_code == 201

    created = api.post(
        f"/v1/conversations/{conversation_id}/escalations",
        headers=headers,
        json={"reason": "I do not recognize this roaming charge."},
    )
    assert created.status_code == 201
    assert created.json()["status"] == "queued"
    escalation_id = UUID(created.json()["id"])
    assert api.get(f"/v1/escalations/{escalation_id}", headers=headers).json() == created.json()
    duplicate = api.post(
        f"/v1/conversations/{conversation_id}/escalations",
        headers=headers,
        json={"reason": "Please open another ticket."},
    )
    assert duplicate.status_code == 409

    with session_factory() as session:
        record = session.scalar(select(EscalationRecord).where(EscalationRecord.id == escalation_id))
    assert record is not None
    context = cast(dict[str, Any], record.handoff_context["conversation"])
    assert len(context["messages"]) == 2
    assert [item["type"] for item in context["messages"][1]["evidence"]] == [
        "bill_snapshot",
        "charge_snapshot",
    ]


def test_failed_handoff_is_durable_and_does_not_block_retry(
    session_factory: sessionmaker[Session],
) -> None:
    seed_synthetic_customer(session_factory, DEVELOPMENT_CUSTOMER)
    assert TEST_DATABASE_URL is not None
    headers = {"Authorization": f"Bearer {DEVELOPMENT_CUSTOMER.raw_token}"}
    failed_api = TestClient(
        create_postgres_app(
            TEST_DATABASE_URL,
            SETTINGS,
            answer_generator=DeterministicAnswerGenerator(),
            handoff=FailedHandoff(),
        )
    )
    conversation_id = failed_api.post("/v1/conversations", headers=headers).json()["id"]
    failed = failed_api.post(
        f"/v1/conversations/{conversation_id}/escalations",
        headers=headers,
        json={"reason": "Please help."},
    )
    assert failed.status_code == 201
    assert failed.json()["status"] == "failed"
    assert failed.json()["next_step"] == "Please try requesting human support again later."

    accepted_api = TestClient(
        create_postgres_app(
            TEST_DATABASE_URL,
            SETTINGS,
            answer_generator=DeterministicAnswerGenerator(),
        )
    )
    retry = accepted_api.post(
        f"/v1/conversations/{conversation_id}/escalations",
        headers=headers,
        json={"reason": "Please try the handoff again."},
    )
    assert retry.status_code == 201
    assert retry.json()["status"] == "queued"
