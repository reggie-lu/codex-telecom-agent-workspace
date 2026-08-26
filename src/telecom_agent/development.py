from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class SyntheticCustomerSeed:
    customer_id: UUID
    display_name: str
    raw_token: str


DEVELOPMENT_CUSTOMER = SyntheticCustomerSeed(
    customer_id=UUID("10000000-0000-0000-0000-000000000001"),
    display_name="Synthetic Alice",
    raw_token="synthetic-alice-token",
)
