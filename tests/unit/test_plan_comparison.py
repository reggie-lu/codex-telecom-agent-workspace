from collections.abc import Iterator
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import cast
from uuid import UUID

import pytest

from telecom_agent.domain.comparisons import CatalogOfferDetails, PlanCatalogDetails
from telecom_agent.domain.messages import AnswerStatus, EvidenceType, MessageExchange
from telecom_agent.domain.plans import CurrentPlanDetails
from telecom_agent.services.send_support_message import SendSupportMessageService
from tests.fakes import DeterministicAnswerGenerator

CUSTOMER_ID = UUID("10000000-0000-0000-0000-000000000001")
CONVERSATION_ID = UUID("20000000-0000-0000-0000-000000000001")
USER_MESSAGE_ID = UUID("30000000-0000-0000-0000-000000000001")
COMPARISON_SNAPSHOT_ID = UUID("40000000-0000-0000-0000-000000000001")
OFFER_IDS = (
    UUID("41000000-0000-0000-0000-000000000001"),
    UUID("41000000-0000-0000-0000-000000000002"),
    UUID("41000000-0000-0000-0000-000000000003"),
)
ASSISTANT_MESSAGE_ID = UUID("50000000-0000-0000-0000-000000000001")
NOW = datetime(2026, 8, 29, 6, 0, tzinfo=UTC)
DEFAULT_CATALOG = object()

CURRENT_PLAN = CurrentPlanDetails(
    plan_code="SYN-KDDI-5G-20",
    plan_name="Synthetic KDDI 5G 20GB",
    data_allowance_gb=20,
    recurring_charge=Decimal("4500.00"),
    currency="JPY",
    effective_from=date(2026, 8, 1),
    source_version="synthetic-kddi-v1",
)


def catalog(*, as_of: date = date(2026, 8, 28)) -> PlanCatalogDetails:
    return PlanCatalogDetails(
        offers=(
            CatalogOfferDetails(
                "SYN-KDDI-LITE-5",
                "Synthetic KDDI Lite 5GB",
                5,
                Decimal("2800.00"),
                "JPY",
                date(2026, 8, 28),
            ),
            CatalogOfferDetails(
                "SYN-KDDI-PLUS-30",
                "Synthetic KDDI Plus 30GB",
                30,
                Decimal("5200.00"),
                "JPY",
                date(2026, 8, 28),
            ),
            CatalogOfferDetails(
                "SYN-KDDI-MAX-100",
                "Synthetic KDDI Max 100GB",
                100,
                Decimal("7500.00"),
                "JPY",
                date(2026, 8, 28),
            ),
        ),
        as_of=as_of,
        source_version="synthetic-kddi-catalog-2026-08-28",
    )


class OwnedConversation:
    def is_owned_by(self, _conversation_id: UUID, _customer_id: UUID) -> bool:
        return True


class StubCurrentPlans:
    def __init__(self, plan: CurrentPlanDetails | None = CURRENT_PLAN) -> None:
        self.plan = plan

    def get_current_plan(self, _customer_id: UUID) -> CurrentPlanDetails | None:
        return self.plan


class StubCatalog:
    def __init__(self, value: PlanCatalogDetails | None) -> None:
        self.value = value

    def get_plan_catalog(self) -> PlanCatalogDetails | None:
        return self.value


class RecordingExchanges:
    def __init__(self) -> None:
        self.saved: list[MessageExchange] = []

    def add(self, exchange: MessageExchange) -> None:
        self.saved.append(exchange)


def build_service(
    *,
    current_plan: CurrentPlanDetails | None = CURRENT_PLAN,
    plan_catalog: PlanCatalogDetails | None | object = DEFAULT_CATALOG,
    now: datetime = NOW,
    ids: list[UUID] | None = None,
) -> tuple[SendSupportMessageService, RecordingExchanges]:
    generated_ids: Iterator[UUID] = iter(
        ids
        or [
            USER_MESSAGE_ID,
            COMPARISON_SNAPSHOT_ID,
            *OFFER_IDS,
            ASSISTANT_MESSAGE_ID,
        ]
    )
    exchanges = RecordingExchanges()
    selected_catalog = (
        catalog()
        if plan_catalog is DEFAULT_CATALOG
        else cast(PlanCatalogDetails | None, plan_catalog)
    )
    service = SendSupportMessageService(
        conversations=OwnedConversation(),
        current_plans=StubCurrentPlans(current_plan),
        plan_catalog=StubCatalog(selected_catalog),
        answer_generator=DeterministicAnswerGenerator(),
        exchanges=exchanges,
        id_factory=lambda: next(generated_ids),
        clock=lambda: now,
    )
    return service, exchanges


@pytest.mark.parametrize(
    "question",
    [
        "Compare my current plan.",
        "What other plans are there?",
        "Show me available plan options.",
    ],
)
def test_comparison_intents_return_complete_grounded_comparison(question: str) -> None:
    service, exchanges = build_service()

    exchange = service.execute(
        customer_id=CUSTOMER_ID,
        conversation_id=CONVERSATION_ID,
        content=question,
    )

    assistant = exchange.assistant_message
    assert assistant.answer_status is AnswerStatus.GROUNDED
    assert assistant.uncertain is False
    assert len(assistant.evidence) == 1
    assert assistant.evidence[0].type is EvidenceType.PLAN_COMPARISON_SNAPSHOT
    assert assistant.evidence[0].id == COMPARISON_SNAPSHOT_ID
    assert exchange.comparison_snapshot is not None
    assert exchange.comparison_snapshot.eligibility_verified is False
    assert [offer.recurring_charge_delta for offer in exchange.comparison_snapshot.offers] == [
        Decimal("-1700.00"),
        Decimal("700.00"),
        Decimal("3000.00"),
    ]
    assert [offer.data_allowance_delta_gb for offer in exchange.comparison_snapshot.offers] == [
        -15,
        10,
        80,
    ]
    for required in (
        "Synthetic KDDI 5G 20GB",
        "20 GB",
        "JPY 4,500",
        "Synthetic KDDI Lite 5GB",
        "5 GB",
        "JPY 2,800",
        "JPY 1,700 less",
        "15 GB less",
        "Synthetic KDDI Plus 30GB",
        "30 GB",
        "JPY 5,200",
        "JPY 700 more",
        "10 GB more",
        "Synthetic KDDI Max 100GB",
        "100 GB",
        "JPY 7,500",
        "JPY 3,000 more",
        "80 GB more",
        "August 28, 2026",
        "customer-specific eligibility is not verified",
        "not total bills or projected savings",
    ):
        assert required in assistant.content
    assert exchanges.saved == [exchange]


@pytest.mark.parametrize(
    ("now", "expected_status"),
    [
        (datetime(2026, 9, 27, 23, 59, tzinfo=UTC), AnswerStatus.GROUNDED),
        (datetime(2026, 9, 28, 0, 0, tzinfo=UTC), AnswerStatus.UNAVAILABLE),
    ],
)
def test_catalog_freshness_boundary(now: datetime, expected_status: AnswerStatus) -> None:
    service, _exchanges = build_service(
        now=now,
        ids=(
            [USER_MESSAGE_ID, COMPARISON_SNAPSHOT_ID, *OFFER_IDS, ASSISTANT_MESSAGE_ID]
            if expected_status is AnswerStatus.GROUNDED
            else [USER_MESSAGE_ID, ASSISTANT_MESSAGE_ID]
        ),
    )

    exchange = service.execute(
        customer_id=CUSTOMER_ID,
        conversation_id=CONVERSATION_ID,
        content="Compare my plan",
    )

    assert exchange.assistant_message.answer_status is expected_status


@pytest.mark.parametrize(
    ("current_plan", "plan_catalog"),
    [
        (None, catalog()),
        (CURRENT_PLAN, None),
        (
            CURRENT_PLAN,
            PlanCatalogDetails(
                offers=(catalog().offers[0], catalog().offers[0], catalog().offers[2]),
                as_of=date(2026, 8, 28),
                source_version="synthetic-kddi-catalog-2026-08-28",
            ),
        ),
    ],
)
def test_unsafe_inputs_fail_closed_without_comparison_evidence(
    current_plan: CurrentPlanDetails | None,
    plan_catalog: PlanCatalogDetails | None,
) -> None:
    service, exchanges = build_service(
        current_plan=current_plan,
        plan_catalog=plan_catalog,
        ids=[USER_MESSAGE_ID, ASSISTANT_MESSAGE_ID],
    )

    exchange = service.execute(
        customer_id=CUSTOMER_ID,
        conversation_id=CONVERSATION_ID,
        content="Show me other plans",
    )

    assert exchange.assistant_message.answer_status is AnswerStatus.UNAVAILABLE
    assert exchange.assistant_message.uncertain is True
    assert exchange.assistant_message.evidence == ()
    assert exchange.comparison_snapshot is None
    assert "request human support" in exchange.assistant_message.content
    assert exchanges.saved == [exchange]
