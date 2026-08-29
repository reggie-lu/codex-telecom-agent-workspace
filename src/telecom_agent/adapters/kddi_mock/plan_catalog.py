from datetime import date
from decimal import Decimal

from telecom_agent.domain.comparisons import CatalogOfferDetails, PlanCatalogDetails


class SyntheticKddiPlanCatalogProvider:
    def get_plan_catalog(self) -> PlanCatalogDetails:
        effective_from = date(2026, 8, 28)
        return PlanCatalogDetails(
            offers=(
                CatalogOfferDetails(
                    plan_code="SYN-KDDI-LITE-5",
                    plan_name="Synthetic KDDI Lite 5GB",
                    data_allowance_gb=5,
                    recurring_charge=Decimal("2800.00"),
                    currency="JPY",
                    effective_from=effective_from,
                ),
                CatalogOfferDetails(
                    plan_code="SYN-KDDI-PLUS-30",
                    plan_name="Synthetic KDDI Plus 30GB",
                    data_allowance_gb=30,
                    recurring_charge=Decimal("5200.00"),
                    currency="JPY",
                    effective_from=effective_from,
                ),
                CatalogOfferDetails(
                    plan_code="SYN-KDDI-MAX-100",
                    plan_name="Synthetic KDDI Max 100GB",
                    data_allowance_gb=100,
                    recurring_charge=Decimal("7500.00"),
                    currency="JPY",
                    effective_from=effective_from,
                ),
            ),
            as_of=effective_from,
            source_version="synthetic-kddi-catalog-2026-08-28",
        )
