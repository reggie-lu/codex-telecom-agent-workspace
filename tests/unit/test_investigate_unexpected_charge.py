from collections.abc import Iterator
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

import pytest

from telecom_agent.domain.charges import (
    ChargeEvidenceDetails,
    ChargeEvidenceState,
)
from telecom_agent.domain.messages import AnswerStatus, EvidenceType, MessageExchange
from telecom_agent.services.send_support_message import SendSupportMessageService
from tests.unit.test_send_current_plan_message import (
    AVAILABLE_PLAN,
    CONVERSATION_ID,
    CUSTOMER_ID,
    StubAnswerGenerator,
    StubConversationAccess,
    StubCurrentPlans,
)
from tests.unit.test_send_latest_bill_message import (
    BILL_SNAPSHOT_ID,
    LATEST_BILL,
    LINE_ITEM_IDS,
    StubLatestBills,
)

USER_MESSAGE_ID = UUID("71000000-0000-0000-0000-000000000001")
CHARGE_SNAPSHOT_ID = UUID("72000000-0000-0000-0000-000000000001")
ASSISTANT_MESSAGE_ID = UUID("73000000-0000-0000-0000-000000000001")
NOW = datetime(2026, 8, 26, 9, 20, tzinfo=UTC)

CONFIRMED_EVIDENCE = ChargeEvidenceDetails(
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


class StubChargeEvidence:
    def __init__(self, details: ChargeEvidenceDetails | None) -> None:
        self.details = details
        self.requests: list[tuple[UUID, str]] = []

    def get_charge_evidence(
        self,
        customer_id: UUID,
        line_item_code: str,
    ) -> ChargeEvidenceDetails | None:
        self.requests.append((customer_id, line_item_code))
        return self.details


class RecordingExchanges:
    def __init__(self) -> None:
        self.saved: list[MessageExchange] = []

    def add(self, exchange: MessageExchange) -> None:
        self.saved.append(exchange)


def id_factory(values: list[UUID]) -> Iterator[UUID]:
    yield from values


def build_service(
    evidence: ChargeEvidenceDetails | None,
    *,
    ids: list[UUID] | None = None,
) -> tuple[SendSupportMessageService, StubLatestBills, StubChargeEvidence, RecordingExchanges]:
    generated_ids = iter(
        ids
        or [
            USER_MESSAGE_ID,
            BILL_SNAPSHOT_ID,
            *LINE_ITEM_IDS,
            CHARGE_SNAPSHOT_ID,
            ASSISTANT_MESSAGE_ID,
        ]
    )
    bills = StubLatestBills(LATEST_BILL)
    charges = StubChargeEvidence(evidence)
    exchanges = RecordingExchanges()
    service = SendSupportMessageService(
        conversations=StubConversationAccess(),
        current_plans=StubCurrentPlans(AVAILABLE_PLAN),
        latest_bills=bills,
        charge_evidence=charges,
        answer_generator=StubAnswerGenerator(),
        exchanges=exchanges,
        id_factory=lambda: next(generated_ids),
        clock=lambda: NOW,
    )
    return service, bills, charges, exchanges


@pytest.mark.parametrize(
    "question",
    [
        "Why is my latest bill higher?",
        "What is the unexpected charge on my bill?",
        "Why was I charged JPY 1,200?",
    ],
)
def test_supported_unexpected_charge_question_returns_two_grounded_evidence_types(
    question: str,
) -> None:
    service, bills, charges, exchanges = build_service(CONFIRMED_EVIDENCE)

    exchange = service.execute(
        customer_id=CUSTOMER_ID,
        conversation_id=CONVERSATION_ID,
        content=question,
    )

    assert exchange.assistant_message.answer_status is AnswerStatus.GROUNDED
    assert exchange.assistant_message.uncertain is False
    assert exchange.assistant_message.content == (
        "The JPY 1,200 International roaming data item on your July 1–31, 2026 bill is "
        "linked to mobile data use in the United States on July 18, 2026. That usage "
        "automatically activated the Synthetic KDDI Overseas Data Day Pass. If you do not "
        "recognize this usage, request human support; I cannot decide a billing dispute."
    )
    assert exchange.bill_snapshot is not None
    assert exchange.charge_snapshot is not None
    assert exchange.charge_snapshot.id == CHARGE_SNAPSHOT_ID
    assert exchange.charge_snapshot.line_item_code == "roaming_data"
    assert exchange.charge_snapshot.occurred_on == date(2026, 7, 18)
    assert exchange.charge_snapshot.location == "United States"
    assert [evidence.type for evidence in exchange.assistant_message.evidence] == [
        EvidenceType.BILL_SNAPSHOT,
        EvidenceType.CHARGE_SNAPSHOT,
    ]
    assert bills.requests == [CUSTOMER_ID]
    assert charges.requests == [(CUSTOMER_ID, "roaming_data")]
    assert exchanges.saved == [exchange]


def test_missing_causal_evidence_identifies_item_but_does_not_invent_reason() -> None:
    service, _bills, _charges, exchanges = build_service(
        None,
        ids=[USER_MESSAGE_ID, BILL_SNAPSHOT_ID, *LINE_ITEM_IDS, ASSISTANT_MESSAGE_ID],
    )

    exchange = service.execute(
        customer_id=CUSTOMER_ID,
        conversation_id=CONVERSATION_ID,
        content="Why is my bill higher?",
    )

    assert exchange.assistant_message.answer_status is AnswerStatus.UNAVAILABLE
    assert exchange.assistant_message.uncertain is True
    assert exchange.assistant_message.content == (
        "I found the JPY 1,200 International roaming data item on your latest bill, but I "
        "can’t determine why it was charged because supporting usage data is unavailable. "
        "Please request human support."
    )
    assert exchange.bill_snapshot is not None
    assert exchange.charge_snapshot is None
    assert [evidence.type for evidence in exchange.assistant_message.evidence] == [
        EvidenceType.BILL_SNAPSHOT
    ]
    assert "United States" not in exchange.assistant_message.content
    assert "activated" not in exchange.assistant_message.content
    assert exchanges.saved == [exchange]


@pytest.mark.parametrize(
    "evidence",
    [
        ChargeEvidenceDetails(
            line_item_code=CONFIRMED_EVIDENCE.line_item_code,
            description=CONFIRMED_EVIDENCE.description,
            amount=Decimal("1300.00"),
            currency=CONFIRMED_EVIDENCE.currency,
            occurred_on=CONFIRMED_EVIDENCE.occurred_on,
            location=CONFIRMED_EVIDENCE.location,
            service_name=CONFIRMED_EVIDENCE.service_name,
            trigger=CONFIRMED_EVIDENCE.trigger,
            state=ChargeEvidenceState.CONFIRMED,
            source_version=CONFIRMED_EVIDENCE.source_version,
        ),
        ChargeEvidenceDetails(
            line_item_code=CONFIRMED_EVIDENCE.line_item_code,
            description=CONFIRMED_EVIDENCE.description,
            amount=CONFIRMED_EVIDENCE.amount,
            currency=CONFIRMED_EVIDENCE.currency,
            occurred_on=CONFIRMED_EVIDENCE.occurred_on,
            location=CONFIRMED_EVIDENCE.location,
            service_name=CONFIRMED_EVIDENCE.service_name,
            trigger=CONFIRMED_EVIDENCE.trigger,
            state=ChargeEvidenceState.STALE,
            source_version=CONFIRMED_EVIDENCE.source_version,
        ),
    ],
)
def test_conflicting_or_stale_causal_evidence_is_flagged_without_explanation(
    evidence: ChargeEvidenceDetails,
) -> None:
    service, _bills, _charges, exchanges = build_service(evidence)

    exchange = service.execute(
        customer_id=CUSTOMER_ID,
        conversation_id=CONVERSATION_ID,
        content="What is this unexpected charge?",
    )

    assert exchange.assistant_message.answer_status is AnswerStatus.UNAVAILABLE
    assert exchange.assistant_message.uncertain is True
    assert "billing and usage records are conflicting or outdated" in (
        exchange.assistant_message.content
    )
    assert "automatically activated" not in exchange.assistant_message.content
    assert exchange.bill_snapshot is not None
    assert exchange.charge_snapshot is not None
    assert [item.type for item in exchange.assistant_message.evidence] == [
        EvidenceType.BILL_SNAPSHOT,
        EvidenceType.CHARGE_SNAPSHOT,
    ]
    assert exchanges.saved == [exchange]


def test_ambiguous_charge_reference_asks_for_line_item_without_retrieval() -> None:
    service, bills, charges, exchanges = build_service(
        CONFIRMED_EVIDENCE,
        ids=[USER_MESSAGE_ID, ASSISTANT_MESSAGE_ID],
    )

    exchange = service.execute(
        customer_id=CUSTOMER_ID,
        conversation_id=CONVERSATION_ID,
        content="What is this charge?",
    )

    assert exchange.assistant_message.answer_status is AnswerStatus.UNAVAILABLE
    assert exchange.assistant_message.uncertain is True
    assert exchange.assistant_message.content == (
        "Which line item do you mean? Please provide its description or amount from your bill."
    )
    assert exchange.assistant_message.evidence == ()
    assert exchange.bill_snapshot is None
    assert exchange.charge_snapshot is None
    assert bills.requests == []
    assert charges.requests == []
    assert exchanges.saved == [exchange]
