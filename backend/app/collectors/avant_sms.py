"""
avant_sms.py — Coleta de estatísticas via Avant SMS API.

Auth: Authorization: alpha {TOKEN}
Docs: https://suporte.solucoesdigitais.dev/smsApi

Endpoints:
  - Envio:  POST https://channel.solucoesdigitais.dev/sms/message/send
  - Saldo:  GET  http://api-messaging.solucoesdigitais.cc/sms/balance/get

Coleta: saldo real via API + stats por costCenterCode do banco local (AvantSmsLog).
"""

import logging
from datetime import datetime, timezone

import httpx

from app.config import settings
from app.utils.retry import with_retry

logger = logging.getLogger(__name__)

# ─── Endpoints ────────────────────────────────────────────────────────────────

AVANT_SEND_URL = "https://channel.solucoesdigitais.dev/sms/message/send"
AVANT_BALANCE_URL = "http://api-messaging.solucoesdigitais.cc/sms/balance/get"

# Status de entrega retornados nos callbacks DLR
AVANT_STATUS_DELIVERED = "DELIVRD"
AVANT_STATUS_FAILED = {"UNDELIV", "EXPIRED", "REJECTD"}
AVANT_STATUS_UNKNOWN = "UNKNOWN"


class AvantSMSCollector:
    """Coleta estatísticas de SMS via Avant SMS API + banco local."""

    def __init__(
        self,
        token: str | None = None,
        base_url: str | None = None,
    ):
        self.token = token or settings.avant_sms_token
        # base_url mantido para compatibilidade — usado apenas no envio
        self.base_url = (base_url or settings.avant_sms_api_base_url).rstrip("/")
        self.headers = {
            "Authorization": f"alpha {self.token}",
            "Content-Type": "application/json",
        }
        self.timeout = settings.mautic_timeout_seconds

    @with_retry(exceptions=(httpx.HTTPError, httpx.TimeoutException))
    async def get_balance(self) -> int | None:
        """Retorna saldo de créditos SMS disponíveis (campo 'current')."""
        try:
            async with httpx.AsyncClient(
                headers=self.headers,
                timeout=self.timeout,
            ) as client:
                resp = await client.get(AVANT_BALANCE_URL)
                resp.raise_for_status()
                data = resp.json()
                return int(data.get("current", 0))
        except Exception as e:
            logger.warning("Erro ao obter saldo Avant SMS: %s", e)
            return None

    async def send_sms(
        self,
        recipient: str,
        message: str,
        cost_center_code: str | None = None,
    ) -> dict | None:
        """
        Envia um SMS via API Avant.

        Args:
            recipient: número destino (ex: "5511999999999")
            message: texto do SMS
            cost_center_code: código do centro de custo (identifica o cliente)

        Returns:
            dict com resposta da API ou None em caso de falha.
        """
        payload = {
            "recipient": recipient,
            "message": {"text": message},
        }
        if cost_center_code:
            payload["costCenterCode"] = cost_center_code

        try:
            async with httpx.AsyncClient(
                headers=self.headers,
                timeout=self.timeout,
            ) as client:
                resp = await client.post(AVANT_SEND_URL, json=payload)
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            logger.error("Erro ao enviar SMS Avant: %s", e)
            return None

    async def collect(self, db_session=None) -> dict:
        """
        Retorna snapshot consolidado de métricas SMS.

        Se db_session for fornecido, agrega stats do AvantSmsLog.
        Caso contrário, retorna apenas saldo.
        """
        balance = await self.get_balance()

        sms_sent = None
        sms_delivered = None
        sms_failed = None

        if db_session:
            try:
                stats = await self._get_stats_from_db(db_session)
                sms_sent = stats["sent"]
                sms_delivered = stats["delivered"]
                sms_failed = stats["failed"]
            except Exception as e:
                logger.warning("Erro ao agregar stats do AvantSmsLog: %s", e)

        return {
            "sms_sent": sms_sent,
            "sms_delivered": sms_delivered,
            "sms_failed": sms_failed,
            "balance_credits": balance,
        }

    async def _get_stats_from_db(self, db_session) -> dict:
        """Agrega totais de SMS das últimas 24h a partir do AvantSmsLog."""
        from sqlalchemy import func, select
        from app.models.avant import AvantSmsLog

        cutoff = datetime.now(tz=timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        result = await db_session.execute(
            select(
                func.count(AvantSmsLog.id).label("total"),
                func.count(AvantSmsLog.id).filter(
                    AvantSmsLog.status == AVANT_STATUS_DELIVERED
                ).label("delivered"),
                func.count(AvantSmsLog.id).filter(
                    AvantSmsLog.status.in_(AVANT_STATUS_FAILED)
                ).label("failed"),
            ).where(AvantSmsLog.sent_at >= cutoff)
        )
        row = result.one()
        return {
            "sent": row.total or 0,
            "delivered": row.delivered or 0,
            "failed": row.failed or 0,
        }

    async def get_stats_by_cost_center(self, db_session, since: datetime | None = None) -> list[dict]:
        """
        Retorna stats agrupadas por costCenterCode.
        Usado pelo frontend para exibir tabela por cliente.
        """
        from sqlalchemy import func, select, case
        from app.models.avant import AvantSmsLog, AvantCostCenter

        if since is None:
            since = datetime.now(tz=timezone.utc).replace(
                hour=0, minute=0, second=0, microsecond=0
            )

        result = await db_session.execute(
            select(
                AvantSmsLog.cost_center_code,
                func.count(AvantSmsLog.id).label("total"),
                func.count(case(
                    (AvantSmsLog.status == AVANT_STATUS_DELIVERED, 1),
                )).label("delivered"),
                func.count(case(
                    (AvantSmsLog.status.in_(AVANT_STATUS_FAILED), 1),
                )).label("failed"),
            )
            .where(AvantSmsLog.sent_at >= since)
            .group_by(AvantSmsLog.cost_center_code)
        )
        rows = result.all()

        # Busca nomes dos cost centers
        cc_result = await db_session.execute(select(AvantCostCenter))
        cc_map = {cc.code: cc.client_name for cc in cc_result.scalars().all()}

        return [
            {
                "cost_center_code": row.cost_center_code or "—",
                "client_name": cc_map.get(row.cost_center_code, "Não identificado"),
                "sms_sent": row.total,
                "sms_delivered": row.delivered,
                "sms_failed": row.failed,
            }
            for row in rows
        ]
