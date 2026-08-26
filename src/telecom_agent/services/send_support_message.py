from collections import Counter
from collections.abc import Callable
from datetime import UTC, date, datetime
from decimal import Decimal
from re import findall
from uuid import UUID, uuid4

from telecom_agent.domain.bills import (
    BillLineItem,
    BillLineItemSnapshot,
    BillSnapshot,
    LatestBillDetails,
)
from telecom_agent.domain.charges import (
    ChargeEvidenceDetails,
    ChargeEvidenceSnapshot,
    ChargeEvidenceState,
)
from telecom_agent.domain.messages import (
    AnswerStatus,
    EvidenceReference,
    EvidenceType,
    Message,
    MessageExchange,
    MessageRole,
)
from telecom_agent.domain.plans import GroundedCurrentPlanFacts, PlanSnapshot
from telecom_agent.ports.messages import (
    AnswerGenerationUnavailableError,
    ChargeEvidenceProvider,
    ConversationAccessRepository,
    CurrentPlanAnswerGenerator,
    CurrentPlanProvider,
    LatestBillProvider,
    MessageExchangeRepository,
)


class ConversationNotFoundError(Exception):
    pass


class SendSupportMessageService:
    def __init__(
        self,
        *,
        conversations: ConversationAccessRepository,
        current_plans: CurrentPlanProvider,
        answer_generator: CurrentPlanAnswerGenerator,
        exchanges: MessageExchangeRepository,
        latest_bills: LatestBillProvider | None = None,
        charge_evidence: ChargeEvidenceProvider | None = None,
        id_factory: Callable[[], UUID] = uuid4,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._conversations = conversations
        self._current_plans = current_plans
        self._latest_bills = latest_bills
        self._charge_evidence = charge_evidence
        self._answer_generator = answer_generator
        self._exchanges = exchanges
        self._id_factory = id_factory
        self._clock = clock

    def execute(
        self,
        *,
        customer_id: UUID,
        conversation_id: UUID,
        content: str,
    ) -> MessageExchange:
        if not self._conversations.is_owned_by(conversation_id, customer_id):
            raise ConversationNotFoundError

        normalized_content = content.strip()
        user_message = Message(
            id=self._id_factory(),
            conversation_id=conversation_id,
            role=MessageRole.USER,
            content=normalized_content,
            created_at=self._clock(),
        )

        if _is_ambiguous_charge_question(normalized_content):
            exchange = self._charge_clarification_exchange(user_message)
        elif _is_unexpected_charge_question(normalized_content):
            bill = (
                self._latest_bills.get_latest_bill(customer_id)
                if self._latest_bills is not None
                else None
            )
            exchange = self._unexpected_charge_exchange(user_message, customer_id, bill)
        elif _is_latest_bill_question(normalized_content):
            bill = (
                self._latest_bills.get_latest_bill(customer_id)
                if self._latest_bills is not None
                else None
            )
            exchange = self._latest_bill_exchange(user_message, customer_id, bill)
        elif not _is_current_plan_question(normalized_content):
            exchange = self._unsupported_exchange(user_message)
        else:
            plan = self._current_plans.get_current_plan(customer_id)
            if plan is None:
                exchange = self._unavailable_exchange(user_message)
            else:
                plan_snapshot = PlanSnapshot(
                    id=self._id_factory(),
                    customer_id=customer_id,
                    plan_code=plan.plan_code,
                    plan_name=plan.plan_name,
                    data_allowance_gb=plan.data_allowance_gb,
                    recurring_charge=plan.recurring_charge,
                    currency=plan.currency,
                    effective_from=plan.effective_from,
                    retrieved_at=self._clock(),
                    source_version=plan.source_version,
                )
                exchange = self._generated_exchange(user_message, plan_snapshot)

        self._exchanges.add(exchange)
        return exchange

    def _latest_bill_exchange(
        self,
        user_message: Message,
        customer_id: UUID,
        bill: LatestBillDetails | None,
    ) -> MessageExchange:
        if bill is None:
            return self._bill_unavailable_exchange(user_message)
        if not _is_reconciled_bill(bill):
            return self._bill_inconsistent_exchange(user_message)

        snapshot = self._snapshot_bill(customer_id, bill)
        line_items = "; ".join(
            f"{item.description} — {_format_money(bill.currency, item.amount)}"
            for item in bill.line_items
        )
        assistant_message = self._assistant_message(
            conversation_id=user_message.conversation_id,
            content=(
                f"Your latest bill covers {_format_bill_period(bill)}. "
                f"The total is {_format_money(bill.currency, bill.total)}. "
                f"Line items: {line_items}."
            ),
            answer_status=AnswerStatus.GROUNDED,
            uncertain=False,
            evidence=(
                EvidenceReference(type=EvidenceType.BILL_SNAPSHOT, id=snapshot.id),
            ),
        )
        return MessageExchange(
            user_message=user_message,
            assistant_message=assistant_message,
            bill_snapshot=snapshot,
        )

    def _unexpected_charge_exchange(
        self,
        user_message: Message,
        customer_id: UUID,
        bill: LatestBillDetails | None,
    ) -> MessageExchange:
        if bill is None:
            return self._bill_unavailable_exchange(user_message)
        if not _is_reconciled_bill(bill):
            return self._bill_inconsistent_exchange(user_message)

        roaming_item = next(
            (item for item in bill.line_items if item.code == "roaming_data"),
            None,
        )
        if roaming_item is None:
            return self._charge_not_identified_exchange(user_message)

        bill_snapshot = self._snapshot_bill(customer_id, bill)
        details = (
            self._charge_evidence.get_charge_evidence(customer_id, roaming_item.code)
            if self._charge_evidence is not None
            else None
        )
        if details is None:
            return self._missing_charge_evidence_exchange(
                user_message,
                bill,
                roaming_item,
                bill_snapshot,
            )

        charge_snapshot = self._snapshot_charge(customer_id, details)
        evidence = (
            EvidenceReference(type=EvidenceType.BILL_SNAPSHOT, id=bill_snapshot.id),
            EvidenceReference(type=EvidenceType.CHARGE_SNAPSHOT, id=charge_snapshot.id),
        )
        if not _charge_evidence_matches(bill, roaming_item, details):
            assistant_message = self._assistant_message(
                conversation_id=user_message.conversation_id,
                content=(
                    "I can’t explain the unexpected charge because the synthetic billing and "
                    "usage records are conflicting or outdated. Please request human support."
                ),
                answer_status=AnswerStatus.UNAVAILABLE,
                uncertain=True,
                evidence=evidence,
            )
        else:
            assistant_message = self._assistant_message(
                conversation_id=user_message.conversation_id,
                content=(
                    f"The {_format_money(bill.currency, roaming_item.amount)} "
                    f"{roaming_item.description} item on your {_format_bill_period(bill)} bill is "
                    f"linked to mobile data use in the {details.location} on "
                    f"{_format_date(details.occurred_on)}. That usage automatically activated "
                    f"the {details.service_name}. If you do not recognize this usage, request "
                    "human support; I cannot decide a billing dispute."
                ),
                answer_status=AnswerStatus.GROUNDED,
                uncertain=False,
                evidence=evidence,
            )
        return MessageExchange(
            user_message=user_message,
            assistant_message=assistant_message,
            bill_snapshot=bill_snapshot,
            charge_snapshot=charge_snapshot,
        )

    def _snapshot_bill(self, customer_id: UUID, bill: LatestBillDetails) -> BillSnapshot:
        return BillSnapshot(
            id=self._id_factory(),
            customer_id=customer_id,
            period_start=bill.period_start,
            period_end=bill.period_end,
            total=bill.total,
            currency=bill.currency,
            line_items=tuple(
                BillLineItemSnapshot(
                    id=self._id_factory(),
                    code=item.code,
                    description=item.description,
                    amount=item.amount,
                )
                for item in bill.line_items
            ),
            retrieved_at=self._clock(),
            source_version=bill.source_version,
        )

    def _snapshot_charge(
        self,
        customer_id: UUID,
        details: ChargeEvidenceDetails,
    ) -> ChargeEvidenceSnapshot:
        return ChargeEvidenceSnapshot(
            id=self._id_factory(),
            customer_id=customer_id,
            line_item_code=details.line_item_code,
            description=details.description,
            amount=details.amount,
            currency=details.currency,
            occurred_on=details.occurred_on,
            location=details.location,
            service_name=details.service_name,
            trigger=details.trigger,
            state=details.state,
            retrieved_at=self._clock(),
            source_version=details.source_version,
        )

    def _generated_exchange(
        self,
        user_message: Message,
        plan_snapshot: PlanSnapshot,
    ) -> MessageExchange:
        facts = GroundedCurrentPlanFacts(
            plan_name=plan_snapshot.plan_name,
            data_allowance=f"{plan_snapshot.data_allowance_gb} GB",
            recurring_charge=(
                f"{plan_snapshot.currency} {_format_amount(plan_snapshot.recurring_charge)}"
            ),
            effective_date=_format_date(plan_snapshot.effective_from),
        )
        try:
            content = self._answer_generator.generate(
                question=user_message.content,
                facts=facts,
            ).strip()
        except AnswerGenerationUnavailableError:
            return self._generation_unavailable_exchange(user_message)

        if not _is_grounded_output(content, facts):
            return self._generation_unavailable_exchange(user_message)

        assistant_message = self._assistant_message(
            conversation_id=user_message.conversation_id,
            content=content,
            answer_status=AnswerStatus.GROUNDED,
            uncertain=False,
            evidence=(
                EvidenceReference(
                    type=EvidenceType.PLAN_SNAPSHOT,
                    id=plan_snapshot.id,
                ),
            ),
        )
        return MessageExchange(user_message, assistant_message, plan_snapshot)

    def _generation_unavailable_exchange(self, user_message: Message) -> MessageExchange:
        assistant_message = self._assistant_message(
            conversation_id=user_message.conversation_id,
            content=(
                "I can’t generate a grounded answer right now. "
                "Please try again later or request human support."
            ),
            answer_status=AnswerStatus.UNAVAILABLE,
            uncertain=True,
        )
        return MessageExchange(user_message, assistant_message, None)

    def _unavailable_exchange(self, user_message: Message) -> MessageExchange:
        assistant_message = self._assistant_message(
            conversation_id=user_message.conversation_id,
            content=(
                "I can’t confirm your current plan because the synthetic plan data is unavailable. "
                "Please try again later or request human support."
            ),
            answer_status=AnswerStatus.UNAVAILABLE,
            uncertain=True,
        )
        return MessageExchange(user_message, assistant_message, None)

    def _bill_unavailable_exchange(self, user_message: Message) -> MessageExchange:
        assistant_message = self._assistant_message(
            conversation_id=user_message.conversation_id,
            content=(
                "I can’t confirm your latest bill because the synthetic billing data is "
                "unavailable. Please try again later or request human support."
            ),
            answer_status=AnswerStatus.UNAVAILABLE,
            uncertain=True,
        )
        return MessageExchange(user_message, assistant_message)

    def _bill_inconsistent_exchange(self, user_message: Message) -> MessageExchange:
        assistant_message = self._assistant_message(
            conversation_id=user_message.conversation_id,
            content=(
                "I can’t confirm your latest bill because the synthetic billing data is "
                "incomplete or inconsistent. Please request human support."
            ),
            answer_status=AnswerStatus.UNAVAILABLE,
            uncertain=True,
        )
        return MessageExchange(user_message, assistant_message)

    def _missing_charge_evidence_exchange(
        self,
        user_message: Message,
        bill: LatestBillDetails,
        line_item: BillLineItem,
        bill_snapshot: BillSnapshot,
    ) -> MessageExchange:
        assistant_message = self._assistant_message(
            conversation_id=user_message.conversation_id,
            content=(
                f"I found the {_format_money(bill.currency, line_item.amount)} "
                f"{line_item.description} item on your latest bill, but I can’t determine why "
                "it was charged because supporting usage data is unavailable. Please request "
                "human support."
            ),
            answer_status=AnswerStatus.UNAVAILABLE,
            uncertain=True,
            evidence=(
                EvidenceReference(type=EvidenceType.BILL_SNAPSHOT, id=bill_snapshot.id),
            ),
        )
        return MessageExchange(
            user_message=user_message,
            assistant_message=assistant_message,
            bill_snapshot=bill_snapshot,
        )

    def _charge_not_identified_exchange(self, user_message: Message) -> MessageExchange:
        assistant_message = self._assistant_message(
            conversation_id=user_message.conversation_id,
            content=(
                "I can’t identify an unexpected line item from the synthetic bill. "
                "Please provide the charge description or request human support."
            ),
            answer_status=AnswerStatus.UNAVAILABLE,
            uncertain=True,
        )
        return MessageExchange(user_message, assistant_message)

    def _charge_clarification_exchange(self, user_message: Message) -> MessageExchange:
        assistant_message = self._assistant_message(
            conversation_id=user_message.conversation_id,
            content=(
                "Which line item do you mean? Please provide its description or amount from your bill."
            ),
            answer_status=AnswerStatus.UNAVAILABLE,
            uncertain=True,
        )
        return MessageExchange(user_message, assistant_message)

    def _unsupported_exchange(self, user_message: Message) -> MessageExchange:
        assistant_message = self._assistant_message(
            conversation_id=user_message.conversation_id,
            content=(
                "I can currently explain your current mobile plan, summarize your latest bill, "
                "or investigate the supported unexpected roaming charge. Other requests are not "
                "implemented yet."
            ),
            answer_status=AnswerStatus.UNSUPPORTED,
            uncertain=True,
        )
        return MessageExchange(user_message, assistant_message, None)

    def _assistant_message(
        self,
        *,
        conversation_id: UUID,
        content: str,
        answer_status: AnswerStatus,
        uncertain: bool,
        evidence: tuple[EvidenceReference, ...] = (),
    ) -> Message:
        return Message(
            id=self._id_factory(),
            conversation_id=conversation_id,
            role=MessageRole.ASSISTANT,
            content=content,
            created_at=self._clock(),
            answer_status=answer_status,
            uncertain=uncertain,
            evidence=evidence,
        )


def _is_current_plan_question(content: str) -> bool:
    normalized = " ".join(findall(r"\w+", content.casefold()))
    words = set(normalized.split())
    return "plan" in words or any(
        phrase in normalized
        for phrase in (
            "data allowance",
            "how much data",
            "monthly recurring charge",
            "mobile package",
            "mobile service",
        )
    )


def _is_latest_bill_question(content: str) -> bool:
    normalized = " ".join(findall(r"\w+", content.casefold()))
    words = set(normalized.split())
    diagnostic_words = {"why", "higher", "unexpected", "wrong", "incorrect"}
    return "bill" in words and words.isdisjoint(diagnostic_words)


def _is_ambiguous_charge_question(content: str) -> bool:
    normalized = " ".join(findall(r"\w+", content.casefold()))
    return (
        "this charge" in normalized
        and "unexpected" not in normalized
        and not findall(r"\d", normalized)
    )


def _is_unexpected_charge_question(content: str) -> bool:
    normalized = " ".join(findall(r"\w+", content.casefold()))
    words = set(normalized.split())
    diagnostic_words = {"why", "higher", "unexpected", "wrong", "incorrect"}
    return (
        "unexpected" in words
        or ("bill" in words and not words.isdisjoint(diagnostic_words))
        or ("charged" in words and bool(findall(r"\d", normalized)))
    )


def _is_reconciled_bill(bill: LatestBillDetails) -> bool:
    return (
        bill.period_start <= bill.period_end
        and bill.total >= 0
        and len(bill.currency) == 3
        and bool(bill.source_version.strip())
        and bool(bill.line_items)
        and all(
            item.amount >= 0 and bool(item.code.strip()) and bool(item.description.strip())
            for item in bill.line_items
        )
        and sum((item.amount for item in bill.line_items), Decimal()) == bill.total
    )


def _charge_evidence_matches(
    bill: LatestBillDetails,
    line_item: BillLineItem,
    details: ChargeEvidenceDetails,
) -> bool:
    return (
        details.state is ChargeEvidenceState.CONFIRMED
        and details.line_item_code == line_item.code
        and details.description == line_item.description
        and details.amount == line_item.amount
        and details.currency == bill.currency
        and bill.period_start <= details.occurred_on <= bill.period_end
        and bool(details.location.strip())
        and bool(details.service_name.strip())
        and bool(details.trigger.strip())
        and bool(details.source_version.strip())
    )


def _format_bill_period(bill: LatestBillDetails) -> str:
    start = bill.period_start
    end = bill.period_end
    if start.year == end.year and start.month == end.month:
        return f"{start.strftime('%B')} {start.day}–{end.day}, {end.year}"
    return f"{_format_date(start)}–{_format_date(end)}"


def _format_money(currency: str, amount: Decimal) -> str:
    return f"{currency} {_format_amount(amount)}"


def _format_amount(amount: Decimal) -> str:
    if amount == amount.to_integral_value():
        return f"{amount:,.0f}"
    return f"{amount:,.2f}"


def _format_date(value: date) -> str:
    return f"{value.strftime('%B')} {value.day}, {value.year}"


def _is_grounded_output(content: str, facts: GroundedCurrentPlanFacts) -> bool:
    if not content or len(content) > 1000:
        return False

    required_values = (
        facts.plan_name,
        facts.data_allowance,
        facts.recurring_charge,
        facts.effective_date,
    )
    if any(value not in content for value in required_values):
        return False

    numeric_pattern = r"\d[\d,.]*"
    allowed_numbers = Counter(
        token.rstrip(".,")
        for value in required_values
        for token in findall(numeric_pattern, value)
    )
    output_numbers = Counter(
        token.rstrip(".,") for token in findall(numeric_pattern, content)
    )
    return output_numbers <= allowed_numbers
