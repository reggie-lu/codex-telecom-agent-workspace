import os
from collections.abc import Iterator
from datetime import UTC, datetime
from hashlib import sha256
from uuid import UUID

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, delete, inspect, select
from sqlalchemy.orm import Session, sessionmaker

from telecom_agent.adapters.postgres.health import SqlAlchemyDatabaseHealth
from telecom_agent.adapters.postgres.models import ConversationRecord, SyntheticCustomerRecord
from telecom_agent.adapters.postgres.repositories import (
    SqlAlchemyConversationRepository,
    SqlAlchemyCustomerIdentityRepository,
)
from telecom_agent.adapters.postgres.seeding import (
    SeedResult,
    seed_synthetic_customer,
)
from telecom_agent.api.composition import create_postgres_app
from telecom_agent.development import DEVELOPMENT_CUSTOMER
from telecom_agent.domain.conversations import Conversation, ConversationStatus

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
        session.execute(delete(ConversationRecord))
        session.execute(delete(SyntheticCustomerRecord))
    yield
    with session_factory.begin() as session:
        session.execute(delete(ConversationRecord))
        session.execute(delete(SyntheticCustomerRecord))


def test_initial_migration_creates_customer_and_conversation_tables(
    migrated_engine: Engine,
) -> None:
    inspector = inspect(migrated_engine)

    assert {"synthetic_customers", "conversations"} <= set(inspector.get_table_names())
    customer_columns = {column["name"] for column in inspector.get_columns("synthetic_customers")}
    assert customer_columns == {"id", "display_name", "token_hash", "created_at"}


def test_repositories_authenticate_hashed_token_and_persist_customer_owned_conversation(
    session_factory: sessionmaker[Session],
) -> None:
    raw_token = "synthetic-alice-token"
    customer_id = UUID("10000000-0000-0000-0000-000000000001")
    conversation_id = UUID("20000000-0000-0000-0000-000000000001")
    created_at = datetime(2026, 8, 26, 12, 0, tzinfo=UTC)
    token_hash = sha256(raw_token.encode()).hexdigest()
    with session_factory.begin() as session:
        session.add(
            SyntheticCustomerRecord(
                id=customer_id,
                display_name="Synthetic Alice",
                token_hash=token_hash,
                created_at=created_at,
            )
        )

    identities = SqlAlchemyCustomerIdentityRepository(session_factory)
    conversations = SqlAlchemyConversationRepository(session_factory)

    assert identities.find_customer_id(token_hash) == customer_id
    conversations.add(
        Conversation(
            id=conversation_id,
            customer_id=customer_id,
            status=ConversationStatus.OPEN,
            created_at=created_at,
        )
    )

    with session_factory() as session:
        saved = session.scalar(
            select(ConversationRecord).where(ConversationRecord.id == conversation_id)
        )
        stored_customer = session.get(SyntheticCustomerRecord, customer_id)

    assert saved is not None
    assert saved.customer_id == customer_id
    assert saved.status == ConversationStatus.OPEN.value
    assert stored_customer is not None
    assert stored_customer.token_hash == token_hash
    assert stored_customer.token_hash != raw_token


def test_conversation_api_persists_to_postgres(
    session_factory: sessionmaker[Session],
) -> None:
    raw_token = "synthetic-bob-token"
    customer_id = UUID("10000000-0000-0000-0000-000000000002")
    with session_factory.begin() as session:
        session.add(
            SyntheticCustomerRecord(
                id=customer_id,
                display_name="Synthetic Bob",
                token_hash=sha256(raw_token.encode()).hexdigest(),
                created_at=datetime(2026, 8, 26, 12, 30, tzinfo=UTC),
            )
        )

    assert TEST_DATABASE_URL is not None
    app = create_postgres_app(TEST_DATABASE_URL)
    response = TestClient(app).post(
        "/v1/conversations",
        headers={"Authorization": f"Bearer {raw_token}"},
    )

    assert response.status_code == 201
    conversation_id = UUID(response.json()["id"])
    with session_factory() as session:
        saved = session.get(ConversationRecord, conversation_id)

    assert saved is not None
    assert saved.customer_id == customer_id


def test_development_seed_is_idempotent_and_never_stores_raw_token(
    session_factory: sessionmaker[Session],
) -> None:
    first = seed_synthetic_customer(session_factory, DEVELOPMENT_CUSTOMER)
    second = seed_synthetic_customer(session_factory, DEVELOPMENT_CUSTOMER)

    with session_factory() as session:
        customers = list(session.scalars(select(SyntheticCustomerRecord)))

    assert first is SeedResult.CREATED
    assert second is SeedResult.EXISTING
    assert len(customers) == 1
    assert customers[0].id == DEVELOPMENT_CUSTOMER.customer_id
    assert customers[0].display_name == "Synthetic Alice"
    assert customers[0].token_hash == sha256(DEVELOPMENT_CUSTOMER.raw_token.encode()).hexdigest()
    assert customers[0].token_hash != DEVELOPMENT_CUSTOMER.raw_token


def test_postgres_health_check_reports_reachable_database(migrated_engine: Engine) -> None:
    assert SqlAlchemyDatabaseHealth(migrated_engine).is_healthy() is True
