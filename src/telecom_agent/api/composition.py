from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from telecom_agent.adapters.escalation_mock.handoff import DeterministicMockHandoff
from telecom_agent.adapters.kddi_mock.charge_evidence import (
    SyntheticKddiChargeEvidenceProvider,
)
from telecom_agent.adapters.kddi_mock.current_plans import SyntheticKddiCurrentPlanProvider
from telecom_agent.adapters.kddi_mock.latest_bills import SyntheticKddiLatestBillProvider
from telecom_agent.adapters.kddi_mock.plan_catalog import SyntheticKddiPlanCatalogProvider
from telecom_agent.adapters.postgres.health import SqlAlchemyDatabaseHealth
from telecom_agent.adapters.postgres.repositories import (
    SqlAlchemyConversationRepository,
    SqlAlchemyCustomerIdentityRepository,
    SqlAlchemyEscalationRepository,
    SqlAlchemyMessageExchangeRepository,
)
from telecom_agent.adapters.sambanova.current_plan_answers import (
    SambaNovaCurrentPlanAnswerGenerator,
    SambaNovaSettings,
)
from telecom_agent.api.app import create_app
from telecom_agent.ports.escalations import HumanHandoff
from telecom_agent.ports.messages import CurrentPlanAnswerGenerator


def create_postgres_app(
    database_url: str,
    sambanova_settings: SambaNovaSettings,
    *,
    answer_generator: CurrentPlanAnswerGenerator | None = None,
    handoff: HumanHandoff | None = None,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> FastAPI:
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
        escalations=SqlAlchemyEscalationRepository(session_factory),
        handoff=handoff or DeterministicMockHandoff(),
        database_health=SqlAlchemyDatabaseHealth(engine),
        current_plans=SyntheticKddiCurrentPlanProvider(),
        latest_bills=SyntheticKddiLatestBillProvider(),
        charge_evidence=SyntheticKddiChargeEvidenceProvider(),
        plan_catalog=SyntheticKddiPlanCatalogProvider(),
        answer_generator=(
            answer_generator or SambaNovaCurrentPlanAnswerGenerator(sambanova_settings)
        ),
        exchanges=SqlAlchemyMessageExchangeRepository(session_factory),
        clock=clock,
        lifespan=lifespan,
    )
