from datetime import date
from decimal import Decimal
from uuid import UUID

from telecom_agent.development import DEVELOPMENT_CUSTOMER
from telecom_agent.domain.bills import BillLineItem, LatestBillDetails


class SyntheticKddiLatestBillProvider:
    def get_latest_bill(self, customer_id: UUID) -> LatestBillDetails | None:
        if customer_id != DEVELOPMENT_CUSTOMER.customer_id:
            return None
        return LatestBillDetails(
            period_start=date(2026, 7, 1),
            period_end=date(2026, 7, 31),
            total=Decimal("6930.00"),
            currency="JPY",
            line_items=(
                BillLineItem(
                    code="monthly_service",
                    description="Monthly mobile service",
                    amount=Decimal("4500.00"),
                ),
                BillLineItem(
                    code="domestic_calls",
                    description="Domestic calls",
                    amount=Decimal("600.00"),
                ),
                BillLineItem(
                    code="roaming_data",
                    description="International roaming data",
                    amount=Decimal("1200.00"),
                ),
                BillLineItem(
                    code="taxes_fees",
                    description="Taxes and fees",
                    amount=Decimal("630.00"),
                ),
            ),
            source_version="synthetic-kddi-bill-v1",
        )
