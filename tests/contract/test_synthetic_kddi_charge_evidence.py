from datetime import date
from decimal import Decimal
from uuid import UUID

from telecom_agent.adapters.kddi_mock.charge_evidence import (
    SyntheticKddiChargeEvidenceProvider,
)
from telecom_agent.development import DEVELOPMENT_CUSTOMER
from telecom_agent.domain.charges import ChargeEvidenceState


def test_synthetic_roaming_item_has_approved_causal_evidence() -> None:
    evidence = SyntheticKddiChargeEvidenceProvider().get_charge_evidence(
        DEVELOPMENT_CUSTOMER.customer_id,
        "roaming_data",
    )

    assert evidence is not None
    assert evidence.description == "International roaming data"
    assert evidence.amount == Decimal("1200.00")
    assert evidence.currency == "JPY"
    assert evidence.occurred_on == date(2026, 7, 18)
    assert evidence.location == "United States"
    assert evidence.service_name == "Synthetic KDDI Overseas Data Day Pass"
    assert evidence.trigger == (
        "automatically activated when the device used mobile data while roaming"
    )
    assert evidence.state is ChargeEvidenceState.CONFIRMED
    assert evidence.source_version == "synthetic-kddi-charge-v1"


def test_unknown_customer_or_line_item_has_no_charge_evidence() -> None:
    provider = SyntheticKddiChargeEvidenceProvider()

    assert provider.get_charge_evidence(
        UUID("ffffffff-ffff-ffff-ffff-ffffffffffff"),
        "roaming_data",
    ) is None
    assert provider.get_charge_evidence(
        DEVELOPMENT_CUSTOMER.customer_id,
        "domestic_calls",
    ) is None
