"""
gateway_settings.py — Acesso às credenciais de gateway com fallback para settings.

Uso nos coletores:
    value = await get_gateway_setting(db, "sendpost_api_key", settings.sendpost_api_key)

Prioridade: banco de dados (GatewayConfig) > settings (.env)
"""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gateway_config import GatewayConfig
from app.utils.crypto import decrypt_secret

logger = logging.getLogger(__name__)


async def get_gateway_setting(
    db: AsyncSession,
    key: str,
    fallback: str,
) -> str:
    """
    Retorna o valor da configuração de gateway para a chave fornecida.
    - Se existe entrada no banco: retorna valor decriptado
    - Caso contrário: retorna fallback (valor de settings/.env)
    """
    result = await db.execute(select(GatewayConfig).where(GatewayConfig.key == key))
    entry = result.scalars().first()

    if entry:
        value = decrypt_secret(entry.value_enc)
        if value:
            return value
        logger.warning("GatewayConfig '%s' encontrada no banco mas falhou ao decriptar — usando fallback.", key)

    return fallback
