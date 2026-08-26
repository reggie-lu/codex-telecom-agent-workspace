from collections import Counter
from collections.abc import Callable
from datetime import UTC, date, datetime
from decimal import Decimal
from re import findall
from uuid import UUID, uuid4

from telecom_agent.domain.bills import (
    BillLineItemSnapshot,
    BillSnapshot,
    LatestBillDetails,
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
        id_factory: Callable[[], UUID] = uuid4,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._conversations = conversations
        self._current_plans = current_plans
        self._latest_bills = latest_bills
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

        if _is_latest_bill_question(normalized_content):
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

        snapshot = BillSnapshot(
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

    def _unsupported_exchange(self, user_message: Message) -> MessageExchange:
        assistant_message = self._assistant_message(
            conversation_id=user_message.conversation_id,
            content=(
                "I can currently explain your current mobile plan or summarize your latest bill. "
                "Unexpected-charge investigation and other requests are not implemented yet."
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
