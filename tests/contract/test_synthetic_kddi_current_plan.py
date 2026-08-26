from decimal import Decimal
from uuid import UUID

from telecom_agent.adapters.kddi_mock.current_plans import SyntheticKddiCurrentPlanProvider
from telecom_agent.development import DEVELOPMENT_CUSTOMER


def test_synthetic_alice_has_stable_current_plan_evidence() -> None:
    provider = SyntheticKddiCurrentPlanProvider()

    plan = provider.get_current_plan(DEVELOPMENT_CUSTOMER.customer_id)

    assert plan is not None
    assert plan.plan_code == "SYN-KDDI-5G-20"
    assert plan.plan_name == "Synthetic KDDI 5G 20GB"
    assert plan.data_allowance_gb == 20
    assert plan.recurring_charge == Decimal("4500.00")
    assert plan.currency == "JPY"
    assert plan.source_version == "synthetic-kddi-v1"


def test_unknown_synthetic_customer_has_unavailable_plan_data() -> None:
    provider = SyntheticKddiCurrentPlanProvider()

    assert provider.get_current_plan(UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")) is None
