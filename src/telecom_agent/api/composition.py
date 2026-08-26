from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from telecom_agent.adapters.kddi_mock.current_plans import SyntheticKddiCurrentPlanProvider
from telecom_agent.adapters.postgres.health import SqlAlchemyDatabaseHealth
from telecom_agent.adapters.postgres.repositories import (
    SqlAlchemyConversationRepository,
    SqlAlchemyCustomerIdentityRepository,
    SqlAlchemyMessageExchangeRepository,
)
from telecom_agent.api.app import create_app


def create_postgres_app(database_url: str) -> FastAPI:
    """Compose the API with PostgreSQL-backed adapters."""
    engine = create_engine(database_url)
    session_factory = sessionmaker[Session](engine, expire_on_commit=False)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
            engine.dispose()

    return create_app(
        customer_identities=SqlAlchemyCustomerIdentityRepository(session_factory),
        conversations=SqlAlchemyConversationRepository(session_factory),
        database_health=SqlAlchemyDatabaseHealth(engine),
        current_plans=SyntheticKddiCurrentPlanProvider(),
        exchanges=SqlAlchemyMessageExchangeRepository(session_factory),
        lifespan=lifespan,
    )
