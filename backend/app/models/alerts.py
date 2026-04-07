"""
alerts.py — Modelo de alertas gerados pelo sistema.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AlertSeverity(str, enum.Enum):
    info = "info"
    warning = "warning"
    critical = "critical"


class NotificationChannel(str, enum.Enum):
    email = "email"
    sms = "sms"
    both = "both"


class Alert(Base):
    """Alerta gerado pelo motor de regras."""

    __tablename__ = "alerts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    instance_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("instances.id", ondelete="SET NULL"), nullable=True
    )

    severity: Mapped[str] = mapped_column(
        Enum(AlertSeverity, name="alert_severity", create_constraint=True, native_enum=True),
        nullable=False, index=True,
    )

    # Tipo do alerta — string livre para permitir novos tipos sem migration
    type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    message: Mapped[str] = mapped_column(Text, nullable=False)

    notified_via: Mapped[str | None] = mapped_column(
        Enum(NotificationChannel, name="notification_channel", create_constraint=True, native_enum=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    acked_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    def __repr__(self) -> str:
        return f"<Alert [{self.severity}] {self.type}: {self.message[:50]}>"
