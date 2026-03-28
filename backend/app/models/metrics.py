"""
metrics.py — Métricas de saúde Mautic e gateways (TimescaleDB hypertables).
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class HealthMetric(Base):
    """
    Snapshots periódicos de saúde de cada instância Mautic.
    TimescaleDB hypertable particionada por 'time'.
    """

    __tablename__ = "health_metrics"
    __table_args__ = (
        Index("ix_health_metrics_time_instance", "time", "instance_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True, server_default=func.now()
    )
    instance_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("instances.id", ondelete="CASCADE"), nullable=False
    )

    # Dados coletados via API Mautic
    new_contacts: Mapped[int | None] = mapped_column(Integer)         # últimas 24h
    active_campaigns: Mapped[int | None] = mapped_column(Integer)

    # Dados coletados via banco Mautic (direto)
    emails_queued: Mapped[int | None] = mapped_column(Integer)
    emails_sent_mautic: Mapped[int | None] = mapped_column(Integer)   # último período
    sms_sent_mautic: Mapped[int | None] = mapped_column(Integer)

    # Performance da instância
    api_response_ms: Mapped[int | None] = mapped_column(Integer)
    db_response_ms: Mapped[int | None] = mapped_column(Integer)

    # Status geral: ok | degraded | down
    status: Mapped[str] = mapped_column(String(20), default="ok")


class GatewayMetric(Base):
    """
    Métricas coletadas diretamente dos gateways de envio.
    TimescaleDB hypertable — base para Delta Alerts.
    """

    __tablename__ = "gateway_metrics"
    __table_args__ = (
        Index("ix_gateway_metrics_time_type", "time", "gateway_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True, server_default=func.now()
    )

    # sendpost | avant_sms
    gateway_type: Mapped[str] = mapped_column(String(30), nullable=False)

    # Métricas de email (Sendpost)
    emails_sent: Mapped[int | None] = mapped_column(Integer)
    emails_delivered: Mapped[int | None] = mapped_column(Integer)
    emails_bounced: Mapped[int | None] = mapped_column(Integer)
    emails_spam: Mapped[int | None] = mapped_column(Integer)
    emails_unsubscribed: Mapped[int | None] = mapped_column(Integer)
    open_rate: Mapped[float | None] = mapped_column(Float)
    click_rate: Mapped[float | None] = mapped_column(Float)

    # Métricas de SMS (Avant)
    sms_sent: Mapped[int | None] = mapped_column(Integer)
    sms_delivered: Mapped[int | None] = mapped_column(Integer)
    sms_failed: Mapped[int | None] = mapped_column(Integer)

    # Saldo da conta
    balance_credits: Mapped[float | None] = mapped_column(Float)
