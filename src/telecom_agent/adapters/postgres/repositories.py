from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from telecom_agent.adapters.postgres.models import (
    BillLineItemRecord,
    BillSnapshotRecord,
    ChargeEvidenceSnapshotRecord,
    ConversationRecord,
    EscalationRecord,
    MessageBillEvidenceRecord,
    MessageChargeEvidenceRecord,
    MessagePlanEvidenceRecord,
    MessageRecord,
    PlanSnapshotRecord,
    SyntheticCustomerRecord,
)
from telecom_agent.domain.conversations import (
    Conversation,
    ConversationHistory,
    ConversationStatus,
)
from telecom_agent.domain.escalations import Escalation, EscalationHandoffContext, EscalationStatus
from telecom_agent.domain.messages import (
    AnswerStatus,
    EvidenceReference,
    EvidenceType,
    Message,
    MessageExchange,
    MessageRole,
)
from telecom_agent.services.errors import ActiveEscalationExistsError


def _handoff_context_to_json(context: EscalationHandoffContext) -> dict[str, object]:
    conversation = context.conversation
    return {
        "conversation": {
            "id": str(conversation.id),
            "status": conversation.status.value,
            "created_at": conversation.created_at.isoformat(),
            "messages": [
                {
                    "id": str(message.id),
                    "conversation_id": str(message.conversation_id),
                    "role": message.role.value,
                    "content": message.content,
                    "created_at": message.created_at.isoformat(),
                    "answer_status": (
                        message.answer_status.value if message.answer_status is not None else None
                    ),
                    "uncertain": message.uncertain,
                    "evidence": [
                        {"type": evidence.type.value, "id": str(evidence.id)}
                        for evidence in message.evidence
                    ],
                }
                for message in conversation.messages
            ],
        }
    }


def _handoff_context_from_json(payload: dict[str, Any]) -> EscalationHandoffContext:
    conversation = payload["conversation"]
    messages = tuple(
        Message(
            id=UUID(item["id"]),
            conversation_id=UUID(item["conversation_id"]),
            role=MessageRole(item["role"]),
            content=item["content"],
            created_at=datetime.fromisoformat(item["created_at"]),
            answer_status=(
                AnswerStatus(item["answer_status"])
                if item["answer_status"] is not None
                else None
            ),
            uncertain=item["uncertain"],
            evidence=tuple(
                EvidenceReference(EvidenceType(evidence["type"]), UUID(evidence["id"]))
                for evidence in item["evidence"]
            ),
        )
        for item in conversation["messages"]
    )
    return EscalationHandoffContext(
        conversation=ConversationHistory(
            id=UUID(conversation["id"]),
            status=ConversationStatus(conversation["status"]),
            created_at=datetime.fromisoformat(conversation["created_at"]),
            messages=messages,
        )
    )


class SqlAlchemyCustomerIdentityRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def find_customer_id(self, token_hash: str) -> UUID | None:
        with self._session_factory() as session:
            return session.scalar(
                select(SyntheticCustomerRecord.id).where(
                    SyntheticCustomerRecord.token_hash == token_hash
                )
            )


class SqlAlchemyConversationRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def add(self, conversation: Conversation) -> None:
        with self._session_factory.begin() as session:
            session.add(
                ConversationRecord(
                    id=conversation.id,
                    customer_id=conversation.customer_id,
                    status=conversation.status.value,
                    created_at=conversation.created_at,
                )
            )

    def is_owned_by(self, conversation_id: UUID, customer_id: UUID) -> bool:
        with self._session_factory() as session:
            return (
                session.scalar(
                    select(ConversationRecord.id).where(
                        ConversationRecord.id == conversation_id,
                        ConversationRecord.customer_id == customer_id,
                    )
                )
                is not None
            )

    def get_history(
        self,
        conversation_id: UUID,
        customer_id: UUID,
    ) -> ConversationHistory | None:
        with self._session_factory() as session:
            conversation = session.scalar(
                select(ConversationRecord).where(
                    ConversationRecord.id == conversation_id,
                    ConversationRecord.customer_id == customer_id,
                )
            )
            if conversation is None:
                return None

            records = tuple(
                session.scalars(
                    select(MessageRecord)
                    .where(MessageRecord.conversation_id == conversation_id)
                    .order_by(MessageRecord.created_at, MessageRecord.id)
                )
            )
            evidence_by_message: dict[UUID, list[EvidenceReference]] = {
                record.id: [] for record in records
            }
            message_ids = tuple(evidence_by_message)
            if message_ids:
                for plan_row in session.scalars(
                    select(MessagePlanEvidenceRecord).where(
                        MessagePlanEvidenceRecord.message_id.in_(message_ids)
                    )
                ):
                    evidence_by_message[plan_row.message_id].append(
                        EvidenceReference(EvidenceType.PLAN_SNAPSHOT, plan_row.plan_snapshot_id)
                    )
                for bill_row in session.scalars(
                    select(MessageBillEvidenceRecord).where(
                        MessageBillEvidenceRecord.message_id.in_(message_ids)
                    )
                ):
                    evidence_by_message[bill_row.message_id].append(
                        EvidenceReference(EvidenceType.BILL_SNAPSHOT, bill_row.bill_snapshot_id)
                    )
                for charge_row in session.scalars(
                    select(MessageChargeEvidenceRecord).where(
                        MessageChargeEvidenceRecord.message_id.in_(message_ids)
                    )
                ):
                    evidence_by_message[charge_row.message_id].append(
                        EvidenceReference(
                            EvidenceType.CHARGE_SNAPSHOT,
                            charge_row.charge_snapshot_id,
                        )
                    )

            messages = tuple(
                Message(
                    id=record.id,
                    conversation_id=record.conversation_id,
                    role=MessageRole(record.role),
                    content=record.content,
                    created_at=record.created_at,
                    answer_status=(
                        AnswerStatus(record.answer_status)
                        if record.answer_status is not None
                        else None
                    ),
                    uncertain=record.uncertain,
                    evidence=tuple(evidence_by_message[record.id]),
                )
                for record in records
            )
            return ConversationHistory(
                id=conversation.id,
                status=ConversationStatus(conversation.status),
                created_at=conversation.created_at,
                messages=messages,
            )


class SqlAlchemyMessageExchangeRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def add(self, exchange: MessageExchange) -> None:
        with self._session_factory.begin() as session:
            if exchange.plan_snapshot is not None:
                snapshot = exchange.plan_snapshot
                session.add(
                    PlanSnapshotRecord(
                        id=snapshot.id,
                        customer_id=snapshot.customer_id,
                        plan_code=snapshot.plan_code,
                        plan_name=snapshot.plan_name,
                        data_allowance_gb=snapshot.data_allowance_gb,
                        recurring_charge=snapshot.recurring_charge,
                        currency=snapshot.currency,
                        effective_from=snapshot.effective_from,
                        retrieved_at=snapshot.retrieved_at,
                        source_version=snapshot.source_version,
                        availability=snapshot.availability.value,
                    )
                )

            if exchange.bill_snapshot is not None:
                bill = exchange.bill_snapshot
                session.add(
                    BillSnapshotRecord(
                        id=bill.id,
                        customer_id=bill.customer_id,
                        period_start=bill.period_start,
                        period_end=bill.period_end,
                        total=bill.total,
                        currency=bill.currency,
                        retrieved_at=bill.retrieved_at,
                        source_version=bill.source_version,
                        availability=bill.availability.value,
                    )
                )
                session.flush()
                session.add_all(
                    [
                        BillLineItemRecord(
                            id=item.id,
                            bill_snapshot_id=bill.id,
                            code=item.code,
                            description=item.description,
                            amount=item.amount,
                            position=position,
                        )
                        for position, item in enumerate(bill.line_items)
                    ]
                )

            if exchange.charge_snapshot is not None:
                charge = exchange.charge_snapshot
                session.add(
                    ChargeEvidenceSnapshotRecord(
                        id=charge.id,
                        customer_id=charge.customer_id,
                        line_item_code=charge.line_item_code,
                        description=charge.description,
                        amount=charge.amount,
                        currency=charge.currency,
                        occurred_on=charge.occurred_on,
                        location=charge.location,
                        service_name=charge.service_name,
                        trigger=charge.trigger,
                        state=charge.state.value,
                        retrieved_at=charge.retrieved_at,
                        source_version=charge.source_version,
                    )
                )

            for message in (exchange.user_message, exchange.assistant_message):
                session.add(
                    MessageRecord(
                        id=message.id,
                        conversation_id=message.conversation_id,
                        role=message.role.value,
                        content=message.content,
                        created_at=message.created_at,
                        answer_status=(
                            message.answer_status.value
                            if message.answer_status is not None
                            else None
                        ),
                        uncertain=message.uncertain,
                    )
                )

            session.flush()
            for evidence in exchange.assistant_message.evidence:
                if evidence.type is EvidenceType.PLAN_SNAPSHOT:
                    session.add(
                        MessagePlanEvidenceRecord(
                            message_id=exchange.assistant_message.id,
                            plan_snapshot_id=evidence.id,
                        )
                    )
                elif evidence.type is EvidenceType.BILL_SNAPSHOT:
                    session.add(
                        MessageBillEvidenceRecord(
                            message_id=exchange.assistant_message.id,
                            bill_snapshot_id=evidence.id,
                        )
                    )
                elif evidence.type is EvidenceType.CHARGE_SNAPSHOT:
                    session.add(
                        MessageChargeEvidenceRecord(
                            message_id=exchange.assistant_message.id,
                            charge_snapshot_id=evidence.id,
                        )
                    )


class SqlAlchemyEscalationRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def add_requested(self, escalation: Escalation) -> None:
        try:
            with self._session_factory.begin() as session:
                session.add(
                    EscalationRecord(
                        id=escalation.id,
                        customer_id=escalation.customer_id,
                        conversation_id=escalation.conversation_id,
                        reason=escalation.reason,
                        status=escalation.status.value,
                        created_at=escalation.created_at,
                        updated_at=escalation.updated_at,
                        next_step=escalation.next_step,
                        handoff_context=_handoff_context_to_json(escalation.handoff_context),
                    )
                )
        except IntegrityError as error:
            raise ActiveEscalationExistsError from error

    def update(self, escalation: Escalation) -> None:
        with self._session_factory.begin() as session:
            record = session.get(EscalationRecord, escalation.id)
            if record is None:
                raise RuntimeError("Escalation disappeared before status update.")
            record.status = escalation.status.value
            record.updated_at = escalation.updated_at
            record.next_step = escalation.next_step

    def get_owned(self, escalation_id: UUID, customer_id: UUID) -> Escalation | None:
        with self._session_factory() as session:
            record = session.scalar(
                select(EscalationRecord).where(
                    EscalationRecord.id == escalation_id,
                    EscalationRecord.customer_id == customer_id,
                )
            )
            if record is None:
                return None
            return Escalation(
                id=record.id,
                customer_id=record.customer_id,
                conversation_id=record.conversation_id,
                reason=record.reason,
                status=EscalationStatus(record.status),
                created_at=record.created_at.astimezone(UTC),
                updated_at=record.updated_at.astimezone(UTC),
                next_step=record.next_step,
                handoff_context=_handoff_context_from_json(record.handoff_context),
            )
