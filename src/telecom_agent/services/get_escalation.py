from uuid import UUID

from telecom_agent.domain.escalations import Escalation
from telecom_agent.ports.escalations import EscalationRepository
from telecom_agent.services.errors import EscalationNotFoundError


class GetEscalationService:
    def __init__(self, repository: EscalationRepository) -> None:
        self._repository = repository

    def execute(self, *, escalation_id: UUID, customer_id: UUID) -> Escalation:
        escalation = self._repository.get_owned(escalation_id, customer_id)
        if escalation is None:
            raise EscalationNotFoundError
        return escalation
