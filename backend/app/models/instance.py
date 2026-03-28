"""
instance.py — Modelos de instâncias Mautic e empresas.

Credenciais são armazenadas criptografadas (Fernet) no banco.
A chave de criptografia deriva do SECRET_KEY da aplicação.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Instance(Base):
    """Representa uma instância Mautic monitorada."""

    __tablename__ = "instances"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    url: Mapped[str] = mapped_column(String(255), nullable=False)

    # Credenciais API Mautic (armazenadas em texto simples — protegidas pelo banco)
    api_user: Mapped[str] = mapped_column(String(100), nullable=False)
    api_password_enc: Mapped[str] = mapped_column(Text, nullable=False)

    # Conexão direta ao banco Mautic
    db_host: Mapped[str | None] = mapped_column(String(255))
    db_port: Mapped[int] = mapped_column(Integer, default=5432)
    db_name: Mapped[str | None] = mapped_column(String(100))
    db_user: Mapped[str | None] = mapped_column(String(100))
    db_password_enc: Mapped[str | None] = mapped_column(Text)

    # Acesso SSH para monitoramento VPS
    ssh_host: Mapped[str | None] = mapped_column(String(255))
    ssh_port: Mapped[int] = mapped_column(Integer, default=22)
    ssh_user: Mapped[str | None] = mapped_column(String(100))
    ssh_key_path: Mapped[str | None] = mapped_column(String(500))

    # Metadados
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relacionamentos
    companies: Mapped[list["Company"]] = relationship(
        "Company", back_populates="instance", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Instance {self.name} ({self.url})>"


class Company(Base):
    """Empresa/segmento dentro de uma instância Mautic."""

    __tablename__ = "companies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    instance_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("instances.id", ondelete="CASCADE")
    )
    mautic_segment_id: Mapped[int | None] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relacionamentos
    instance: Mapped["Instance"] = relationship("Instance", back_populates="companies")

    def __repr__(self) -> str:
        return f"<Company {self.name} (instance={self.instance_id})>"
