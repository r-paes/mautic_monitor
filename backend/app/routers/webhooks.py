"""
routers/webhooks.py — Webhooks de sistemas externos.

POST /webhooks/avant — recebe callbacks DLR (delivery receipts) da Avant SMS.
"""

import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.avant import AvantSmsLog

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/avant", status_code=status.HTTP_200_OK)
async def avant_dlr_webhook(request: Request):
    """
    Recebe callbacks DLR (Delivery Receipt) da Avant SMS.

    Campos esperados no payload:
        - id: identificador único da mensagem Avant
        - costCenterCode: código do centro de custo (identifica o cliente)
        - recipient: número destinatário
        - status: DELIVRD | UNDELIV | EXPIRED | UNKNOWN | REJECTD
        - dateTime: timestamp do evento (ISO 8601)
        - type: Answer | Reply (opcional)
        - errorCode: código de erro (opcional)

    O webhook NÃO requer autenticação JWT — é chamado diretamente pela Avant.
    """
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": "Payload JSON inválido"},
        )

    # Aceita payload único ou lista de callbacks
    callbacks = body if isinstance(body, list) else [body]

    async with AsyncSessionLocal() as db:
        processed = 0

        for cb in callbacks:
            avant_id = cb.get("id")
            if not avant_id:
                logger.warning("Webhook Avant: callback sem campo 'id', ignorado")
                continue

            try:
                # Tenta localizar registro existente (upsert por avant_message_id)
                result = await db.execute(
                    select(AvantSmsLog).where(
                        AvantSmsLog.avant_message_id == str(avant_id)
                    )
                )
                existing = result.scalar_one_or_none()

                cb_status = cb.get("status", "UNKNOWN")
                cb_datetime = _parse_datetime(cb.get("dateTime"))
                raw = json.dumps(cb, ensure_ascii=False)[:2000]

                if existing:
                    existing.status = cb_status
                    existing.error_code = cb.get("errorCode")
                    existing.raw_payload = raw
                    if cb_status == "DELIVRD" and cb_datetime:
                        existing.delivered_at = cb_datetime
                else:
                    log_entry = AvantSmsLog(
                        avant_message_id=str(avant_id),
                        cost_center_code=cb.get("costCenterCode"),
                        recipient=cb.get("recipient"),
                        status=cb_status,
                        error_code=cb.get("errorCode"),
                        sent_at=cb_datetime or datetime.now(tz=timezone.utc),
                        delivered_at=cb_datetime if cb_status == "DELIVRD" else None,
                        raw_payload=raw,
                    )
                    db.add(log_entry)

                processed += 1

            except Exception as e:
                logger.error("Webhook Avant: erro ao processar callback id=%s: %s", avant_id, e)

        await db.commit()

    logger.info("Webhook Avant: %d callback(s) processado(s)", processed)
    return {"processed": processed}


def _parse_datetime(value: str | None) -> datetime | None:
    """Tenta parsear datetime ISO 8601 do callback Avant."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None
