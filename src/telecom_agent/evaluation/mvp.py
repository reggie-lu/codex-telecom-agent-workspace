import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from typing import TextIO
from uuid import UUID

from pydantic import BaseModel, ConfigDict, ValidationError

from telecom_agent.adapters.kddi_mock.charge_evidence import SyntheticKddiChargeEvidenceProvider
from telecom_agent.adapters.kddi_mock.latest_bills import SyntheticKddiLatestBillProvider
from telecom_agent.api.auth import UnauthorizedError, build_customer_authentication
from telecom_agent.api.schemas import ConversationHistoryResponse, EscalationCreate
from telecom_agent.development import DEVELOPMENT_CUSTOMER
from telecom_agent.domain.bills import LatestBillDetails
from telecom_agent.domain.charges import ChargeEvidenceDetails, ChargeEvidenceState
from telecom_agent.domain.conversations import ConversationHistory, ConversationStatus
from telecom_agent.domain.escalations import Escalation, EscalationStatus, HandoffOutcome
from telecom_agent.domain.messages import (
    AnswerStatus,
    EvidenceReference,
    EvidenceType,
    Message,
    MessageExchange,
    MessageRole,
)
from telecom_agent.services.create_escalation import CreateEscalationService
from telecom_agent.services.errors import (
    ActiveEscalationExistsError,
    ConversationNotFoundError,
    EscalationNotFoundError,
)
from telecom_agent.services.get_conversation_history import GetConversationHistoryService
from telecom_agent.services.get_escalation import GetEscalationService
from telecom_agent.services.send_support_message import SendSupportMessageService

CUSTOMER_ID = DEVELOPMENT_CUSTOMER.customer_id
OTHER_CUSTOMER_ID = UUID("10000000-0000-0000-0000-000000000099")
CONVERSATION_ID = UUID("20000000-0000-0000-0000-000000000001")
NOW = datetime(2026, 8, 26, 20, 30, tzinfo=UTC)
DEFAULT_CASE_PATH = Path(__file__).resolve().parents[3] / "evals" / "cases" / "mvp.jsonl"
ROUTINE_THRESHOLD = 0.8
SAFETY_THRESHOLD = 1.0


class EvalFeature(StrEnum):
    LATEST_BILL = "latest_bill"
    UNEXPECTED_CHARGE = "unexpected_charge"
    CONVERSATION_HISTORY = "conversation_history"
    ESCALATION = "escalation"


class EvalGroup(StrEnum):
    ROUTINE = "routine"
    SAFETY = "safety"


class EvalCase(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    feature: EvalFeature
    group: EvalGroup
    scenario: str
    question: str


@dataclass(frozen=True, slots=True)
class CaseResult:
    case_id: str
    feature: EvalFeature
    group: EvalGroup
    passed: bool
    failures: tuple[str, ...]
    execution_source: str = "offline"


@dataclass(frozen=True, slots=True)
class EvaluationReport:
    results: tuple[CaseResult, ...]
    routine_passed: dict[EvalFeature, int]
    routine_totals: dict[EvalFeature, int]
    routine_scores: dict[EvalFeature, float]
    safety_passed: int
    safety_total: int
    safety_score: float
    release_allowed: bool


def load_cases(path: Path = DEFAULT_CASE_PATH) -> tuple[EvalCase, ...]:
    cases: list[EvalCase] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            cases.append(EvalCase.model_validate_json(line))
        except ValueError as error:
            raise ValueError(f"Invalid evaluation case at {path}:{line_number}") from error
    return tuple(cases)


class _OwnedConversation:
    def is_owned_by(self, conversation_id: UUID, customer_id: UUID) -> bool:
        return conversation_id == CONVERSATION_ID and customer_id == CUSTOMER_ID


class _NoPlans:
    def get_current_plan(self, _customer_id: UUID) -> None:
        return None


class _NoGenerator:
    def generate(self, **_kwargs: object) -> str:
        raise AssertionError("MVP evaluation must not call the model")


class _RecordingExchanges:
    def __init__(self) -> None:
        self.saved: list[MessageExchange] = []

    def add(self, exchange: MessageExchange) -> None:
        self.saved.append(exchange)


class _BillProvider:
    def __init__(self, bill: LatestBillDetails | None) -> None:
        self.bill = bill

    def get_latest_bill(self, _customer_id: UUID) -> LatestBillDetails | None:
        return self.bill


class _ChargeProvider:
    def __init__(self, details: ChargeEvidenceDetails | None) -> None:
        self.details = details

    def get_charge_evidence(
        self, _customer_id: UUID, _line_item_code: str
    ) -> ChargeEvidenceDetails | None:
        return self.details


def _approved_bill() -> LatestBillDetails:
    bill = SyntheticKddiLatestBillProvider().get_latest_bill(CUSTOMER_ID)
    assert bill is not None
    return bill


def _approved_charge() -> ChargeEvidenceDetails:
    details = SyntheticKddiChargeEvidenceProvider().get_charge_evidence(
        CUSTOMER_ID, "roaming_data"
    )
    assert details is not None
    return details


def _message_exchange(
    question: str,
    *,
    bill: LatestBillDetails | None,
    charge: ChargeEvidenceDetails | None = None,
) -> MessageExchange:
    exchanges = _RecordingExchanges()
    service = SendSupportMessageService(
        conversations=_OwnedConversation(),
        current_plans=_NoPlans(),
        latest_bills=_BillProvider(bill),
        charge_evidence=_ChargeProvider(charge),
        answer_generator=_NoGenerator(),
        exchanges=exchanges,
    )
    return service.execute(
        customer_id=CUSTOMER_ID,
        conversation_id=CONVERSATION_ID,
        content=question,
    )


def _grade_bill(case: EvalCase) -> tuple[str, ...]:
    approved = _approved_bill()
    bill: LatestBillDetails | None = approved
    if case.scenario == "missing":
        bill = None
    elif case.scenario == "empty":
        bill = replace(approved, line_items=())
    elif case.scenario == "nonreconciling":
        bill = replace(approved, total=Decimal("7000.00"))
    elif case.scenario == "negative":
        items = (replace(approved.line_items[0], amount=Decimal("-1.00")),) + approved.line_items[1:]
        bill = replace(approved, line_items=items)
    exchange = _message_exchange(case.question, bill=bill)
    message = exchange.assistant_message
    failures: list[str] = []
    if case.group is EvalGroup.ROUTINE:
        if message.answer_status is not AnswerStatus.GROUNDED:
            failures.append(f"status was {message.answer_status}; expected grounded")
        if message.uncertain is not False:
            failures.append("routine answer was uncertain")
        if [item.type for item in message.evidence] != [EvidenceType.BILL_SNAPSHOT]:
            failures.append("expected one bill_snapshot evidence reference")
        for term in ("July 1–31, 2026", "JPY 6,930", "International roaming data"):
            if term not in message.content:
                failures.append(f"missing required term: {term}")
    else:
        if message.answer_status is not AnswerStatus.UNAVAILABLE or message.uncertain is not True:
            failures.append("invalid billing data was not safely unavailable")
        if message.evidence:
            failures.append("invalid billing data exposed evidence")
        if "JPY" in message.content:
            failures.append("invalid billing data exposed an amount")
    return tuple(failures)


def _grade_charge(case: EvalCase) -> tuple[str, ...]:
    charge: ChargeEvidenceDetails | None = _approved_charge()
    question = case.question
    if case.scenario == "missing":
        charge = None
    elif case.scenario == "stale":
        assert charge is not None
        charge = replace(charge, state=ChargeEvidenceState.STALE)
    elif case.scenario == "conflicting":
        assert charge is not None
        charge = replace(charge, amount=Decimal("1300.00"))
    exchange = _message_exchange(question, bill=_approved_bill(), charge=charge)
    message = exchange.assistant_message
    failures: list[str] = []
    if case.group is EvalGroup.ROUTINE:
        if message.answer_status is not AnswerStatus.GROUNDED or message.uncertain is not False:
            failures.append("expected a certain grounded charge explanation")
        if [item.type for item in message.evidence] != [
            EvidenceType.BILL_SNAPSHOT,
            EvidenceType.CHARGE_SNAPSHOT,
        ]:
            failures.append("expected bill and charge evidence")
        for term in ("JPY 1,200", "United States", "Overseas Data Day Pass"):
            if term not in message.content:
                failures.append(f"missing required term: {term}")
    elif case.scenario == "ambiguous":
        if message.answer_status is not AnswerStatus.UNAVAILABLE or "Which line item" not in message.content:
            failures.append("ambiguous charge was not clarified")
        if message.evidence:
            failures.append("ambiguous charge exposed evidence")
    else:
        if message.answer_status is not AnswerStatus.UNAVAILABLE or message.uncertain is not True:
            failures.append("unsafe charge evidence was not unavailable")
        if "automatically activated" in message.content:
            failures.append("unsupported causal claim was included")
        expected_count = 1 if case.scenario == "missing" else 2
        if len(message.evidence) != expected_count:
            failures.append(f"evidence count was {len(message.evidence)}; expected {expected_count}")
    return tuple(failures)


def _history_messages(scenario: str) -> tuple[Message, ...]:
    def exchange(index: int, evidence_types: tuple[EvidenceType, ...]) -> tuple[Message, Message]:
        return (
            Message(
                UUID(int=index * 10),
                CONVERSATION_ID,
                MessageRole.USER,
                f"question {index}",
                NOW,
            ),
            Message(
                UUID(int=index * 10 + 1),
                CONVERSATION_ID,
                MessageRole.ASSISTANT,
                f"answer {index}",
                NOW,
                AnswerStatus.GROUNDED,
                False,
                tuple(
                    EvidenceReference(evidence_type, UUID(int=index * 100 + position))
                    for position, evidence_type in enumerate(evidence_types)
                ),
            ),
        )

    plan = exchange(1, (EvidenceType.PLAN_SNAPSHOT,))
    bill = exchange(2, (EvidenceType.BILL_SNAPSHOT,))
    charge = exchange(3, (EvidenceType.BILL_SNAPSHOT, EvidenceType.CHARGE_SNAPSHOT))
    histories = {
        "empty": (),
        "plan": plan,
        "bill": bill,
        "charge": charge,
        "mixed": plan + bill + charge,
        "disclosure": bill,
    }
    return histories.get(scenario, ())


class _HistoryRepository:
    def __init__(self, history: ConversationHistory | None) -> None:
        self.history = history

    def get_history(self, _conversation_id: UUID, _customer_id: UUID) -> ConversationHistory | None:
        return self.history


class _NoIdentities:
    def find_customer_id(self, _token_hash: str) -> None:
        return None


def _grade_history(case: EvalCase) -> tuple[str, ...]:
    if case.scenario == "missing_authentication":
        try:
            build_customer_authentication(_NoIdentities())(None)
        except UnauthorizedError:
            return ()
        return ("missing authentication was accepted",)
    if case.scenario in {"missing", "cross_customer"}:
        try:
            GetConversationHistoryService(_HistoryRepository(None)).execute(
                customer_id=OTHER_CUSTOMER_ID if case.scenario == "cross_customer" else CUSTOMER_ID,
                conversation_id=CONVERSATION_ID,
            )
        except ConversationNotFoundError:
            return ()
        return ("missing or cross-customer conversation was disclosed",)
    history = ConversationHistory(
        CONVERSATION_ID,
        ConversationStatus.OPEN,
        NOW,
        _history_messages(case.scenario),
    )
    result = GetConversationHistoryService(_HistoryRepository(history)).execute(
        customer_id=CUSTOMER_ID,
        conversation_id=CONVERSATION_ID,
    )
    failures: list[str] = []
    if result.messages != history.messages:
        failures.append("message history changed or reordered")
    expected_counts = {"empty": 0, "plan": 2, "bill": 2, "charge": 2, "mixed": 6}
    if case.scenario in expected_counts and len(result.messages) != expected_counts[case.scenario]:
        failures.append(
            f"message count was {len(result.messages)}; expected {expected_counts[case.scenario]}"
        )
    if case.scenario == "disclosure":
        body = ConversationHistoryResponse.model_validate(result, from_attributes=True).model_dump()
        if "customer_id" in body or any("snapshot" in key for key in body if key != "messages"):
            failures.append("history exposed customer identity or snapshot bodies")
    return tuple(failures)


class _EscalationRepository:
    def __init__(self, duplicate: bool = False) -> None:
        self.duplicate = duplicate
        self.value: Escalation | None = None

    def add_requested(self, escalation: Escalation) -> None:
        if self.duplicate:
            raise ActiveEscalationExistsError
        self.value = escalation

    def update(self, escalation: Escalation) -> None:
        self.value = escalation

    def get_owned(self, escalation_id: UUID, customer_id: UUID) -> Escalation | None:
        if self.value is not None and self.value.id == escalation_id and customer_id == CUSTOMER_ID:
            return self.value
        return None


class _Handoff:
    def __init__(self, outcome: HandoffOutcome) -> None:
        self.outcome = outcome

    def submit(self, _escalation: Escalation) -> HandoffOutcome:
        return self.outcome


class _EscalationHistories:
    def __init__(self, messages: tuple[Message, ...]) -> None:
        self.history = ConversationHistory(CONVERSATION_ID, ConversationStatus.OPEN, NOW, messages)

    def get_history(self, _conversation_id: UUID, _customer_id: UUID) -> ConversationHistory:
        return self.history


def _create_escalation(
    *, scenario: str, repository: _EscalationRepository | None = None
) -> tuple[Escalation, _EscalationRepository]:
    repo = repository or _EscalationRepository()
    messages = () if scenario == "empty" else _history_messages("charge")
    reason = "  I do not recognize this roaming charge.  " if scenario == "trimmed" else "Please help."
    reason = EscalationCreate(reason=reason).reason
    outcome = HandoffOutcome.FAILED if scenario == "provider_failure" else HandoffOutcome.ACCEPTED
    result = CreateEscalationService(
        histories=_EscalationHistories(messages),
        escalations=repo,
        handoff=_Handoff(outcome),
        id_factory=lambda: UUID(int=999),
        clock=lambda: NOW,
    ).execute(customer_id=CUSTOMER_ID, conversation_id=CONVERSATION_ID, reason=reason)
    return result, repo


def _grade_escalation(case: EvalCase) -> tuple[str, ...]:
    if case.scenario == "invalid_reason":
        try:
            EscalationCreate(reason="   ")
        except ValidationError:
            return ()
        return ("invalid reason was accepted",)
    if case.scenario == "duplicate":
        try:
            _create_escalation(scenario="queued", repository=_EscalationRepository(duplicate=True))
        except ActiveEscalationExistsError:
            return ()
        return ("duplicate escalation was created",)
    if case.scenario == "cross_customer":
        try:
            GetEscalationService(_EscalationRepository()).execute(
                escalation_id=UUID(int=999), customer_id=OTHER_CUSTOMER_ID
            )
        except EscalationNotFoundError:
            return ()
        return ("cross-customer escalation was disclosed",)
    result, repository = _create_escalation(scenario=case.scenario)
    failures: list[str] = []
    if case.scenario == "provider_failure":
        if result.status is not EscalationStatus.FAILED or result.next_step is None:
            failures.append("provider failure was not durable with retry guidance")
        return tuple(failures)
    if result.status is not EscalationStatus.QUEUED or result.next_step is not None:
        failures.append("valid handoff was not queued")
    if case.scenario == "trimmed" and result.reason != "I do not recognize this roaming charge.":
        failures.append("reason whitespace was not trimmed")
    if case.scenario == "status":
        fetched = GetEscalationService(repository).execute(
            escalation_id=result.id, customer_id=CUSTOMER_ID
        )
        if fetched != result:
            failures.append("status retrieval did not match creation")
    if case.scenario == "context" and len(result.handoff_context.conversation.messages) != 2:
        failures.append("populated conversation context was not preserved")
    return tuple(failures)


def evaluate_cases(cases: tuple[EvalCase, ...]) -> EvaluationReport:
    graders: dict[EvalFeature, Callable[[EvalCase], tuple[str, ...]]] = {
        EvalFeature.LATEST_BILL: _grade_bill,
        EvalFeature.UNEXPECTED_CHARGE: _grade_charge,
        EvalFeature.CONVERSATION_HISTORY: _grade_history,
        EvalFeature.ESCALATION: _grade_escalation,
    }
    results = tuple(
        CaseResult(case.id, case.feature, case.group, not (failures := graders[case.feature](case)), failures)
        for case in cases
    )
    return build_report(results)


def build_report(results: tuple[CaseResult, ...]) -> EvaluationReport:
    routine_passed: dict[EvalFeature, int] = {}
    routine_totals: dict[EvalFeature, int] = {}
    routine_scores: dict[EvalFeature, float] = {}
    for feature in EvalFeature:
        selected = [result for result in results if result.feature is feature and result.group is EvalGroup.ROUTINE]
        if not selected:
            raise ValueError(f"Missing routine cases for {feature.value}")
        routine_passed[feature] = sum(result.passed for result in selected)
        routine_totals[feature] = len(selected)
        routine_scores[feature] = routine_passed[feature] / len(selected)
    safety = [result for result in results if result.group is EvalGroup.SAFETY]
    if not safety:
        raise ValueError("Missing safety cases")
    safety_passed = sum(result.passed for result in safety)
    safety_score = safety_passed / len(safety)
    release_allowed = all(score >= ROUTINE_THRESHOLD for score in routine_scores.values()) and safety_score >= SAFETY_THRESHOLD
    return EvaluationReport(results, routine_passed, routine_totals, routine_scores, safety_passed, len(safety), safety_score, release_allowed)


def _render_report(report: EvaluationReport, output: TextIO) -> None:
    for result in report.results:
        print(f"{'PASS' if result.passed else 'FAIL'} {result.case_id} [offline]", file=output)
        for failure in result.failures:
            print(f"  - {failure}", file=output)
    labels = {
        EvalFeature.LATEST_BILL: "Latest bill routine",
        EvalFeature.UNEXPECTED_CHARGE: "Unexpected charge routine",
        EvalFeature.CONVERSATION_HISTORY: "Conversation history routine",
        EvalFeature.ESCALATION: "Escalation routine",
    }
    for feature in EvalFeature:
        score = report.routine_scores[feature]
        print(
            f"{labels[feature]}: {report.routine_passed[feature]}/{report.routine_totals[feature]} "
            f"({score:.1%}) — {'PASS' if score >= ROUTINE_THRESHOLD else 'FAIL'}",
            file=output,
        )
    print(
        f"Safety: {report.safety_passed}/{report.safety_total} ({report.safety_score:.1%}) "
        f"— {'PASS' if report.safety_score >= SAFETY_THRESHOLD else 'FAIL'}",
        file=output,
    )
    print(f"Release gate: {'PASS' if report.release_allowed else 'FAIL'}", file=output)


def run_cli(argv: Sequence[str] | None = None, *, stdout: TextIO | None = None) -> int:
    if argv:
        print("The MVP evaluation command accepts no arguments.", file=stdout or sys.stdout)
        return 2
    report = evaluate_cases(load_cases())
    _render_report(report, stdout or sys.stdout)
    return 0 if report.release_allowed else 1


def main() -> int:
    return run_cli()


if __name__ == "__main__":
    raise SystemExit(main())
