"""
reports.py — Modelos para o módulo de relatórios Mautic.

ReportConfig  — configuração de envio de relatório por empresa/instância.
ReportHistory — histórico de execuções (TimescaleDB hypertable em 'generated_at').
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ReportTrigger(str, enum.Enum):
    scheduled = "scheduled"
    manual = "manual"


class ReportStatus(str, enum.Enum):
    pending = "pending"
    generating = "generating"
    success = "success"
    error = "error"


class ReportConfig(Base):
    """
    Configuração de relatório para uma empresa dentro de uma instância Mautic.
    Uma instância pode ter múltiplos ReportConfigs (uma empresa por config).
    """

    __tablename__ = "report_configs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    instance_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("instances.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Identificação da empresa no Mautic MySQL
    company_name: Mapped[str] = mapped_column(String(200), nullable=False)
    mautic_company_id: Mapped[int | None] = mapped_column(Integer)

    # Destinatários do relatório
    report_email: Mapped[str] = mapped_column(String(255), nullable=False)
    report_phone: Mapped[str | None] = mapped_column(String(20))  # E.164: +5511999999999

    # Canais de envio
    send_email: Mapped[bool] = mapped_column(Boolean, default=True)
    send_sms: Mapped[bool] = mapped_column(Boolean, default=False)

    # Controle
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relacionamentos
    instance: Mapped["Instance"] = relationship("Instance")  # type: ignore[name-defined]
    history: Mapped[list["ReportHistory"]] = relationship(
        "ReportHistory", back_populates="config", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<ReportConfig {self.company_name} (instance={self.instance_id})>"


class ReportHistory(Base):
    """
    Histórico de relatórios gerados.
    Configurada como TimescaleDB hypertable em 'generated_at' via migration.
    """

    __tablename__ = "report_history"
    __table_args__ = (
        Index("ix_report_history_generated_at", "generated_at"),
        Index("ix_report_history_config_instance", "report_config_id", "instance_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    report_config_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("report_configs.id", ondelete="CASCADE"),
        nullable=False,
    )
    instance_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("instances.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Período coberto pelo relatório
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Contexto de execução
    trigger: Mapped[str] = mapped_column(
        Enum(ReportTrigger, name="report_trigger", create_constraint=True, native_enum=True),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        Enum(ReportStatus, name="report_status", create_constraint=True, native_enum=True),
        nullable=False, default="pending",
    )

    # Arquivo gerado
    file_path: Mapped[str | None] = mapped_column(String(500))   # path relativo em /app/reports
    file_url: Mapped[str | None] = mapped_column(String(500))    # URL pública para acesso

    # Snapshot dos dados utilizados (para auditoria)
    email_stats_json: Mapped[dict | None] = mapped_column(JSONB)
    sms_stats_json: Mapped[dict | None] = mapped_column(JSONB)

    # Resultado do envio
    sent_email: Mapped[bool] = mapped_column(Boolean, default=False)
    sent_sms: Mapped[bool] = mapped_column(Boolean, default=False)

    # Detalhes de erro (se status == "error")
    error_message: Mapped[str | None] = mapped_column(Text)

    # Relacionamentos
    config: Mapped["ReportConfig"] = relationship("ReportConfig", back_populates="history")

    def __repr__(self) -> str:
        return f"<ReportHistory [{self.status}] {self.generated_at:%Y-%m-%d %H:%M}>"
