"""
routers/gateways.py — Gerenciamento de credenciais dos gateways de envio.

GET   /gateways/config              — retorna quais chaves estão configuradas (sem valores sensíveis)
PATCH /gateways/config              — salva/atualiza credenciais (admin only)
POST  /gateways/collect             — força coleta imediata de métricas (admin only)
"""

import logging
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

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/gateways", tags=["gateways"])

# ─── Chaves gerenciadas ────────────────────────────────────────────────────────
# Define quais chaves cada gateway expõe na interface.
# label: exibido no frontend  |  sensitive: mascara o valor na resposta GET

GATEWAY_KEYS: dict[str, dict] = {
    # Sendpost
    "sendpost_api_key": {
        "gateway": "sendpost",
        "label": "Account API Key (coleta de stats)",
        "sensitive": True,
    },
    "sendpost_subaccount_api_key": {
        "gateway": "sendpost",
        "label": "SubAccount API Key (envio de alertas)",
        "sensitive": True,
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


# ─── Coleta Manual ───────────────────────────────────────────────────────────

@router.post("/collect")
async def collect_gateways_now(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Força coleta imediata de métricas dos gateways.
    Útil para testar credenciais e ver dados na tab Email/SMS.
    Admin only.
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão")

    from app.collectors.sendpost import SendpostCollector
    from app.collectors.avant_sms import AvantSMSCollector
    from app.models.metrics import GatewayMetric
    from app.utils.gateway_settings import get_gateway_setting
    from app.config import settings

    now = datetime.now(timezone.utc)
    results = {}

    # Sendpost — coleta por sub-account
    try:
        sendpost_key = await get_gateway_setting(db, "sendpost_api_key", settings.sendpost_api_key)
        sendpost = SendpostCollector(account_api_key=sendpost_key)
        subaccount_results = await sendpost.collect()
        for data in subaccount_results:
            sub_id = data.pop("subaccount_id", None)
            sub_name = data.pop("subaccount_name", None)
            metric = GatewayMetric(
                time=now,
                gateway_type="sendpost",
                subaccount_id=sub_id,
                subaccount_name=sub_name,
                **data,
            )
            db.add(metric)
        results["sendpost"] = {
            "status": "ok",
            "subaccounts": len(subaccount_results),
            "data": subaccount_results,
        }
    except Exception as e:
        logger.error("Coleta manual Sendpost falhou: %s", e)
        results["sendpost"] = {"status": "error", "detail": str(e)}

    # Avant SMS
    try:
        avant_token = await get_gateway_setting(db, "avant_sms_token", settings.avant_sms_token)
        avant_base_url = await get_gateway_setting(
            db, "avant_sms_api_base_url", settings.avant_sms_api_base_url
        )
        avant = AvantSMSCollector(token=avant_token, base_url=avant_base_url)
        data = await avant.collect(db_session=db)
        metric = GatewayMetric(time=now, gateway_type="avant_sms", **data)
        db.add(metric)
        results["avant_sms"] = {"status": "ok", "data": data}
    except Exception as e:
        logger.error("Coleta manual Avant SMS falhou: %s", e)
        results["avant_sms"] = {"status": "error", "detail": str(e)}

    await db.commit()
    return results


# ─── Stats On-Demand (Sendpost) ──────────────────────────────────────────────

@router.get("/sendpost/stats")
async def get_sendpost_stats(
    start: str,
    end: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """
    Consulta a API Sendpost on-demand para o período selecionado.
    Retorna stats por sub-account diretamente da Sendpost (não do banco local).
    """
    from app.collectors.sendpost import SendpostCollector
    from app.utils.gateway_settings import get_gateway_setting
    from app.config import settings

    sendpost_key = await get_gateway_setting(db, "sendpost_api_key", settings.sendpost_api_key)
    if not sendpost_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account API Key do Sendpost não configurada",
        )

    collector = SendpostCollector(account_api_key=sendpost_key)

    # Lista sub-accounts
    subaccounts = await collector.list_subaccounts()

    # Parseia datas — frontend envia ISO com Z
    from_date = start.replace("Z", "+00:00").split("T")[0]  # YYYY-MM-DD
    to_date = end.replace("Z", "+00:00").split("T")[0]

    results = []
    for sub in subaccounts:
        sub_id = sub.get("id")
        sub_name = sub.get("name", f"Sub-{sub_id}")

        raw = await collector.get_subaccount_stats_by_date(sub_id, from_date, to_date)
        if raw is None:
            stats = collector._empty_stats()
        else:
            stats = collector._parse_stats(raw)

        results.append({
            "subaccount_id": sub_id,
            "subaccount_name": sub_name,
            **stats,
        })

    # Totais consolidados
    totals = collector._empty_stats()
    for r in results:
        for key in totals:
            if r.get(key) is not None and totals[key] is not None:
                totals[key] = (totals[key] or 0) + r[key]
            elif r.get(key) is not None:
                totals[key] = r[key]

    return {
        "period": {"start": from_date, "end": to_date},
        "subaccounts": results,
        "totals": totals,
    }
