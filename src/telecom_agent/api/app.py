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
    ConversationHistoryResponse,
    ErrorDetail,
    ErrorResponse,
    EscalationCreate,
    EscalationResponse,
    HealthResponse,
    MessageCreate,
    MessageExchangeCreated,
)
from telecom_agent.ports.conversations import (
    ConversationStore,
    CustomerIdentityRepository,
)
from telecom_agent.ports.escalations import EscalationRepository, HumanHandoff
from telecom_agent.ports.health import DatabaseHealth
from telecom_agent.ports.messages import (
    ChargeEvidenceProvider,
    CurrentPlanAnswerGenerator,
    CurrentPlanProvider,
    LatestBillProvider,
    MessageExchangeRepository,
)
from telecom_agent.services.create_conversation import CreateConversationService
from telecom_agent.services.create_escalation import CreateEscalationService
from telecom_agent.services.errors import (
    ActiveEscalationExistsError,
    ConversationNotFoundError,
    EscalationNotFoundError,
)
from telecom_agent.services.get_conversation_history import GetConversationHistoryService
from telecom_agent.services.get_escalation import GetEscalationService
from telecom_agent.services.send_support_message import SendSupportMessageService


def create_app(
    *,
    customer_identities: CustomerIdentityRepository,
    conversations: ConversationStore,
    escalations: EscalationRepository,
    handoff: HumanHandoff,
    database_health: DatabaseHealth,
    current_plans: CurrentPlanProvider,
    answer_generator: CurrentPlanAnswerGenerator,
    exchanges: MessageExchangeRepository,
    latest_bills: LatestBillProvider | None = None,
    charge_evidence: ChargeEvidenceProvider | None = None,
    lifespan: Lifespan[FastAPI] | None = None,
) -> FastAPI:
    app = FastAPI(title="Telecom Customer-Service Agent", lifespan=lifespan)
    authenticate = build_customer_authentication(customer_identities)
    create_conversation = CreateConversationService(repository=conversations)
    get_conversation_history = GetConversationHistoryService(repository=conversations)
    create_escalation = CreateEscalationService(
        histories=conversations,
        escalations=escalations,
        handoff=handoff,
    )
    get_escalation = GetEscalationService(repository=escalations)
    send_message = SendSupportMessageService(
        conversations=conversations,
        current_plans=current_plans,
        latest_bills=latest_bills,
        charge_evidence=charge_evidence,
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

    @app.exception_handler(EscalationNotFoundError)
    async def handle_escalation_not_found(
        _request: Request,
        _error: EscalationNotFoundError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=ErrorResponse(
                error=ErrorDetail(
                    code="escalation_not_found",
                    message="Escalation not found.",
                )
            ).model_dump(),
        )

    @app.exception_handler(ActiveEscalationExistsError)
    async def handle_active_escalation_exists(
        _request: Request,
        _error: ActiveEscalationExistsError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=ErrorResponse(
                error=ErrorDetail(
                    code="escalation_already_active",
                    message="This conversation already has an active escalation.",
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
        is_escalation_body_error = (
            request.method == "POST"
            and fullmatch(r"/v1/conversations/[^/]+/escalations", request.url.path) is not None
            and any(item["loc"] and item["loc"][0] == "body" for item in error.errors())
        )
        if is_escalation_body_error:
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                content=ErrorResponse(
                    error=ErrorDetail(
                        code="invalid_escalation_reason",
                        message="Escalation reason must contain 1 to 1000 characters.",
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

    @app.get(
        "/v1/conversations/{conversation_id}",
        response_model=ConversationHistoryResponse,
        responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
    )
    def get_conversation_route(
        conversation_id: UUID,
        customer_id: Annotated[UUID, Depends(authenticate)],
    ) -> ConversationHistoryResponse:
        history = get_conversation_history.execute(
            customer_id=customer_id,
            conversation_id=conversation_id,
        )
        return ConversationHistoryResponse.model_validate(history, from_attributes=True)

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

    @app.post(
        "/v1/conversations/{conversation_id}/escalations",
        response_model=EscalationResponse,
        status_code=status.HTTP_201_CREATED,
        responses={
            status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
            status.HTTP_409_CONFLICT: {"model": ErrorResponse},
            status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ErrorResponse},
        },
    )
    def create_escalation_route(
        conversation_id: UUID,
        request: EscalationCreate,
        customer_id: Annotated[UUID, Depends(authenticate)],
    ) -> EscalationResponse:
        escalation = create_escalation.execute(
            customer_id=customer_id,
            conversation_id=conversation_id,
            reason=request.reason,
        )
        return EscalationResponse.model_validate(escalation, from_attributes=True)

    @app.get(
        "/v1/escalations/{escalation_id}",
        response_model=EscalationResponse,
        responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
    )
    def get_escalation_route(
        escalation_id: UUID,
        customer_id: Annotated[UUID, Depends(authenticate)],
    ) -> EscalationResponse:
        escalation = get_escalation.execute(
            escalation_id=escalation_id,
            customer_id=customer_id,
        )
        return EscalationResponse.model_validate(escalation, from_attributes=True)

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
