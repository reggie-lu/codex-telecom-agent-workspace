from collections.abc import Iterator
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

import pytest

from telecom_agent.domain.messages import AnswerStatus, EvidenceType, MessageExchange, MessageRole
from telecom_agent.domain.plans import CurrentPlanDetails
from telecom_agent.services.send_current_plan_message import (
    ConversationNotFoundError,
    SendCurrentPlanMessageService,
)

CUSTOMER_ID = UUID("10000000-0000-0000-0000-000000000001")
CONVERSATION_ID = UUID("20000000-0000-0000-0000-000000000001")
USER_MESSAGE_ID = UUID("30000000-0000-0000-0000-000000000001")
PLAN_SNAPSHOT_ID = UUID("40000000-0000-0000-0000-000000000001")
ASSISTANT_MESSAGE_ID = UUID("50000000-0000-0000-0000-000000000001")
NOW = datetime(2026, 8, 26, 6, 0, tzinfo=UTC)

AVAILABLE_PLAN = CurrentPlanDetails(
    plan_code="SYN-KDDI-5G-20",
    plan_name="Synthetic KDDI 5G 20GB",
    data_allowance_gb=20,
    recurring_charge=Decimal("4500.00"),
    currency="JPY",
    effective_from=date(2026, 8, 1),
    source_version="synthetic-kddi-v1",
)


class StubConversationAccess:
    def __init__(self, owned: bool = True) -> None:
        self.owned = owned

    def is_owned_by(self, conversation_id: UUID, customer_id: UUID) -> bool:
        assert conversation_id == CONVERSATION_ID
        assert customer_id == CUSTOMER_ID
        return self.owned


class StubCurrentPlans:
    def __init__(self, plan: CurrentPlanDetails | None) -> None:
        self.plan = plan
        self.requests: list[UUID] = []

    def get_current_plan(self, customer_id: UUID) -> CurrentPlanDetails | None:
        self.requests.append(customer_id)
        return self.plan


class RecordingExchanges:
    def __init__(self) -> None:
        self.saved: list[MessageExchange] = []

    def add(self, exchange: MessageExchange) -> None:
        self.saved.append(exchange)


def id_factory(values: list[UUID]) -> Iterator[UUID]:
    yield from values


def build_service(
    *,
    plan: CurrentPlanDetails | None,
    owned: bool = True,
    ids: list[UUID] | None = None,
) -> tuple[SendCurrentPlanMessageService, StubCurrentPlans, RecordingExchanges]:
    generated_ids = iter(
        ids or [USER_MESSAGE_ID, PLAN_SNAPSHOT_ID, ASSISTANT_MESSAGE_ID]
    )
    plans = StubCurrentPlans(plan)
    exchanges = RecordingExchanges()
    service = SendCurrentPlanMessageService(
        conversations=StubConversationAccess(owned),
        current_plans=plans,
        exchanges=exchanges,
        id_factory=lambda: next(generated_ids),
        clock=lambda: NOW,
    )
    return service, plans, exchanges


def test_current_plan_question_returns_and_persists_only_grounded_plan_facts() -> None:
    service, plans, exchanges = build_service(plan=AVAILABLE_PLAN)

    exchange = service.execute(
        customer_id=CUSTOMER_ID,
        conversation_id=CONVERSATION_ID,
        content="  What is my current plan?  ",
    )

    assert exchange.user_message.id == USER_MESSAGE_ID
    assert exchange.user_message.role is MessageRole.USER
    assert exchange.user_message.content == "What is my current plan?"
    assert exchange.assistant_message.id == ASSISTANT_MESSAGE_ID
    assert exchange.assistant_message.role is MessageRole.ASSISTANT
    assert exchange.assistant_message.answer_status is AnswerStatus.GROUNDED
    assert exchange.assistant_message.uncertain is False
    assert exchange.assistant_message.content == (
        "Your current plan is Synthetic KDDI 5G 20GB. "
        "It includes 20 GB of domestic data. "
        "The recorded monthly recurring charge is JPY 4,500. "
        "The plan has been effective since August 1, 2026."
    )
    assert exchange.plan_snapshot is not None
    assert exchange.plan_snapshot.id == PLAN_SNAPSHOT_ID
    assert exchange.plan_snapshot.customer_id == CUSTOMER_ID
    assert exchange.plan_snapshot.recurring_charge == Decimal("4500.00")
    assert len(exchange.assistant_message.evidence) == 1
    evidence = exchange.assistant_message.evidence[0]
    assert evidence.type is EvidenceType.PLAN_SNAPSHOT
    assert evidence.id == PLAN_SNAPSHOT_ID
    assert plans.requests == [CUSTOMER_ID]
    assert exchanges.saved == [exchange]


def test_unavailable_plan_never_invents_facts_and_gives_a_next_step() -> None:
    service, plans, exchanges = build_service(
        plan=None,
        ids=[USER_MESSAGE_ID, ASSISTANT_MESSAGE_ID],
    )

    exchange = service.execute(
        customer_id=CUSTOMER_ID,
        conversation_id=CONVERSATION_ID,
        content="Tell me about my plan",
    )

    assert exchange.plan_snapshot is None
    assert exchange.assistant_message.answer_status is AnswerStatus.UNAVAILABLE
    assert exchange.assistant_message.uncertain is True
    assert exchange.assistant_message.evidence == ()
    assert exchange.assistant_message.content == (
        "I can’t confirm your current plan because the synthetic plan data is unavailable. "
        "Please try again later or request human support."
    )
    assert "20" not in exchange.assistant_message.content
    assert "4,500" not in exchange.assistant_message.content
    assert plans.requests == [CUSTOMER_ID]
    assert exchanges.saved == [exchange]


def test_unsupported_question_is_persisted_without_querying_or_inventing_plan_data() -> None:
    service, plans, exchanges = build_service(
        plan=AVAILABLE_PLAN,
        ids=[USER_MESSAGE_ID, ASSISTANT_MESSAGE_ID],
    )

    exchange = service.execute(
        customer_id=CUSTOMER_ID,
        conversation_id=CONVERSATION_ID,
        content="Why is my latest bill higher?",
    )

    assert exchange.plan_snapshot is None
    assert exchange.assistant_message.answer_status is AnswerStatus.UNSUPPORTED
    assert exchange.assistant_message.uncertain is True
    assert exchange.assistant_message.evidence == ()
    assert exchange.assistant_message.content == (
        "I can currently explain your current mobile plan. "
        "Billing, unexpected-charge, and other requests are not implemented yet."
    )
    assert plans.requests == []
    assert exchanges.saved == [exchange]


def test_missing_or_cross_customer_conversation_uses_same_not_found_failure() -> None:
    service, plans, exchanges = build_service(plan=AVAILABLE_PLAN, owned=False)

    with pytest.raises(ConversationNotFoundError):
        service.execute(
            customer_id=CUSTOMER_ID,
            conversation_id=CONVERSATION_ID,
            content="What is my plan?",
        )

    assert plans.requests == []
    assert exchanges.saved == []
