from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class ConversationStatus(StrEnum):
    OPEN = "open"


@dataclass(frozen=True, slots=True)
class Conversation:
    id: UUID
    customer_id: UUID
    status: ConversationStatus
    created_at: datetime
