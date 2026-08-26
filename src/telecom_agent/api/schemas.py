from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, StringConstraints

from telecom_agent.domain.conversations import ConversationStatus
from telecom_agent.domain.messages import AnswerStatus, EvidenceType, MessageRole


class ConversationCreated(BaseModel):
    id: UUID
    status: ConversationStatus
    created_at: datetime


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail


class HealthResponse(BaseModel):
    status: Literal["ok", "unavailable"]
    database: Literal["ok", "unavailable"]


class MessageCreate(BaseModel):
    content: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]


class MessageCreated(BaseModel):
    id: UUID
    role: MessageRole
    content: str
    created_at: datetime


class EvidenceCreated(BaseModel):
    type: EvidenceType
    id: UUID


class AssistantMessageCreated(MessageCreated):
    answer_status: AnswerStatus
    uncertain: bool
    evidence: list[EvidenceCreated]


class MessageExchangeCreated(BaseModel):
    user_message: MessageCreated
    assistant_message: AssistantMessageCreated
