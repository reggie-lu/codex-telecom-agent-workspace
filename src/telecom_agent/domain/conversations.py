from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from telecom_agent.domain.messages import Message


class ConversationStatus(StrEnum):
    OPEN = "open"


@dataclass(frozen=True, slots=True)
class Conversation:
    id: UUID
    customer_id: UUID
    status: ConversationStatus
    created_at: datetime


@dataclass(frozen=True, slots=True)
class ConversationHistory:
    id: UUID
    status: ConversationStatus
    created_at: datetime
    messages: tuple[Message, ...]
