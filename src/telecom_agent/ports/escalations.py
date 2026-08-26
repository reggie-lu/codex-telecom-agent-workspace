from typing import Protocol
from uuid import UUID

from telecom_agent.domain.escalations import Escalation, HandoffOutcome


class HandoffUnavailableError(Exception):
    """The handoff provider did not return an accepted or rejected outcome."""


class EscalationRepository(Protocol):
    def add_requested(self, escalation: Escalation) -> None: ...

    def update(self, escalation: Escalation) -> None: ...

    def get_owned(self, escalation_id: UUID, customer_id: UUID) -> Escalation | None: ...


class HumanHandoff(Protocol):
    def submit(self, escalation: Escalation) -> HandoffOutcome: ...
