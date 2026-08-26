from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from telecom_agent.domain.conversations import ConversationStatus


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
