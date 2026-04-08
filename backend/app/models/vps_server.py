"""
vps_server.py — Modelo de servidores VPS (entidade independente).

Cada VPS pode hospedar múltiplas instâncias Mautic.
Monitoramento via API do EasyPanel (tRPC).
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class VpsServer(Base):
    """Servidor VPS monitorado via EasyPanel API."""

    __tablename__ = "vps_servers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    # EasyPanel connection
    easypanel_url: Mapped[str] = mapped_column(String(255), nullable=False)
    api_key_enc: Mapped[str | None] = mapped_column(Text)

    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relacionamento reverso — instâncias hospedadas nesta VPS
    instances: Mapped[list["Instance"]] = relationship(
        "Instance", back_populates="vps", lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<VpsServer {self.name} ({self.easypanel_url})>"
