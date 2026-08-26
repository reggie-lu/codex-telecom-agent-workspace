import os
from collections.abc import Iterator
from datetime import UTC, datetime
from uuid import UUID

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, delete, inspect, select
from sqlalchemy.orm import Session, sessionmaker

from telecom_agent.adapters.postgres.models import (
    ConversationRecord,
    MessagePlanEvidenceRecord,
    MessageRecord,
    PlanSnapshotRecord,
    SyntheticCustomerRecord,
)
from telecom_agent.adapters.postgres.repositories import (
    SqlAlchemyConversationRepository,
)
from telecom_agent.adapters.postgres.seeding import seed_synthetic_customer
from telecom_agent.api.composition import create_postgres_app
from telecom_agent.development import DEVELOPMENT_CUSTOMER
from telecom_agent.domain.messages import AnswerStatus, MessageRole

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    TEST_DATABASE_URL is None,
    reason="TEST_DATABASE_URL is required for PostgreSQL integration tests",
)


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
        session.execute(delete(MessagePlanEvidenceRecord))
        session.execute(delete(MessageRecord))
        session.execute(delete(PlanSnapshotRecord))
        session.execute(delete(ConversationRecord))
        session.execute(delete(SyntheticCustomerRecord))
    yield


def test_second_migration_creates_message_and_plan_snapshot_schema(
    migrated_engine: Engine,
) -> None:
    inspector = inspect(migrated_engine)

    assert {"plan_snapshots", "messages", "message_plan_evidence"} <= set(
        inspector.get_table_names()
    )
    message_columns = {column["name"] for column in inspector.get_columns("messages")}
    assert message_columns == {
        "id",
        "conversation_id",
        "role",
        "content",
        "created_at",
        "answer_status",
        "uncertain",
    }


def test_conversation_ownership_is_customer_scoped(
    session_factory: sessionmaker[Session],
) -> None:
    customer_id = DEVELOPMENT_CUSTOMER.customer_id
    other_customer_id = UUID("10000000-0000-0000-0000-000000000099")
    conversation_id = UUID("20000000-0000-0000-0000-000000000001")
    with session_factory.begin() as session:
        session.add_all(
            [
                SyntheticCustomerRecord(
                    id=customer_id,
                    display_name="Synthetic Alice",
                    token_hash="a" * 64,
                    created_at=datetime(2026, 8, 26, 6, 0, tzinfo=UTC),
                ),
                SyntheticCustomerRecord(
                    id=other_customer_id,
                    display_name="Synthetic Other",
                    token_hash="b" * 64,
                    created_at=datetime(2026, 8, 26, 6, 0, tzinfo=UTC),
                ),
            ]
        )
        session.flush()
        session.add(
            ConversationRecord(
                id=conversation_id,
                customer_id=customer_id,
                status="open",
                created_at=datetime(2026, 8, 26, 6, 1, tzinfo=UTC),
            )
        )

    repository = SqlAlchemyConversationRepository(session_factory)

    assert repository.is_owned_by(conversation_id, customer_id) is True
    assert repository.is_owned_by(conversation_id, other_customer_id) is False
    assert (
        repository.is_owned_by(
            UUID("ffffffff-ffff-ffff-ffff-ffffffffffff"),
            customer_id,
        )
        is False
    )


def test_postgres_composition_persists_grounded_message_exchange(
    session_factory: sessionmaker[Session],
) -> None:
    assert TEST_DATABASE_URL is not None
    seed_synthetic_customer(session_factory, DEVELOPMENT_CUSTOMER)
    client = TestClient(create_postgres_app(TEST_DATABASE_URL))
    headers = {"Authorization": f"Bearer {DEVELOPMENT_CUSTOMER.raw_token}"}
    conversation_response = client.post("/v1/conversations", headers=headers)
    conversation_id = UUID(conversation_response.json()["id"])

    response = client.post(
        f"/v1/conversations/{conversation_id}/messages",
        headers=headers,
        json={"content": "What is my current plan?"},
    )

    assert response.status_code == 201
    body = response.json()
    user_message_id = UUID(body["user_message"]["id"])
    assistant_message_id = UUID(body["assistant_message"]["id"])
    evidence_id = UUID(body["assistant_message"]["evidence"][0]["id"])
    with session_factory() as session:
        user_message = session.get(MessageRecord, user_message_id)
        assistant_message = session.get(MessageRecord, assistant_message_id)
        snapshot = session.get(PlanSnapshotRecord, evidence_id)
        evidence = session.scalar(
            select(MessagePlanEvidenceRecord).where(
                MessagePlanEvidenceRecord.message_id == assistant_message_id
            )
        )

    assert user_message is not None
    assert user_message.conversation_id == conversation_id
    assert user_message.role == MessageRole.USER.value
    assert user_message.answer_status is None
    assert user_message.uncertain is None
    assert assistant_message is not None
    assert assistant_message.role == MessageRole.ASSISTANT.value
    assert assistant_message.answer_status == AnswerStatus.GROUNDED.value
    assert assistant_message.uncertain is False
    assert snapshot is not None
    assert snapshot.customer_id == DEVELOPMENT_CUSTOMER.customer_id
    assert snapshot.plan_code == "SYN-KDDI-5G-20"
    assert str(snapshot.recurring_charge) == "4500.00"
    assert snapshot.currency == "JPY"
    assert evidence is not None
    assert evidence.plan_snapshot_id == snapshot.id
