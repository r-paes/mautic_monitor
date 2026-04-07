"""
gateway_config.py — Configurações de credenciais dos gateways (Sendpost, Avant SMS).

Armazena pares chave/valor com o valor criptografado via Fernet.
Permite que as credenciais sejam editadas pela interface sem alterar variáveis de ambiente.
"""

from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class GatewayConfig(Base):
    """
    Configuração de gateway — chave única por entrada.
    O valor é armazenado criptografado (Fernet) mesmo para campos não-sensíveis,
    garantindo uniformidade no acesso.
    """

    __tablename__ = "gateway_configs"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value_enc: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<GatewayConfig {self.key}>"
