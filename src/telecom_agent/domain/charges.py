from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID


class ChargeEvidenceState(StrEnum):
    CONFIRMED = "confirmed"
    STALE = "stale"


@dataclass(frozen=True, slots=True)
class ChargeEvidenceDetails:
    line_item_code: str
    description: str
    amount: Decimal
    currency: str
    occurred_on: date
    location: str
    service_name: str
    trigger: str
    state: ChargeEvidenceState
    source_version: str


@dataclass(frozen=True, slots=True)
class ChargeEvidenceSnapshot:
    id: UUID
    customer_id: UUID
    line_item_code: str
    description: str
    amount: Decimal
    currency: str
    occurred_on: date
    location: str
    service_name: str
    trigger: str
    state: ChargeEvidenceState
    retrieved_at: datetime
    source_version: str
