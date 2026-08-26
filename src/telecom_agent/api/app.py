from re import fullmatch
from typing import Annotated
from uuid import UUID

from fastapi import Depends, FastAPI, Request, Response, status
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.types import Lifespan

from telecom_agent.api.auth import UnauthorizedError, build_customer_authentication
from telecom_agent.api.schemas import (
    ConversationCreated,
    ErrorDetail,
    ErrorResponse,
    HealthResponse,
    MessageCreate,
    MessageExchangeCreated,
)
from telecom_agent.ports.conversations import (
    ConversationStore,
    CustomerIdentityRepository,
)
from telecom_agent.ports.health import DatabaseHealth
from telecom_agent.ports.messages import (
    CurrentPlanAnswerGenerator,
    CurrentPlanProvider,
    MessageExchangeRepository,
)
from telecom_agent.services.create_conversation import CreateConversationService
from telecom_agent.services.send_current_plan_message import (
    ConversationNotFoundError,
    SendCurrentPlanMessageService,
)


def create_app(
    *,
    customer_identities: CustomerIdentityRepository,
    conversations: ConversationStore,
    database_health: DatabaseHealth,
    current_plans: CurrentPlanProvider,
    answer_generator: CurrentPlanAnswerGenerator,
    exchanges: MessageExchangeRepository,
    lifespan: Lifespan[FastAPI] | None = None,
) -> FastAPI:
    app = FastAPI(title="Telecom Customer-Service Agent", lifespan=lifespan)
    authenticate = build_customer_authentication(customer_identities)
    create_conversation = CreateConversationService(repository=conversations)
    send_message = SendCurrentPlanMessageService(
        conversations=conversations,
        current_plans=current_plans,
        answer_generator=answer_generator,
        exchanges=exchanges,
    )

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

    @app.exception_handler(ConversationNotFoundError)
    async def handle_conversation_not_found(
        _request: Request,
        _error: ConversationNotFoundError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=ErrorResponse(
                error=ErrorDetail(
                    code="conversation_not_found",
                    message="Conversation not found.",
                )
            ).model_dump(),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request,
        error: RequestValidationError,
    ) -> Response:
        is_message_body_error = (
            request.method == "POST"
            and fullmatch(r"/v1/conversations/[^/]+/messages", request.url.path) is not None
            and any(item["loc"] and item["loc"][0] == "body" for item in error.errors())
        )
        if is_message_body_error:
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                content=ErrorResponse(
                    error=ErrorDetail(
                        code="invalid_message",
                        message="Message content must contain 1 to 2000 characters.",
                    )
                ).model_dump(),
            )
        return await request_validation_exception_handler(request, error)

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

    @app.post(
        "/v1/conversations/{conversation_id}/messages",
        response_model=MessageExchangeCreated,
        status_code=status.HTTP_201_CREATED,
        responses={
            status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
            status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ErrorResponse},
        },
    )
    def send_message_route(
        conversation_id: UUID,
        message: MessageCreate,
        customer_id: Annotated[UUID, Depends(authenticate)],
    ) -> MessageExchangeCreated:
        exchange = send_message.execute(
            customer_id=customer_id,
            conversation_id=conversation_id,
            content=message.content,
        )
        return MessageExchangeCreated.model_validate(exchange, from_attributes=True)

    @app.get(
        "/health",
        response_model=HealthResponse,
        responses={
            status.HTTP_503_SERVICE_UNAVAILABLE: {
                "model": HealthResponse,
                "description": "PostgreSQL is unavailable",
            }
        },
    )
    def health(response: Response) -> HealthResponse:
        if database_health.is_healthy():
            return HealthResponse(status="ok", database="ok")

        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return HealthResponse(status="unavailable", database="unavailable")

    return app
