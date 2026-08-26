from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID


class PlanAvailability(StrEnum):
    AVAILABLE = "available"


@dataclass(frozen=True, slots=True)
class CurrentPlanDetails:
    plan_code: str
    plan_name: str
    data_allowance_gb: int
    recurring_charge: Decimal
    currency: str
    effective_from: date
    source_version: str


@dataclass(frozen=True, slots=True)
class GroundedCurrentPlanFacts:
    """Canonical display values that a model may use in a current-plan answer."""

    plan_name: str
    data_allowance: str
    recurring_charge: str
    effective_date: str


@dataclass(frozen=True, slots=True)
class PlanSnapshot:
    id: UUID
    customer_id: UUID
    plan_code: str
    plan_name: str
    data_allowance_gb: int
    recurring_charge: Decimal
    currency: str
    effective_from: date
    retrieved_at: datetime
    source_version: str
    availability: PlanAvailability = PlanAvailability.AVAILABLE
