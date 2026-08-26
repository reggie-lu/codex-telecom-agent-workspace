from uuid import UUID

from telecom_agent.domain.escalations import Escalation, HandoffOutcome
from telecom_agent.domain.plans import GroundedCurrentPlanFacts


class DeterministicAnswerGenerator:
    """Offline model boundary used by API and PostgreSQL tests."""

    def generate(self, *, question: str, facts: GroundedCurrentPlanFacts) -> str:
        del question
        return (
            f"Your current plan is {facts.plan_name}. "
            f"It includes {facts.data_allowance} of domestic data. "
            f"The recorded monthly recurring charge is {facts.recurring_charge}. "
            f"The plan has been effective since {facts.effective_date}."
        )


class UnusedEscalations:
    def add_requested(self, _escalation: Escalation) -> None:
        raise AssertionError("This request must not create an escalation")

    def update(self, _escalation: Escalation) -> None:
        raise AssertionError("This request must not update an escalation")

    def get_owned(self, _escalation_id: UUID, _customer_id: UUID) -> Escalation | None:
        raise AssertionError("This request must not retrieve an escalation")


class UnusedHandoff:
    def submit(self, _escalation: Escalation) -> HandoffOutcome:
        raise AssertionError("This request must not call human handoff")
