"""
sendpost.py — Coleta de estatísticas via Sendpost REST API.

Nota: O Mautic envia emails via SMTP para o Sendpost.
      Esta coleta usa a API REST do Sendpost para obter as estatísticas
      reais de entrega — base para os Delta Alerts.

Auth: Header X-SubAccount-ApiKey
Docs: https://docs.sendpost.io/api-reference/introduction
"""

import logging
from datetime import datetime, timedelta, timezone

import httpx

from app.config import settings
from app.utils.retry import with_retry

logger = logging.getLogger(__name__)

# Endpoints Sendpost — centralizados aqui, não espalhados no código
SENDPOST_STATS_ENDPOINT = "/subaccount/stat/aggregate"
SENDPOST_SUPPRESSION_ENDPOINT = "/subaccount/suppression"


class SendpostCollector:
    """Coleta estatísticas de email via Sendpost REST API."""

    def __init__(
        self,
        api_key: str | None = None,
        from_email: str | None = None,
    ):
        # Aceita credenciais via parâmetro (do banco) ou fallback para settings
        self.base_url = settings.sendpost_api_base_url.rstrip("/")
        self.headers = {
            "X-SubAccount-ApiKey": api_key or settings.sendpost_api_key,
            "Content-Type": "application/json",
        }
        self.from_email = from_email or settings.sendpost_alert_from_email
        self.timeout = settings.mautic_timeout_seconds

    @with_retry(exceptions=(httpx.HTTPError, httpx.TimeoutException))
    async def get_aggregate_stats(self, hours: int = 1) -> dict | None:
        """
        Coleta estatísticas agregadas do período.
        Retorna: sent, delivered, bounced, spam, unsubscribed, open_rate, click_rate.
        """
        now = datetime.now(timezone.utc)
        from_dt = now - timedelta(hours=hours)

        params = {
            "from": from_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "to": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

        try:
            async with httpx.AsyncClient(
                base_url=self.base_url,
                headers=self.headers,
                timeout=self.timeout,
            ) as client:
                resp = await client.get(SENDPOST_STATS_ENDPOINT, params=params)
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as e:
            logger.error("Sendpost API erro %s: %s", e.response.status_code, e.response.text)
            return None
        except Exception as e:
            logger.error("Erro ao coletar stats Sendpost: %s", e)
            return None

    async def collect(self) -> dict:
        """Retorna snapshot consolidado de métricas de email."""
        raw = await self.get_aggregate_stats(hours=1)

        if raw is None:
            return {
                "emails_sent": None,
                "emails_delivered": None,
                "emails_bounced": None,
                "emails_spam": None,
                "emails_unsubscribed": None,
                "open_rate": None,
                "click_rate": None,
            }

        # Mapeia campos da resposta Sendpost para nosso modelo
        # Os nomes de campo podem variar conforme a versão da API —
        # ajuste aqui se necessário sem alterar o restante do código.
        return {
            "emails_sent": raw.get("sent") or raw.get("totalSent") or 0,
            "emails_delivered": raw.get("delivered") or raw.get("totalDelivered") or 0,
            "emails_bounced": raw.get("bounced") or raw.get("totalBounced") or 0,
            "emails_spam": raw.get("spam") or raw.get("totalSpam") or 0,
            "emails_unsubscribed": raw.get("unsubscribed") or raw.get("totalUnsubscribed") or 0,
            "open_rate": raw.get("openRate") or raw.get("open_rate"),
            "click_rate": raw.get("clickRate") or raw.get("click_rate"),
        }
