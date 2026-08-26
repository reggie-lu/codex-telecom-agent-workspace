from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints

from telecom_agent.domain.conversations import ConversationStatus
from telecom_agent.domain.escalations import EscalationStatus
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


class ConversationUserMessage(MessageCreated):
    role: Literal[MessageRole.USER]


class ConversationAssistantMessage(AssistantMessageCreated):
    role: Literal[MessageRole.ASSISTANT]


ConversationHistoryMessage = Annotated[
    ConversationUserMessage | ConversationAssistantMessage,
    Field(discriminator="role"),
]


class ConversationHistoryResponse(BaseModel):
    id: UUID
    status: ConversationStatus
    created_at: datetime
    messages: list[ConversationHistoryMessage]


class EscalationCreate(BaseModel):
    reason: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]


class EscalationResponse(BaseModel):
    id: UUID
    conversation_id: UUID
    reason: str
    status: EscalationStatus
    created_at: datetime
    updated_at: datetime
    next_step: str | None
