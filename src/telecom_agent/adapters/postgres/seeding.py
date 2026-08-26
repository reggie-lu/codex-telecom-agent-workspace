from datetime import UTC, datetime
from enum import StrEnum
from hashlib import sha256

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from telecom_agent.adapters.postgres.models import SyntheticCustomerRecord
from telecom_agent.development import SyntheticCustomerSeed


class SeedResult(StrEnum):
    CREATED = "created"
    EXISTING = "existing"


def seed_synthetic_customer(
    session_factory: sessionmaker[Session],
    seed: SyntheticCustomerSeed,
) -> SeedResult:
    token_hash = sha256(seed.raw_token.encode()).hexdigest()
    with session_factory.begin() as session:
        existing_id = session.scalar(
            select(SyntheticCustomerRecord.id).where(
                SyntheticCustomerRecord.token_hash == token_hash
            )
        )
        if existing_id is not None:
            return SeedResult.EXISTING

        session.add(
            SyntheticCustomerRecord(
                id=seed.customer_id,
                display_name=seed.display_name,
                token_hash=token_hash,
                created_at=datetime.now(UTC),
            )
        )
    return SeedResult.CREATED
