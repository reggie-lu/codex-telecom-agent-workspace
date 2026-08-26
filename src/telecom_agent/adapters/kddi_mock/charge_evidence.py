from datetime import date
from decimal import Decimal
from uuid import UUID

from telecom_agent.development import DEVELOPMENT_CUSTOMER
from telecom_agent.domain.charges import ChargeEvidenceDetails, ChargeEvidenceState


class SyntheticKddiChargeEvidenceProvider:
    def get_charge_evidence(
        self,
        customer_id: UUID,
        line_item_code: str,
    ) -> ChargeEvidenceDetails | None:
        if customer_id != DEVELOPMENT_CUSTOMER.customer_id or line_item_code != "roaming_data":
            return None
        return ChargeEvidenceDetails(
            line_item_code="roaming_data",
            description="International roaming data",
            amount=Decimal("1200.00"),
            currency="JPY",
            occurred_on=date(2026, 7, 18),
            location="United States",
            service_name="Synthetic KDDI Overseas Data Day Pass",
            trigger="automatically activated when the device used mobile data while roaming",
            state=ChargeEvidenceState.CONFIRMED,
            source_version="synthetic-kddi-charge-v1",
        )
