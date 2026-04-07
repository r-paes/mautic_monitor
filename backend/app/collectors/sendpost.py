"""
sendpost.py — Coleta de estatísticas via Sendpost REST API (Account-level).

Usa a X-Account-ApiKey para:
  1. Listar todas as sub-accounts da conta
  2. Coletar stats agregadas de cada sub-account individualmente

Docs: https://docs.sendpost.io/api-reference/
"""

import logging
from datetime import datetime, timedelta, timezone

import httpx

from app.config import settings
from app.utils.retry import with_retry

logger = logging.getLogger(__name__)


class SendpostCollector:
    """Coleta estatísticas de email via Sendpost Account API."""

    def __init__(self, account_api_key: str | None = None):
        self.base_url = settings.sendpost_api_base_url.rstrip("/")
        self.headers = {
            "X-Account-ApiKey": account_api_key or settings.sendpost_api_key,
            "Content-Type": "application/json",
        }
        self.timeout = settings.mautic_timeout_seconds

    @with_retry(exceptions=(httpx.HTTPError, httpx.TimeoutException))
    async def list_subaccounts(self) -> list[dict]:
        """
        Lista todas as sub-accounts da conta Sendpost.
        GET /account/subaccount/
        Retorna: [{"id": 123, "name": "Sub1", ...}, ...]
        """
        try:
            async with httpx.AsyncClient(
                base_url=self.base_url,
                headers=self.headers,
                timeout=self.timeout,
            ) as client:
                resp = await client.get("/account/subaccount/", params={"limit": 100, "offset": 0})
                resp.raise_for_status()
                data = resp.json()
                raw_list = data if isinstance(data, list) else data.get("data", [])
                # Sanitiza: extrai APENAS id e name — a API retorna apiKey,
                # smtpAuths com senhas, etc. que nunca devem ser logados/armazenados.
                return [{"id": s.get("id"), "name": s.get("name")} for s in raw_list]
        except httpx.HTTPStatusError as e:
            logger.error("Sendpost list_subaccounts erro %s: %s", e.response.status_code, e.response.text)
            return []
        except Exception as e:
            logger.error("Erro ao listar sub-accounts Sendpost: %s", e)
            return []

    @with_retry(exceptions=(httpx.HTTPError, httpx.TimeoutException))
    async def get_subaccount_stats(self, subaccount_id: int, hours: int = 1) -> dict | None:
        """
        Coleta stats agregadas de uma sub-account específica.
        GET /account/subaccount/stat/{subaccount_id}/aggregate
        Retorna: {processed, delivered, dropped, hardBounced, softBounced,
                  opened, clicked, unsubscribed, spam}
        """
        now = datetime.now(timezone.utc)
        from_dt = now - timedelta(hours=hours)

        params = {
            "from": from_dt.strftime("%Y-%m-%d"),
            "to": now.strftime("%Y-%m-%d"),
        }

        try:
            async with httpx.AsyncClient(
                base_url=self.base_url,
                headers=self.headers,
                timeout=self.timeout,
            ) as client:
                resp = await client.get(
                    f"/account/subaccount/stat/{subaccount_id}/aggregate",
                    params=params,
                )
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as e:
            logger.error(
                "Sendpost stats subaccount %s erro %s: %s",
                subaccount_id, e.response.status_code, e.response.text,
            )
            return None
        except Exception as e:
            logger.error("Erro ao coletar stats Sendpost subaccount %s: %s", subaccount_id, e)
            return None

    async def get_subaccount_stats_by_date(
        self, subaccount_id: int, from_date: str, to_date: str
    ) -> dict | None:
        """
        Coleta stats agregadas de uma sub-account para um período específico.
        from_date/to_date no formato YYYY-MM-DD.
        """
        try:
            async with httpx.AsyncClient(
                base_url=self.base_url,
                headers=self.headers,
                timeout=self.timeout,
            ) as client:
                resp = await client.get(
                    f"/account/subaccount/stat/{subaccount_id}/aggregate",
                    params={"from": from_date, "to": to_date},
                )
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as e:
            logger.error(
                "Sendpost stats subaccount %s erro %s: %s",
                subaccount_id, e.response.status_code, e.response.text,
            )
            return None
        except Exception as e:
            logger.error("Erro stats Sendpost subaccount %s: %s", subaccount_id, e)
            return None

    async def get_account_stats(self, hours: int = 1) -> dict | None:
        """
        Coleta stats agregadas de toda a conta (fallback se não há sub-accounts).
        GET /account/stat/aggregate
        """
        now = datetime.now(timezone.utc)
        from_dt = now - timedelta(hours=hours)

        params = {
            "from": from_dt.strftime("%Y-%m-%d"),
            "to": now.strftime("%Y-%m-%d"),
        }

        try:
            async with httpx.AsyncClient(
                base_url=self.base_url,
                headers=self.headers,
                timeout=self.timeout,
            ) as client:
                resp = await client.get("/account/stat/aggregate", params=params)
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as e:
            logger.error("Sendpost account stats erro %s: %s", e.response.status_code, e.response.text)
            return None
        except Exception as e:
            logger.error("Erro ao coletar stats conta Sendpost: %s", e)
            return None

    @staticmethod
    def _parse_stats(raw: dict) -> dict:
        """Converte resposta da API em dict normalizado para nosso modelo."""
        delivered = raw.get("delivered", 0) or 0
        # Account endpoints usam 'opens'/'clicks'/'spams';
        # SubAccount endpoints usam 'opened'/'clicked'/'spam'
        opened = raw.get("opened") or raw.get("opens") or 0
        clicked = raw.get("clicked") or raw.get("clicks") or 0
        spam = raw.get("spam") or raw.get("spams") or 0

        return {
            "emails_sent": raw.get("processed", 0) or 0,
            "emails_delivered": delivered,
            "emails_dropped": raw.get("dropped", 0) or 0,
            "emails_hard_bounced": raw.get("hardBounced", 0) or 0,
            "emails_soft_bounced": raw.get("softBounced", 0) or 0,
            "emails_opened": opened,
            "emails_clicked": clicked,
            "emails_unsubscribed": raw.get("unsubscribed", 0) or 0,
            "emails_spam": spam,
            "open_rate": round(opened / delivered * 100, 2) if delivered > 0 else 0.0,
            "click_rate": round(clicked / delivered * 100, 2) if delivered > 0 else 0.0,
        }

    @staticmethod
    def _empty_stats() -> dict:
        return {
            "emails_sent": None,
            "emails_delivered": None,
            "emails_dropped": None,
            "emails_hard_bounced": None,
            "emails_soft_bounced": None,
            "emails_opened": None,
            "emails_clicked": None,
            "emails_unsubscribed": None,
            "emails_spam": None,
            "open_rate": None,
            "click_rate": None,
        }

    async def collect(self) -> list[dict]:
        """
        Coleta stats de todas as sub-accounts.
        Retorna lista de dicts, cada um com:
          subaccount_id, subaccount_name, + campos de métricas
        """
        subaccounts = await self.list_subaccounts()

        if not subaccounts:
            # Fallback: coleta stats gerais da conta
            raw = await self.get_account_stats(hours=1)
            if raw is None:
                return [{"subaccount_id": None, "subaccount_name": "Conta", **self._empty_stats()}]
            return [{"subaccount_id": None, "subaccount_name": "Conta", **self._parse_stats(raw)}]

        results = []
        for sub in subaccounts:
            sub_id = sub.get("id")
            sub_name = sub.get("name", f"Sub-{sub_id}")

            raw = await self.get_subaccount_stats(sub_id, hours=1)
            if raw is None:
                stats = self._empty_stats()
            else:
                stats = self._parse_stats(raw)

            results.append({
                "subaccount_id": sub_id,
                "subaccount_name": sub_name,
                **stats,
            })

        return results
