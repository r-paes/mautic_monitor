"""
routers/gateways.py — Gerenciamento de credenciais dos gateways de envio.

GET  /gateways/config        — retorna quais chaves estão configuradas (sem valores sensíveis)
PATCH /gateways/config       — salva/atualiza credenciais (admin only)
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.gateway_config import GatewayConfig
from app.routers.auth import get_current_user
from app.models.users import User
from app.utils.crypto import encrypt_secret

router = APIRouter(prefix="/gateways", tags=["gateways"])

# ─── Chaves gerenciadas ────────────────────────────────────────────────────────
# Define quais chaves cada gateway expõe na interface.
# label: exibido no frontend  |  sensitive: mascara o valor na resposta GET

GATEWAY_KEYS: dict[str, dict] = {
    # Sendpost
    "sendpost_api_key": {
        "gateway": "sendpost",
        "label": "API Key",
        "sensitive": True,
    },
    "sendpost_alert_from_email": {
        "gateway": "sendpost",
        "label": "E-mail remetente",
        "sensitive": False,
    },
    # Avant SMS
    "avant_sms_token": {
        "gateway": "avant",
        "label": "Token Alpha",
        "sensitive": True,
    },
    "avant_sms_api_base_url": {
        "gateway": "avant",
        "label": "URL da API",
        "sensitive": False,
    },
}


# ─── Schemas ──────────────────────────────────────────────────────────────────

class GatewayConfigField(BaseModel):
    key: str
    label: str
    gateway: str
    sensitive: bool
    configured: bool       # True se há valor salvo no banco
    value: Optional[str]   # None para campos sensíveis; valor real para não-sensíveis


class GatewayConfigOut(BaseModel):
    fields: list[GatewayConfigField]


class GatewayConfigPatch(BaseModel):
    # Dicionário chave → valor; apenas as chaves enviadas são atualizadas
    values: dict[str, str]


# ─── Helpers ──────────────────────────────────────────────────────────────────

async def _get_all_configs(db: AsyncSession) -> dict[str, GatewayConfig]:
    result = await db.execute(select(GatewayConfig))
    return {row.key: row for row in result.scalars().all()}


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/config", response_model=GatewayConfigOut)
async def get_gateway_config(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """
    Retorna o estado das configurações de gateway.
    Campos sensíveis: apenas indica se está configurado (não retorna o valor).
    Campos não-sensíveis: retorna o valor decriptado.
    """
    from app.utils.crypto import decrypt_secret

    db_configs = await _get_all_configs(db)
    fields: list[GatewayConfigField] = []

    for key, meta in GATEWAY_KEYS.items():
        db_entry = db_configs.get(key)
        configured = db_entry is not None

        if meta["sensitive"]:
            value = None
        else:
            value = decrypt_secret(db_entry.value_enc) if db_entry else None

        fields.append(
            GatewayConfigField(
                key=key,
                label=meta["label"],
                gateway=meta["gateway"],
                sensitive=meta["sensitive"],
                configured=configured,
                value=value,
            )
        )

    return GatewayConfigOut(fields=fields)


@router.patch("/config", status_code=status.HTTP_204_NO_CONTENT)
async def update_gateway_config(
    data: GatewayConfigPatch,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Salva ou atualiza credenciais de gateway.
    Apenas chaves definidas em GATEWAY_KEYS são aceitas.
    Valores vazios são ignorados (não removem a configuração existente).
    """
    if current_user.role not in ("admin",):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão")

    db_configs = await _get_all_configs(db)
    now = datetime.now(timezone.utc)

    for key, value in data.values.items():
        if key not in GATEWAY_KEYS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Chave desconhecida: {key}",
            )
        if not value:
            continue  # ignora valor vazio

        encrypted = encrypt_secret(value)

        if key in db_configs:
            db_configs[key].value_enc = encrypted
            db_configs[key].updated_at = now
        else:
            db.add(GatewayConfig(key=key, value_enc=encrypted, updated_at=now))

    await db.commit()
