"""
vps_metrics.py — Métricas de recursos das VPS + status de containers + logs de serviços.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class VpsMetric(Base):
    """
    Métricas de recursos do sistema coletadas via SSH.
    TimescaleDB hypertable particionada por 'time'.
    """

    __tablename__ = "vps_metrics"
    __table_args__ = (
        Index("ix_vps_metrics_time_instance", "time", "instance_id"),
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

    # CPU
    cpu_percent: Mapped[float | None] = mapped_column(Float)

    # Memória
    memory_percent: Mapped[float | None] = mapped_column(Float)
    memory_used_mb: Mapped[int | None] = mapped_column(Integer)
    memory_total_mb: Mapped[int | None] = mapped_column(Integer)

    # Disco
    disk_percent: Mapped[float | None] = mapped_column(Float)
    disk_used_gb: Mapped[float | None] = mapped_column(Float)
    disk_total_gb: Mapped[float | None] = mapped_column(Float)

    # Load average do sistema
    load_avg_1m: Mapped[float | None] = mapped_column(Float)
    load_avg_5m: Mapped[float | None] = mapped_column(Float)
    load_avg_15m: Mapped[float | None] = mapped_column(Float)


class ServiceStatus(Base):
    """
    Status de containers Docker em cada VPS.
    TimescaleDB hypertable.
    """

    __tablename__ = "service_status"
    __table_args__ = (
        Index("ix_service_status_time_instance", "time", "instance_id"),
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
    container_name: Mapped[str] = mapped_column(String(200), nullable=False)

    # running | stopped | restarting | error | unknown
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    uptime_seconds: Mapped[int | None] = mapped_column(Integer)
    restart_count: Mapped[int | None] = mapped_column(Integer)
    image: Mapped[str | None] = mapped_column(String(300))


class ServiceLog(Base):
    """
    Logs relevantes de serviços coletados das VPS.
    Armazena apenas entradas com padrões de erro/anomalia detectados.
    """

    __tablename__ = "service_logs"
    __table_args__ = (
        Index("ix_service_logs_instance_captured", "instance_id", "captured_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    instance_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("instances.id", ondelete="CASCADE"), nullable=False
    )
    container_name: Mapped[str] = mapped_column(String(200), nullable=False)

    # info | warning | error | critical
    log_level: Mapped[str] = mapped_column(String(20), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    pattern_matched: Mapped[str | None] = mapped_column(String(100))  # qual regra detectou
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
