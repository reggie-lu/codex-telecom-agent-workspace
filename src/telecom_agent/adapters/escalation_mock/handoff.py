from telecom_agent.domain.escalations import Escalation, HandoffOutcome


class DeterministicMockHandoff:
    def submit(self, _escalation: Escalation) -> HandoffOutcome:
        return HandoffOutcome.ACCEPTED
