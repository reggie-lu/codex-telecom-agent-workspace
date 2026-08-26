from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID


class BillAvailability(StrEnum):
    AVAILABLE = "available"


@dataclass(frozen=True, slots=True)
class BillLineItem:
    code: str
    description: str
    amount: Decimal


@dataclass(frozen=True, slots=True)
class LatestBillDetails:
    period_start: date
    period_end: date
    total: Decimal
    currency: str
    line_items: tuple[BillLineItem, ...]
    source_version: str


@dataclass(frozen=True, slots=True)
class BillLineItemSnapshot:
    id: UUID
    code: str
    description: str
    amount: Decimal


@dataclass(frozen=True, slots=True)
class BillSnapshot:
    id: UUID
    customer_id: UUID
    period_start: date
    period_end: date
    total: Decimal
    currency: str
    line_items: tuple[BillLineItemSnapshot, ...]
    retrieved_at: datetime
    source_version: str
    availability: BillAvailability = BillAvailability.AVAILABLE
