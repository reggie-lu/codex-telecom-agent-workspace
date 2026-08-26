from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID

import pytest

from telecom_agent.domain.conversations import ConversationHistory, ConversationStatus
from telecom_agent.domain.escalations import Escalation, EscalationStatus, HandoffOutcome
from telecom_agent.domain.messages import (
    AnswerStatus,
    EvidenceReference,
    EvidenceType,
    Message,
    MessageRole,
)
from telecom_agent.ports.escalations import HandoffUnavailableError
from telecom_agent.services.create_escalation import CreateEscalationService
from telecom_agent.services.errors import (
    ActiveEscalationExistsError,
    ConversationNotFoundError,
)

CUSTOMER_ID = UUID("10000000-0000-0000-0000-000000000001")
CONVERSATION_ID = UUID("20000000-0000-0000-0000-000000000001")
ESCALATION_ID = UUID("30000000-0000-0000-0000-000000000001")
EVIDENCE_ID = UUID("40000000-0000-0000-0000-000000000001")
NOW = datetime(2026, 8, 26, 20, 0, tzinfo=UTC)
LATER = datetime(2026, 8, 26, 20, 0, 1, tzinfo=UTC)


def conversation_history() -> ConversationHistory:
    return ConversationHistory(
        id=CONVERSATION_ID,
        status=ConversationStatus.OPEN,
        created_at=NOW,
        messages=(
            Message(
                id=UUID("50000000-0000-0000-0000-000000000001"),
                conversation_id=CONVERSATION_ID,
                role=MessageRole.USER,
                content="Why is my bill higher?",
                created_at=NOW,
            ),
            Message(
                id=UUID("50000000-0000-0000-0000-000000000002"),
                conversation_id=CONVERSATION_ID,
                role=MessageRole.ASSISTANT,
                content="The roaming item needs human review if unrecognized.",
                created_at=LATER,
                answer_status=AnswerStatus.GROUNDED,
                uncertain=False,
                evidence=(EvidenceReference(EvidenceType.CHARGE_SNAPSHOT, EVIDENCE_ID),),
            ),
        ),
    )


class StubHistories:
    def __init__(self, history: ConversationHistory | None) -> None:
        self.history = history

    def get_history(self, conversation_id: UUID, customer_id: UUID) -> ConversationHistory | None:
        assert conversation_id == CONVERSATION_ID
        assert customer_id == CUSTOMER_ID
        return self.history


class RecordingEscalations:
    def __init__(self, duplicate: bool = False) -> None:
        self.duplicate = duplicate
        self.added: list[Escalation] = []
        self.updated: list[Escalation] = []

    def add_requested(self, escalation: Escalation) -> None:
        if self.duplicate:
            raise ActiveEscalationExistsError
        assert escalation.status is EscalationStatus.REQUESTED
        self.added.append(escalation)

    def update(self, escalation: Escalation) -> None:
        self.updated.append(escalation)

    def get_owned(self, escalation_id: UUID, customer_id: UUID) -> None:
        raise AssertionError("Creation must not retrieve escalation status")


class StubHandoff:
    def __init__(self, outcome: HandoffOutcome) -> None:
        self.outcome = outcome
        self.received: list[Escalation] = []

    def submit(self, escalation: Escalation) -> HandoffOutcome:
        self.received.append(escalation)
        return self.outcome


class UnavailableHandoff:
    def submit(self, _escalation: Escalation) -> HandoffOutcome:
        raise HandoffUnavailableError


def clock() -> Callable[[], datetime]:
    values = iter((NOW, LATER))
    return lambda: next(values)


def test_accepted_handoff_persists_requested_before_returning_queued_context() -> None:
    repository = RecordingEscalations()
    handoff = StubHandoff(HandoffOutcome.ACCEPTED)
    service = CreateEscalationService(
        histories=StubHistories(conversation_history()),
        escalations=repository,
        handoff=handoff,
        id_factory=lambda: ESCALATION_ID,
        clock=clock(),
    )

    result = service.execute(
        customer_id=CUSTOMER_ID,
        conversation_id=CONVERSATION_ID,
        reason="I do not recognize this roaming charge.",
    )

    assert repository.added[0].status is EscalationStatus.REQUESTED
    assert handoff.received == repository.added
    assert result.status is EscalationStatus.QUEUED
    assert result.next_step is None
    assert repository.updated == [result]
    assert result.handoff_context.conversation == conversation_history()


def test_failed_handoff_remains_durable_with_safe_next_step() -> None:
    repository = RecordingEscalations()
    result = CreateEscalationService(
        histories=StubHistories(conversation_history()),
        escalations=repository,
        handoff=StubHandoff(HandoffOutcome.FAILED),
        id_factory=lambda: ESCALATION_ID,
        clock=clock(),
    ).execute(
        customer_id=CUSTOMER_ID,
        conversation_id=CONVERSATION_ID,
        reason="Please help.",
    )

    assert result.status is EscalationStatus.FAILED
    assert result.next_step == "Please try requesting human support again later."
    assert repository.added[0].status is EscalationStatus.REQUESTED
    assert repository.updated == [result]


def test_unavailable_handoff_is_also_persisted_as_failed() -> None:
    repository = RecordingEscalations()
    result = CreateEscalationService(
        histories=StubHistories(conversation_history()),
        escalations=repository,
        handoff=UnavailableHandoff(),
        id_factory=lambda: ESCALATION_ID,
        clock=clock(),
    ).execute(
        customer_id=CUSTOMER_ID,
        conversation_id=CONVERSATION_ID,
        reason="Please help.",
    )

    assert result.status is EscalationStatus.FAILED
    assert repository.added[0].status is EscalationStatus.REQUESTED
    assert repository.updated == [result]


def test_missing_or_cross_customer_conversation_does_not_create_handoff() -> None:
    repository = RecordingEscalations()
    handoff = StubHandoff(HandoffOutcome.ACCEPTED)

    with pytest.raises(ConversationNotFoundError):
        CreateEscalationService(
            histories=StubHistories(None),
            escalations=repository,
            handoff=handoff,
        ).execute(
            customer_id=CUSTOMER_ID,
            conversation_id=CONVERSATION_ID,
            reason="Please help.",
        )

    assert repository.added == []
    assert handoff.received == []


def test_duplicate_active_escalation_does_not_call_handoff() -> None:
    handoff = StubHandoff(HandoffOutcome.ACCEPTED)

    with pytest.raises(ActiveEscalationExistsError):
        CreateEscalationService(
            histories=StubHistories(conversation_history()),
            escalations=RecordingEscalations(duplicate=True),
            handoff=handoff,
        ).execute(
            customer_id=CUSTOMER_ID,
            conversation_id=CONVERSATION_ID,
            reason="Please help.",
        )

    assert handoff.received == []
