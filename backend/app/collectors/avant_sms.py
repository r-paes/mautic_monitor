"""
avant_sms.py — Coleta de estatísticas via Avant SMS API.

Auth: Token Bearer
Docs: https://suporte.solucoesdigitais.dev/smsApi

Coleta: volume enviado, status de entrega (DELIVRD/UNDELIV), saldo de créditos.
"""

import logging

import httpx

from app.config import settings
from app.utils.retry import with_retry

logger = logging.getLogger(__name__)

# Endpoints Avant SMS — centralizados aqui
AVANT_BALANCE_ENDPOINT = "/sms/balance"
AVANT_REPORT_ENDPOINT = "/sms/report"

# Status de entrega mapeados pela API Avant
AVANT_STATUS_DELIVERED = "DELIVRD"
AVANT_STATUS_UNDELIVERED = "UNDELIV"


class AvantSMSCollector:
    """Coleta estatísticas de SMS via Avant SMS API."""

    def __init__(self):
        self.base_url = settings.avant_sms_api_base_url.rstrip("/")
        self.headers = {
            "Authorization": f"Bearer {settings.avant_sms_token}",
            "Content-Type": "application/json",
        }
        self.timeout = settings.mautic_timeout_seconds

    @with_retry(exceptions=(httpx.HTTPError, httpx.TimeoutException))
    async def get_balance(self) -> float | None:
        """Retorna saldo de créditos SMS disponíveis."""
        try:
            async with httpx.AsyncClient(
                base_url=self.base_url,
                headers=self.headers,
                timeout=self.timeout,
            ) as client:
                resp = await client.get(AVANT_BALANCE_ENDPOINT)
                resp.raise_for_status()
                data = resp.json()
                # Ajuste o campo conforme retorno real da API
                return float(
                    data.get("balance")
                    or data.get("saldo")
                    or data.get("credits")
                    or 0
                )
        except Exception as e:
            logger.warning("Erro ao obter saldo Avant SMS: %s", e)
            return None

    @with_retry(exceptions=(httpx.HTTPError, httpx.TimeoutException))
    async def get_delivery_report(self) -> dict | None:
        """Retorna relatório de entregas do período recente."""
        try:
            async with httpx.AsyncClient(
                base_url=self.base_url,
                headers=self.headers,
                timeout=self.timeout,
            ) as client:
                resp = await client.get(AVANT_REPORT_ENDPOINT)
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            logger.warning("Erro ao obter relatório Avant SMS: %s", e)
            return None

    async def collect(self) -> dict:
        """Retorna snapshot consolidado de métricas SMS."""
        balance = await self.get_balance()
        report = await self.get_delivery_report()

        sms_sent = None
        sms_delivered = None
        sms_failed = None

        if report:
            # Adaptação ao formato real da API — ajuste os campos conforme necessário
            sms_sent = (
                report.get("total")
                or report.get("sent")
                or report.get("totalSent")
            )
            sms_delivered = (
                report.get(AVANT_STATUS_DELIVERED)
                or report.get("delivered")
                or report.get("totalDelivered")
            )
            sms_failed = (
                report.get(AVANT_STATUS_UNDELIVERED)
                or report.get("failed")
                or report.get("totalFailed")
            )

        return {
            "sms_sent": sms_sent,
            "sms_delivered": sms_delivered,
            "sms_failed": sms_failed,
            "balance_credits": balance,
        }
