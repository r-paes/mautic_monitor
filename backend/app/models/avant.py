"""
avant.py — Modelos para integração Avant SMS: cost centers e logs de entrega.

AvantCostCenter: tabela de correlação costCenterCode → nome do cliente.
AvantSmsLog: log de eventos DLR recebidos via webhook.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AvantSmsStatus(str, enum.Enum):
    PENDING = "PENDING"
    DELIVRD = "DELIVRD"
    UNDELIV = "UNDELIV"
    EXPIRED = "EXPIRED"
    UNKNOWN = "UNKNOWN"
    REJECTD = "REJECTD"


class AvantCostCenter(Base):
    """
    Correlação entre costCenterCode (usado no envio/callback Avant)
    e o nome do cliente. Gerenciado via interface administrativa.
    """

    __tablename__ = "avant_cost_centers"

    code: Mapped[str] = mapped_column(String(100), primary_key=True)
    client_name: Mapped[str] = mapped_column(String(255), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class AvantSmsLog(Base):
    """
    Log de eventos SMS Avant — populado via webhook DLR (delivery receipts).
    Cada registro representa um SMS enviado/entregue/falhado.
    """

    __tablename__ = "avant_sms_logs"
    __table_args__ = (
        Index("ix_avant_sms_logs_sent_at", "sent_at"),
        Index("ix_avant_sms_logs_cost_center", "cost_center_code"),
        Index("ix_avant_sms_logs_avant_id", "avant_message_id", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    avant_message_id: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True
    )
    cost_center_code: Mapped[str | None] = mapped_column(
        String(100),
        ForeignKey("avant_cost_centers.code", ondelete="SET NULL"),
        nullable=True,
    )
    recipient: Mapped[str | None] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(
        Enum(AvantSmsStatus, name="avant_sms_status", create_constraint=True, native_enum=True),
        nullable=False, default="PENDING",
    )
    error_code: Mapped[str | None] = mapped_column(String(50))
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    raw_payload: Mapped[str | None] = mapped_column(String(2000))
