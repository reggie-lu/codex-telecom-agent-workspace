from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID, uuid4

from telecom_agent.domain.escalations import (
    Escalation,
    EscalationHandoffContext,
    EscalationStatus,
    HandoffOutcome,
)
from telecom_agent.ports.conversations import ConversationHistoryRepository
from telecom_agent.ports.escalations import (
    EscalationRepository,
    HandoffUnavailableError,
    HumanHandoff,
)
from telecom_agent.services.errors import ConversationNotFoundError


class CreateEscalationService:
    def __init__(
        self,
        *,
        histories: ConversationHistoryRepository,
        escalations: EscalationRepository,
        handoff: HumanHandoff,
        id_factory: Callable[[], UUID] = uuid4,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._histories = histories
        self._escalations = escalations
        self._handoff = handoff
        self._id_factory = id_factory
        self._clock = clock or (lambda: datetime.now(UTC))

    def execute(self, *, customer_id: UUID, conversation_id: UUID, reason: str) -> Escalation:
        history = self._histories.get_history(conversation_id, customer_id)
        if history is None:
            raise ConversationNotFoundError

        created_at = self._clock()
        requested = Escalation(
            id=self._id_factory(),
            customer_id=customer_id,
            conversation_id=conversation_id,
            reason=reason,
            status=EscalationStatus.REQUESTED,
            created_at=created_at,
            updated_at=created_at,
            next_step=None,
            handoff_context=EscalationHandoffContext(conversation=history),
        )
        self._escalations.add_requested(requested)
        try:
            outcome = self._handoff.submit(requested)
        except HandoffUnavailableError:
            outcome = HandoffOutcome.FAILED
        target = (
            EscalationStatus.QUEUED
            if outcome is HandoffOutcome.ACCEPTED
            else EscalationStatus.FAILED
        )
        result = requested.transition(target, at=self._clock())
        self._escalations.update(result)
        return result
