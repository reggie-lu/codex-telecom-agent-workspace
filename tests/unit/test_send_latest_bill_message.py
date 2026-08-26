from collections.abc import Iterator
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from telecom_agent.domain.bills import BillLineItem, LatestBillDetails
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

USER_MESSAGE_ID = UUID("61000000-0000-0000-0000-000000000001")
BILL_SNAPSHOT_ID = UUID("62000000-0000-0000-0000-000000000001")
LINE_ITEM_IDS = (
    UUID("63000000-0000-0000-0000-000000000001"),
    UUID("63000000-0000-0000-0000-000000000002"),
    UUID("63000000-0000-0000-0000-000000000003"),
    UUID("63000000-0000-0000-0000-000000000004"),
)
ASSISTANT_MESSAGE_ID = UUID("64000000-0000-0000-0000-000000000001")
NOW = datetime(2026, 8, 26, 8, 45, tzinfo=UTC)

LATEST_BILL = LatestBillDetails(
    period_start=date(2026, 7, 1),
    period_end=date(2026, 7, 31),
    total=Decimal("6930.00"),
    currency="JPY",
    line_items=(
        BillLineItem("monthly_service", "Monthly mobile service", Decimal("4500.00")),
        BillLineItem("domestic_calls", "Domestic calls", Decimal("600.00")),
        BillLineItem("roaming_data", "International roaming data", Decimal("1200.00")),
        BillLineItem("taxes_fees", "Taxes and fees", Decimal("630.00")),
    ),
    source_version="synthetic-kddi-bill-v1",
)


class StubLatestBills:
    def __init__(self, bill: LatestBillDetails | None) -> None:
        self.bill = bill
        self.requests: list[UUID] = []

    def get_latest_bill(self, customer_id: UUID) -> LatestBillDetails | None:
        self.requests.append(customer_id)
        return self.bill


class RecordingExchanges:
    def __init__(self) -> None:
        self.saved: list[MessageExchange] = []

    def add(self, exchange: MessageExchange) -> None:
        self.saved.append(exchange)


def id_factory(values: list[UUID]) -> Iterator[UUID]:
    yield from values


def build_service(
    bill: LatestBillDetails | None,
) -> tuple[SendSupportMessageService, StubLatestBills, RecordingExchanges, StubAnswerGenerator]:
    ids = iter(
        [USER_MESSAGE_ID, BILL_SNAPSHOT_ID, *LINE_ITEM_IDS, ASSISTANT_MESSAGE_ID]
        if bill is not None
        else [USER_MESSAGE_ID, ASSISTANT_MESSAGE_ID]
    )
    bills = StubLatestBills(bill)
    exchanges = RecordingExchanges()
    generator = StubAnswerGenerator()
    service = SendSupportMessageService(
        conversations=StubConversationAccess(),
        current_plans=StubCurrentPlans(AVAILABLE_PLAN),
        latest_bills=bills,
        answer_generator=generator,
        exchanges=exchanges,
        id_factory=lambda: next(ids),
        clock=lambda: NOW,
    )
    return service, bills, exchanges, generator


def test_latest_bill_question_returns_reconciled_typed_evidence() -> None:
    service, bills, exchanges, generator = build_service(LATEST_BILL)

    exchange = service.execute(
        customer_id=CUSTOMER_ID,
        conversation_id=CONVERSATION_ID,
        content="What is my latest bill?",
    )

    assert exchange.assistant_message.answer_status is AnswerStatus.GROUNDED
    assert exchange.assistant_message.uncertain is False
    assert exchange.assistant_message.content == (
        "Your latest bill covers July 1–31, 2026. The total is JPY 6,930. "
        "Line items: Monthly mobile service — JPY 4,500; Domestic calls — JPY 600; "
        "International roaming data — JPY 1,200; Taxes and fees — JPY 630."
    )
    assert exchange.plan_snapshot is None
    assert exchange.bill_snapshot is not None
    assert exchange.bill_snapshot.id == BILL_SNAPSHOT_ID
    assert exchange.bill_snapshot.customer_id == CUSTOMER_ID
    assert exchange.bill_snapshot.total == Decimal("6930.00")
    assert tuple(item.id for item in exchange.bill_snapshot.line_items) == LINE_ITEM_IDS
    assert len(exchange.assistant_message.evidence) == 1
    assert exchange.assistant_message.evidence[0].type is EvidenceType.BILL_SNAPSHOT
    assert exchange.assistant_message.evidence[0].id == BILL_SNAPSHOT_ID
    assert bills.requests == [CUSTOMER_ID]
    assert generator.requests == []
    assert exchanges.saved == [exchange]


def test_missing_latest_bill_returns_safe_unavailable_without_amounts() -> None:
    service, bills, exchanges, generator = build_service(None)

    exchange = service.execute(
        customer_id=CUSTOMER_ID,
        conversation_id=CONVERSATION_ID,
        content="Show me my latest bill",
    )

    assert exchange.assistant_message.answer_status is AnswerStatus.UNAVAILABLE
    assert exchange.assistant_message.uncertain is True
    assert exchange.assistant_message.evidence == ()
    assert exchange.bill_snapshot is None
    assert "billing data is unavailable" in exchange.assistant_message.content
    assert "6,930" not in exchange.assistant_message.content
    assert bills.requests == [CUSTOMER_ID]
    assert generator.requests == []
    assert exchanges.saved == [exchange]


def test_mismatched_bill_total_fails_safe_without_persisting_evidence() -> None:
    inconsistent_bill = LatestBillDetails(
        period_start=LATEST_BILL.period_start,
        period_end=LATEST_BILL.period_end,
        total=Decimal("7000.00"),
        currency=LATEST_BILL.currency,
        line_items=LATEST_BILL.line_items,
        source_version=LATEST_BILL.source_version,
    )
    service, _bills, exchanges, _generator = build_service(inconsistent_bill)

    exchange = service.execute(
        customer_id=CUSTOMER_ID,
        conversation_id=CONVERSATION_ID,
        content="Explain my latest bill",
    )

    assert exchange.assistant_message.answer_status is AnswerStatus.UNAVAILABLE
    assert exchange.assistant_message.uncertain is True
    assert exchange.assistant_message.evidence == ()
    assert exchange.bill_snapshot is None
    assert "billing data is incomplete or inconsistent" in exchange.assistant_message.content
    assert exchanges.saved == [exchange]
