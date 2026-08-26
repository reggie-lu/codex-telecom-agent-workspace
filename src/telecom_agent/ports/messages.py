from typing import Protocol
from uuid import UUID

from telecom_agent.domain.messages import MessageExchange
from telecom_agent.domain.plans import CurrentPlanDetails


class ConversationAccessRepository(Protocol):
    def is_owned_by(self, conversation_id: UUID, customer_id: UUID) -> bool: ...


class CurrentPlanProvider(Protocol):
    def get_current_plan(self, customer_id: UUID) -> CurrentPlanDetails | None: ...


class MessageExchangeRepository(Protocol):
    def add(self, exchange: MessageExchange) -> None: ...
