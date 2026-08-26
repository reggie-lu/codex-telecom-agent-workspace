from datetime import date
from decimal import Decimal
from uuid import UUID

from telecom_agent.development import DEVELOPMENT_CUSTOMER
from telecom_agent.domain.plans import CurrentPlanDetails


class SyntheticKddiCurrentPlanProvider:
    def get_current_plan(self, customer_id: UUID) -> CurrentPlanDetails | None:
        if customer_id != DEVELOPMENT_CUSTOMER.customer_id:
            return None
        return CurrentPlanDetails(
            plan_code="SYN-KDDI-5G-20",
            plan_name="Synthetic KDDI 5G 20GB",
            data_allowance_gb=20,
            recurring_charge=Decimal("4500.00"),
            currency="JPY",
            effective_from=date(2026, 8, 1),
            source_version="synthetic-kddi-v1",
        )
