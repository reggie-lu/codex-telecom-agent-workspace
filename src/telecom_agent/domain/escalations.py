from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from telecom_agent.domain.conversations import ConversationHistory

FAILED_NEXT_STEP = "Please try requesting human support again later."


class EscalationStatus(StrEnum):
    REQUESTED = "requested"
    QUEUED = "queued"
    ASSIGNED = "assigned"
    RESOLVED = "resolved"
    FAILED = "failed"


class HandoffOutcome(StrEnum):
    ACCEPTED = "accepted"
    FAILED = "failed"


class InvalidEscalationTransitionError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class EscalationHandoffContext:
    conversation: ConversationHistory


@dataclass(frozen=True, slots=True)
class Escalation:
    id: UUID
    customer_id: UUID
    conversation_id: UUID
    reason: str
    status: EscalationStatus
    created_at: datetime
    updated_at: datetime
    next_step: str | None
    handoff_context: EscalationHandoffContext

    def transition(self, status: EscalationStatus, *, at: datetime) -> "Escalation":
        allowed = {
            EscalationStatus.REQUESTED: {EscalationStatus.QUEUED, EscalationStatus.FAILED},
            EscalationStatus.QUEUED: {EscalationStatus.ASSIGNED, EscalationStatus.FAILED},
            EscalationStatus.ASSIGNED: {EscalationStatus.RESOLVED},
            EscalationStatus.RESOLVED: set(),
            EscalationStatus.FAILED: set(),
        }
        if status not in allowed[self.status]:
            raise InvalidEscalationTransitionError(
                f"Cannot transition escalation from {self.status} to {status}."
            )
        return replace(
            self,
            status=status,
            updated_at=at,
            next_step=FAILED_NEXT_STEP if status is EscalationStatus.FAILED else None,
        )
