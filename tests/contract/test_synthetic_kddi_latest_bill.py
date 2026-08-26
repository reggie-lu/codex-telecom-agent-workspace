from datetime import date
from decimal import Decimal
from uuid import UUID

from telecom_agent.adapters.kddi_mock.latest_bills import SyntheticKddiLatestBillProvider
from telecom_agent.development import DEVELOPMENT_CUSTOMER


def test_synthetic_alice_has_approved_reconciled_latest_bill() -> None:
    bill = SyntheticKddiLatestBillProvider().get_latest_bill(DEVELOPMENT_CUSTOMER.customer_id)

    assert bill is not None
    assert bill.period_start == date(2026, 7, 1)
    assert bill.period_end == date(2026, 7, 31)
    assert bill.total == Decimal("6930.00")
    assert bill.currency == "JPY"
    assert [(item.description, item.amount) for item in bill.line_items] == [
        ("Monthly mobile service", Decimal("4500.00")),
        ("Domestic calls", Decimal("600.00")),
        ("International roaming data", Decimal("1200.00")),
        ("Taxes and fees", Decimal("630.00")),
    ]
    assert sum((item.amount for item in bill.line_items), Decimal()) == bill.total
    assert bill.source_version == "synthetic-kddi-bill-v1"


def test_unknown_customer_has_no_synthetic_bill() -> None:
    bill = SyntheticKddiLatestBillProvider().get_latest_bill(
        UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")
    )

    assert bill is None
