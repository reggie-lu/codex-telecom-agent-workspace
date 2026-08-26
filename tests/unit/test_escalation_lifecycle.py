from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID

import pytest

from telecom_agent.domain.conversations import ConversationHistory, ConversationStatus
from telecom_agent.domain.escalations import (
    Escalation,
    EscalationHandoffContext,
    EscalationStatus,
    InvalidEscalationTransitionError,
)

NOW = datetime(2026, 8, 26, 20, 0, tzinfo=UTC)


def escalation(status: EscalationStatus) -> Escalation:
    return Escalation(
        id=UUID("30000000-0000-0000-0000-000000000001"),
        customer_id=UUID("10000000-0000-0000-0000-000000000001"),
        conversation_id=UUID("20000000-0000-0000-0000-000000000001"),
        reason="Please help.",
        status=status,
        created_at=NOW,
        updated_at=NOW,
        next_step=None,
        handoff_context=EscalationHandoffContext(
            conversation=ConversationHistory(
                id=UUID("20000000-0000-0000-0000-000000000001"),
                status=ConversationStatus.OPEN,
                created_at=NOW,
                messages=(),
            )
        ),
    )


@pytest.mark.parametrize(
    ("source", "target"),
    [
        (EscalationStatus.REQUESTED, EscalationStatus.QUEUED),
        (EscalationStatus.REQUESTED, EscalationStatus.FAILED),
        (EscalationStatus.QUEUED, EscalationStatus.ASSIGNED),
        (EscalationStatus.QUEUED, EscalationStatus.FAILED),
        (EscalationStatus.ASSIGNED, EscalationStatus.RESOLVED),
    ],
)
def test_approved_escalation_transitions(source: EscalationStatus, target: EscalationStatus) -> None:
    assert escalation(source).transition(target, at=NOW).status is target


def test_terminal_or_skipped_transition_is_rejected() -> None:
    with pytest.raises(InvalidEscalationTransitionError):
        escalation(EscalationStatus.REQUESTED).transition(EscalationStatus.RESOLVED, at=NOW)
    with pytest.raises(InvalidEscalationTransitionError):
        replace(escalation(EscalationStatus.RESOLVED), next_step=None).transition(
            EscalationStatus.QUEUED,
            at=NOW,
        )
