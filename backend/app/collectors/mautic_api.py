"""
mautic_api.py — Coleta de dados via API REST do Mautic.

Coleta: ping/latência, novos contatos, campanhas ativas.
Credenciais lidas do banco de dados por instância.
"""

import logging
import time
from datetime import datetime, timedelta, timezone

import httpx

from app.config import settings
from app.utils.retry import with_retry

logger = logging.getLogger(__name__)


class MauticAPICollector:
    """Coleta métricas de uma instância Mautic via API REST."""

    def __init__(self, instance_url: str, username: str, password: str):
        self.base_url = instance_url.rstrip("/")
        self.auth = (username, password)
        self.timeout = settings.mautic_timeout_seconds

    @with_retry(exceptions=(httpx.HTTPError, httpx.TimeoutException))
    async def ping(self) -> dict:
        """Verifica disponibilidade da instância e mede latência."""
        start = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(
                    f"{self.base_url}/api/contacts",
                    auth=self.auth,
                    params={"limit": 1},
                )
                resp.raise_for_status()
                latency_ms = int((time.monotonic() - start) * 1000)
                return {"status": "ok", "latency_ms": latency_ms}
        except httpx.TimeoutException:
            return {"status": "down", "latency_ms": None, "error": "timeout"}
        except httpx.HTTPStatusError as e:
            return {"status": "degraded", "latency_ms": None, "error": str(e)}
        except Exception as e:
            logger.error("Erro ao pingar instância %s: %s", self.base_url, e)
            return {"status": "down", "latency_ms": None, "error": str(e)}

    @with_retry(exceptions=(httpx.HTTPError,))
    async def get_new_contacts_count(self, hours: int = 24) -> int | None:
        """Retorna número de contatos criados nas últimas N horas."""
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        since_str = since.strftime("%Y-%m-%dT%H:%M:%S%z")
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(
                    f"{self.base_url}/api/contacts",
                    auth=self.auth,
                    params={
                        "search": f"date_added:>{since_str}",
                        "minimal": 1,
                        "limit": 1,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                return data.get("total", 0)
        except Exception as e:
            logger.warning("Erro ao obter contatos novos: %s", e)
            return None

    @with_retry(exceptions=(httpx.HTTPError,))
    async def get_active_campaigns_count(self) -> int | None:
        """Retorna número de campanhas ativas (publicadas)."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(
                    f"{self.base_url}/api/campaigns",
                    auth=self.auth,
                    params={"search": "isPublished:1", "minimal": 1, "limit": 1},
                )
                resp.raise_for_status()
                data = resp.json()
                return data.get("total", 0)
        except Exception as e:
            logger.warning("Erro ao obter campanhas ativas: %s", e)
            return None

    async def collect(self) -> dict:
        """Executa todas as coletas e retorna snapshot consolidado."""
        ping_result = await self.ping()
        new_contacts = None
        active_campaigns = None

        if ping_result["status"] != "down":
            new_contacts = await self.get_new_contacts_count()
            active_campaigns = await self.get_active_campaigns_count()

        return {
            "status": ping_result["status"],
            "api_response_ms": ping_result.get("latency_ms"),
            "new_contacts": new_contacts,
            "active_campaigns": active_campaigns,
        }
