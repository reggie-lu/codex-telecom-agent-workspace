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
