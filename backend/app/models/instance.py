"""
instance.py — Modelos de instâncias Mautic, empresas e credenciais de conexão.

Credenciais são armazenadas criptografadas (Fernet) em tabelas separadas,
cada uma com FK 1:1 para a instância, garantindo modularidade.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Instance(Base):
    """Representa uma instância Mautic monitorada (metadados apenas)."""

    __tablename__ = "instances"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    url: Mapped[str] = mapped_column(String(255), nullable=False)

    # Metadados
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relacionamentos — credenciais em tabelas dedicadas (1:1, eager load)
    api_creds: Mapped["InstanceApiCredential"] = relationship(
        "InstanceApiCredential", back_populates="instance",
        uselist=False, cascade="all, delete-orphan", lazy="joined",
    )
    db_creds: Mapped["InstanceDbCredential"] = relationship(
        "InstanceDbCredential", back_populates="instance",
        uselist=False, cascade="all, delete-orphan", lazy="joined",
    )
    ssh_creds: Mapped["InstanceSshCredential"] = relationship(
        "InstanceSshCredential", back_populates="instance",
        uselist=False, cascade="all, delete-orphan", lazy="joined",
    )
    companies: Mapped[list["Company"]] = relationship(
        "Company", back_populates="instance", cascade="all, delete-orphan"
    )

    # ── Propriedades de conveniência (compatibilidade com código existente) ──

    @property
    def api_user(self) -> str | None:
        return self.api_creds.username if self.api_creds else None

    @property
    def api_password_enc(self) -> str | None:
        return self.api_creds.password_enc if self.api_creds else None

    @property
    def db_host(self) -> str | None:
        return self.db_creds.host if self.db_creds else None

    @property
    def db_port(self) -> int:
        return self.db_creds.port if self.db_creds else 3306

    @property
    def db_name(self) -> str | None:
        return self.db_creds.dbname if self.db_creds else None

    @property
    def db_user(self) -> str | None:
        return self.db_creds.username if self.db_creds else None

    @property
    def db_password_enc(self) -> str | None:
        return self.db_creds.password_enc if self.db_creds else None

    @property
    def ssh_host(self) -> str | None:
        return self.ssh_creds.host if self.ssh_creds else None

    @property
    def ssh_port(self) -> int:
        return self.ssh_creds.port if self.ssh_creds else 22

    @property
    def ssh_user(self) -> str | None:
        return self.ssh_creds.username if self.ssh_creds else None

    @property
    def ssh_key_path(self) -> str | None:
        return self.ssh_creds.key_path if self.ssh_creds else None

    @property
    def ssh_private_key_enc(self) -> str | None:
        return self.ssh_creds.private_key_enc if self.ssh_creds else None

    @property
    def ssh_public_key(self) -> str | None:
        return self.ssh_creds.public_key if self.ssh_creds else None

    def __repr__(self) -> str:
        return f"<Instance {self.name} ({self.url})>"


class InstanceApiCredential(Base):
    """Credenciais de API REST para uma instância Mautic."""

    __tablename__ = "instance_api_credentials"

    instance_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("instances.id", ondelete="CASCADE"), primary_key=True
    )
    username: Mapped[str] = mapped_column(String(100), nullable=False)
    password_enc: Mapped[str] = mapped_column(Text, nullable=False)

    instance: Mapped["Instance"] = relationship("Instance", back_populates="api_creds")


class InstanceDbCredential(Base):
    """Credenciais de banco MySQL para uma instância Mautic."""

    __tablename__ = "instance_db_credentials"

    instance_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("instances.id", ondelete="CASCADE"), primary_key=True
    )
    host: Mapped[str] = mapped_column(String(255), nullable=False)
    port: Mapped[int] = mapped_column(Integer, default=3306)
    dbname: Mapped[str] = mapped_column(String(100), nullable=False)
    username: Mapped[str] = mapped_column(String(100), nullable=False)
    password_enc: Mapped[str] = mapped_column(Text, nullable=False)

    instance: Mapped["Instance"] = relationship("Instance", back_populates="db_creds")


class InstanceSshCredential(Base):
    """Credenciais SSH para monitoramento VPS de uma instância."""

    __tablename__ = "instance_ssh_credentials"

    instance_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("instances.id", ondelete="CASCADE"), primary_key=True
    )
    host: Mapped[str] = mapped_column(String(255), nullable=False)
    port: Mapped[int] = mapped_column(Integer, default=22)
    username: Mapped[str] = mapped_column(String(100), default="root")
    key_path: Mapped[str | None] = mapped_column(String(500))  # legado
    private_key_enc: Mapped[str | None] = mapped_column(Text)  # RSA Fernet
    public_key: Mapped[str | None] = mapped_column(Text)       # RSA público

    instance: Mapped["Instance"] = relationship("Instance", back_populates="ssh_creds")


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

    instance: Mapped["Instance"] = relationship("Instance", back_populates="companies")

    def __repr__(self) -> str:
        return f"<Company {self.name} (instance={self.instance_id})>"
