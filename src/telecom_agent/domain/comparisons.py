from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CatalogOfferDetails:
    plan_code: str
    plan_name: str
    data_allowance_gb: int
    recurring_charge: Decimal
    currency: str
    effective_from: date


@dataclass(frozen=True, slots=True)
class PlanCatalogDetails:
    offers: tuple[CatalogOfferDetails, ...]
    as_of: date
    source_version: str


@dataclass(frozen=True, slots=True)
class PlanComparisonOfferSnapshot:
    id: UUID
    plan_code: str
    plan_name: str
    data_allowance_gb: int
    recurring_charge: Decimal
    currency: str
    effective_from: date
    recurring_charge_delta: Decimal
    data_allowance_delta_gb: int


@dataclass(frozen=True, slots=True)
class PlanComparisonSnapshot:
    id: UUID
    customer_id: UUID
    current_plan_code: str
    current_plan_name: str
    current_data_allowance_gb: int
    current_recurring_charge: Decimal
    currency: str
    current_effective_from: date
    catalog_as_of: date
    retrieved_at: datetime
    source_version: str
    eligibility_verified: bool
    offers: tuple[PlanComparisonOfferSnapshot, ...]
