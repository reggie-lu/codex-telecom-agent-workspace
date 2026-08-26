import os
from collections.abc import Iterator
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, delete, inspect, select
from sqlalchemy.orm import Session, sessionmaker

from telecom_agent.adapters.postgres.models import (
    BillLineItemRecord,
    BillSnapshotRecord,
    ChargeEvidenceSnapshotRecord,
    ConversationRecord,
    MessageBillEvidenceRecord,
    MessageChargeEvidenceRecord,
    MessagePlanEvidenceRecord,
    MessageRecord,
    PlanSnapshotRecord,
    SyntheticCustomerRecord,
)
from telecom_agent.adapters.postgres.repositories import (
    SqlAlchemyConversationRepository,
)
from telecom_agent.adapters.postgres.seeding import seed_synthetic_customer
from telecom_agent.adapters.sambanova.current_plan_answers import SambaNovaSettings
from telecom_agent.api.composition import create_postgres_app
from telecom_agent.development import DEVELOPMENT_CUSTOMER
from telecom_agent.domain.messages import AnswerStatus, MessageRole
from tests.fakes import DeterministicAnswerGenerator

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
TEST_SAMBANOVA_SETTINGS = SambaNovaSettings(
    base_url="https://example.invalid/v1",
    model="MiniMax-M3",
    api_key="test-key",
)
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
        session.execute(delete(MessageChargeEvidenceRecord))
        session.execute(delete(MessageBillEvidenceRecord))
        session.execute(delete(MessagePlanEvidenceRecord))
        session.execute(delete(MessageRecord))
        session.execute(delete(ChargeEvidenceSnapshotRecord))
        session.execute(delete(BillLineItemRecord))
        session.execute(delete(BillSnapshotRecord))
        session.execute(delete(PlanSnapshotRecord))
        session.execute(delete(ConversationRecord))
        session.execute(delete(SyntheticCustomerRecord))
    yield


def test_migrations_create_message_plan_and_bill_snapshot_schema(
    migrated_engine: Engine,
) -> None:
    inspector = inspect(migrated_engine)

    assert {
        "plan_snapshots",
        "messages",
        "message_plan_evidence",
        "bill_snapshots",
        "bill_line_items",
        "message_bill_evidence",
        "charge_evidence_snapshots",
        "message_charge_evidence",
    } <= set(inspector.get_table_names())
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
    bill_columns = {column["name"] for column in inspector.get_columns("bill_snapshots")}
    assert bill_columns == {
        "id",
        "customer_id",
        "period_start",
        "period_end",
        "total",
        "currency",
        "retrieved_at",
        "source_version",
        "availability",
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
    client = TestClient(
        create_postgres_app(
            TEST_DATABASE_URL,
            TEST_SAMBANOVA_SETTINGS,
            answer_generator=DeterministicAnswerGenerator(),
        )
    )
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


def test_postgres_composition_persists_latest_bill_and_line_item_evidence(
    session_factory: sessionmaker[Session],
) -> None:
    assert TEST_DATABASE_URL is not None
    seed_synthetic_customer(session_factory, DEVELOPMENT_CUSTOMER)
    client = TestClient(
        create_postgres_app(
            TEST_DATABASE_URL,
            TEST_SAMBANOVA_SETTINGS,
            answer_generator=DeterministicAnswerGenerator(),
        )
    )
    headers = {"Authorization": f"Bearer {DEVELOPMENT_CUSTOMER.raw_token}"}
    conversation_response = client.post("/v1/conversations", headers=headers)
    conversation_id = UUID(conversation_response.json()["id"])

    response = client.post(
        f"/v1/conversations/{conversation_id}/messages",
        headers=headers,
        json={"content": "What is my latest bill?"},
    )

    assert response.status_code == 201
    body = response.json()
    assistant_message_id = UUID(body["assistant_message"]["id"])
    evidence_id = UUID(body["assistant_message"]["evidence"][0]["id"])
    with session_factory() as session:
        snapshot = session.get(BillSnapshotRecord, evidence_id)
        line_items = session.scalars(
            select(BillLineItemRecord)
            .where(BillLineItemRecord.bill_snapshot_id == evidence_id)
            .order_by(BillLineItemRecord.position)
        ).all()
        evidence = session.scalar(
            select(MessageBillEvidenceRecord).where(
                MessageBillEvidenceRecord.message_id == assistant_message_id
            )
        )

    assert snapshot is not None
    assert snapshot.customer_id == DEVELOPMENT_CUSTOMER.customer_id
    assert snapshot.period_start.isoformat() == "2026-07-01"
    assert snapshot.period_end.isoformat() == "2026-07-31"
    assert snapshot.total == Decimal("6930.00")
    assert snapshot.currency == "JPY"
    assert [(item.description, item.amount) for item in line_items] == [
        ("Monthly mobile service", Decimal("4500.00")),
        ("Domestic calls", Decimal("600.00")),
        ("International roaming data", Decimal("1200.00")),
        ("Taxes and fees", Decimal("630.00")),
    ]
    assert evidence is not None
    assert evidence.bill_snapshot_id == snapshot.id


def test_postgres_composition_persists_grounded_charge_investigation_evidence(
    session_factory: sessionmaker[Session],
) -> None:
    assert TEST_DATABASE_URL is not None
    seed_synthetic_customer(session_factory, DEVELOPMENT_CUSTOMER)
    client = TestClient(
        create_postgres_app(
            TEST_DATABASE_URL,
            TEST_SAMBANOVA_SETTINGS,
            answer_generator=DeterministicAnswerGenerator(),
        )
    )
    headers = {"Authorization": f"Bearer {DEVELOPMENT_CUSTOMER.raw_token}"}
    conversation_response = client.post("/v1/conversations", headers=headers)
    conversation_id = UUID(conversation_response.json()["id"])

    response = client.post(
        f"/v1/conversations/{conversation_id}/messages",
        headers=headers,
        json={"content": "Why is my latest bill higher?"},
    )

    assert response.status_code == 201
    body = response.json()
    assistant_message_id = UUID(body["assistant_message"]["id"])
    evidence_by_type = {
        evidence["type"]: UUID(evidence["id"])
        for evidence in body["assistant_message"]["evidence"]
    }
    charge_id = evidence_by_type["charge_snapshot"]
    with session_factory() as session:
        charge = session.get(ChargeEvidenceSnapshotRecord, charge_id)
        evidence = session.scalar(
            select(MessageChargeEvidenceRecord).where(
                MessageChargeEvidenceRecord.message_id == assistant_message_id
            )
        )

    assert charge is not None
    assert charge.customer_id == DEVELOPMENT_CUSTOMER.customer_id
    assert charge.line_item_code == "roaming_data"
    assert charge.amount == Decimal("1200.00")
    assert charge.currency == "JPY"
    assert charge.occurred_on.isoformat() == "2026-07-18"
    assert charge.location == "United States"
    assert charge.service_name == "Synthetic KDDI Overseas Data Day Pass"
    assert charge.state == "confirmed"
    assert evidence is not None
    assert evidence.charge_snapshot_id == charge.id


def test_postgres_api_returns_complete_ordered_history_with_all_evidence_types(
    session_factory: sessionmaker[Session],
) -> None:
    assert TEST_DATABASE_URL is not None
    seed_synthetic_customer(session_factory, DEVELOPMENT_CUSTOMER)
    client = TestClient(
        create_postgres_app(
            TEST_DATABASE_URL,
            TEST_SAMBANOVA_SETTINGS,
            answer_generator=DeterministicAnswerGenerator(),
        )
    )
    headers = {"Authorization": f"Bearer {DEVELOPMENT_CUSTOMER.raw_token}"}
    conversation_response = client.post("/v1/conversations", headers=headers)
    conversation_id = UUID(conversation_response.json()["id"])
    questions = (
        "What is my current plan?",
        "What is my latest bill?",
        "Why is my latest bill higher?",
    )
    for question in questions:
        response = client.post(
            f"/v1/conversations/{conversation_id}/messages",
            headers=headers,
            json={"content": question},
        )
        assert response.status_code == 201

    response = client.get(
        f"/v1/conversations/{conversation_id}",
        headers=headers,
    )

    assert response.status_code == 200
    history = response.json()
    assert history["id"] == str(conversation_id)
    assert history["status"] == "open"
    assert len(history["messages"]) == 6
    assert [history["messages"][index]["content"] for index in (0, 2, 4)] == list(questions)
    assert [history["messages"][index]["role"] for index in range(6)] == [
        "user",
        "assistant",
        "user",
        "assistant",
        "user",
        "assistant",
    ]
    assert [item["type"] for item in history["messages"][1]["evidence"]] == [
        "plan_snapshot"
    ]
    assert [item["type"] for item in history["messages"][3]["evidence"]] == [
        "bill_snapshot"
    ]
    assert [item["type"] for item in history["messages"][5]["evidence"]] == [
        "bill_snapshot",
        "charge_snapshot",
    ]
