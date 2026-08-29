from datetime import date
from decimal import Decimal

from telecom_agent.adapters.kddi_mock.plan_catalog import SyntheticKddiPlanCatalogProvider


def test_synthetic_catalog_returns_the_three_approved_offers_in_source_order() -> None:
    catalog = SyntheticKddiPlanCatalogProvider().get_plan_catalog()

    assert catalog is not None
    assert catalog.source_version == "synthetic-kddi-catalog-2026-08-28"
    assert catalog.as_of == date(2026, 8, 28)
    assert [
        (offer.plan_code, offer.plan_name, offer.data_allowance_gb, offer.recurring_charge)
        for offer in catalog.offers
    ] == [
        ("SYN-KDDI-LITE-5", "Synthetic KDDI Lite 5GB", 5, Decimal("2800.00")),
        ("SYN-KDDI-PLUS-30", "Synthetic KDDI Plus 30GB", 30, Decimal("5200.00")),
        ("SYN-KDDI-MAX-100", "Synthetic KDDI Max 100GB", 100, Decimal("7500.00")),
    ]
    assert all(offer.currency == "JPY" for offer in catalog.offers)
    assert all(offer.effective_from == date(2026, 8, 28) for offer in catalog.offers)


def test_synthetic_catalog_does_not_depend_on_customer_identity() -> None:
    first = SyntheticKddiPlanCatalogProvider().get_plan_catalog()
    second = SyntheticKddiPlanCatalogProvider().get_plan_catalog()

    assert first == second
