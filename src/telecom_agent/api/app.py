from typing import Annotated
from uuid import UUID

from fastapi import Depends, FastAPI, Request, status
from fastapi.responses import JSONResponse

from telecom_agent.api.auth import UnauthorizedError, build_customer_authentication
from telecom_agent.api.schemas import ConversationCreated, ErrorDetail, ErrorResponse
from telecom_agent.ports.conversations import (
    ConversationRepository,
    CustomerIdentityRepository,
)
from telecom_agent.services.create_conversation import CreateConversationService


def create_app(
    *,
    customer_identities: CustomerIdentityRepository,
    conversations: ConversationRepository,
) -> FastAPI:
    app = FastAPI(title="Telecom Customer-Service Agent")
    authenticate = build_customer_authentication(customer_identities)
    create_conversation = CreateConversationService(repository=conversations)

    @app.exception_handler(UnauthorizedError)
    async def handle_unauthorized(
        _request: Request,
        _error: UnauthorizedError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            headers={"WWW-Authenticate": "Bearer"},
            content=ErrorResponse(
                error=ErrorDetail(
                    code="unauthorized",
                    message="A valid synthetic bearer token is required.",
                )
            ).model_dump(),
        )

    @app.post(
        "/v1/conversations",
        response_model=ConversationCreated,
        status_code=status.HTTP_201_CREATED,
    )
    def create_conversation_route(
        customer_id: Annotated[UUID, Depends(authenticate)],
    ) -> ConversationCreated:
        conversation = create_conversation.execute(customer_id=customer_id)
        return ConversationCreated.model_validate(conversation, from_attributes=True)

    return app
