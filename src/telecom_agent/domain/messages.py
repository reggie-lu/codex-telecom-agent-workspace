from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from telecom_agent.domain.bills import BillSnapshot
from telecom_agent.domain.charges import ChargeEvidenceSnapshot
from telecom_agent.domain.plans import PlanSnapshot


class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"


class AnswerStatus(StrEnum):
    GROUNDED = "grounded"
    UNAVAILABLE = "unavailable"
    UNSUPPORTED = "unsupported"


class EvidenceType(StrEnum):
    PLAN_SNAPSHOT = "plan_snapshot"
    BILL_SNAPSHOT = "bill_snapshot"
    CHARGE_SNAPSHOT = "charge_snapshot"


@dataclass(frozen=True, slots=True)
class EvidenceReference:
    type: EvidenceType
    id: UUID


@dataclass(frozen=True, slots=True)
class Message:
    id: UUID
    conversation_id: UUID
    role: MessageRole
    content: str
    created_at: datetime
    answer_status: AnswerStatus | None = None
    uncertain: bool | None = None
    evidence: tuple[EvidenceReference, ...] = ()


@dataclass(frozen=True, slots=True)
class MessageExchange:
    user_message: Message
    assistant_message: Message
    plan_snapshot: PlanSnapshot | None = None
    bill_snapshot: BillSnapshot | None = None
    charge_snapshot: ChargeEvidenceSnapshot | None = None
