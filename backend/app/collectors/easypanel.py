"""
easypanel.py — Monitoramento de VPS via API tRPC do EasyPanel.

Coleta: CPU, memória, disco, status de containers/serviços,
        e lista de projetos/serviços para descoberta automática.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = settings.mautic_timeout_seconds


@dataclass
class EasyPanelSnapshot:
    """Dados coletados de uma VPS via EasyPanel API."""

    cpu_percent: Optional[float] = None
    memory_percent: Optional[float] = None
    memory_used_mb: Optional[float] = None
    memory_total_mb: Optional[float] = None
    disk_percent: Optional[float] = None
    disk_used_gb: Optional[float] = None
    disk_total_gb: Optional[float] = None
    load_avg_1m: Optional[float] = None
    containers: list = field(default_factory=list)
    error: Optional[str] = None


class EasyPanelCollector:
    """Coleta métricas e status via EasyPanel tRPC API."""

    def __init__(self, easypanel_url: str, api_key: str):
        self.base_url = easypanel_url.rstrip("/")
        self.api_key = api_key

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _trpc_url(self, procedure: str) -> str:
        return f"{self.base_url}/api/trpc/{procedure}"

    async def _trpc_query(self, procedure: str, input_data: dict | None = None) -> dict:
        """Executa uma query tRPC (GET)."""
        url = self._trpc_url(procedure)
        params = {}
        if input_data is not None:
            import json
            params["input"] = json.dumps({"json": input_data})

        async with httpx.AsyncClient(verify=False, timeout=REQUEST_TIMEOUT) as client:
            resp = await client.get(url, headers=self._headers(), params=params)
            resp.raise_for_status()
            data = resp.json()
            return data.get("result", {}).get("data", {}).get("json", {})

    async def get_system_stats(self) -> dict:
        """Coleta métricas do sistema (CPU, RAM, Disco, Network)."""
        return await self._trpc_query("monitor.getSystemStats")

    async def get_projects_and_services(self) -> dict:
        """Lista todos os projetos e serviços."""
        return await self._trpc_query("projects.listProjectsAndServices")

    async def test_connection(self) -> dict:
        """Testa conexão retornando métricas básicas."""
        stats = await self.get_system_stats()
        return {
            "success": True,
            "cpu_count": stats.get("cpuInfo", {}).get("count"),
            "memory_total_mb": stats.get("memInfo", {}).get("totalMemMb"),
            "disk_total_gb": stats.get("diskInfo", {}).get("totalGb"),
            "uptime_seconds": stats.get("uptime"),
        }

    def _parse_system_stats(self, stats: dict) -> dict:
        """Extrai métricas do sistema do retorno de getSystemStats."""
        mem = stats.get("memInfo", {})
        disk = stats.get("diskInfo", {})
        cpu = stats.get("cpuInfo", {})
        loadavg = cpu.get("loadavg", [])

        return {
            "cpu_percent": cpu.get("usedPercentage"),
            "memory_percent": mem.get("usedMemPercentage"),
            "memory_used_mb": mem.get("usedMemMb"),
            "memory_total_mb": mem.get("totalMemMb"),
            "disk_percent": _to_float(disk.get("usedPercentage")),
            "disk_used_gb": _to_float(disk.get("usedGb")),
            "disk_total_gb": _to_float(disk.get("totalGb")),
            "load_avg_1m": loadavg[0] if loadavg else None,
        }

    def _parse_services(self, data: dict) -> list[dict]:
        """Extrai lista de containers/serviços do retorno de listProjectsAndServices."""
        containers = []
        for svc in data.get("services", []):
            name = svc.get("name", "")
            project = svc.get("projectName", "")
            svc_type = svc.get("type", "app")
            enabled = svc.get("enabled", True)

            status = "running" if enabled else "stopped"
            image = ""

            if svc_type in ("mysql", "postgres", "redis", "mongo", "mariadb"):
                image = svc.get("image", "")
            else:
                source = svc.get("source", {})
                if source:
                    image = source.get("image", "") or ""

            containers.append({
                "name": name,
                "project": project,
                "status": status,
                "image": image,
                "type": svc_type,
                "restart_count": 0,
            })
        return containers

    async def collect(self) -> EasyPanelSnapshot:
        """Coleta todas as métricas disponíveis via EasyPanel API."""
        snapshot = EasyPanelSnapshot()

        try:
            stats = await self.get_system_stats()
            parsed = self._parse_system_stats(stats)
            snapshot.cpu_percent = parsed["cpu_percent"]
            snapshot.memory_percent = parsed["memory_percent"]
            snapshot.memory_used_mb = parsed["memory_used_mb"]
            snapshot.memory_total_mb = parsed["memory_total_mb"]
            snapshot.disk_percent = parsed["disk_percent"]
            snapshot.disk_used_gb = parsed["disk_used_gb"]
            snapshot.disk_total_gb = parsed["disk_total_gb"]
            snapshot.load_avg_1m = parsed["load_avg_1m"]

            services_data = await self.get_projects_and_services()
            snapshot.containers = self._parse_services(services_data)

        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            if status == 401:
                snapshot.error = "auth_failed"
                logger.error("EasyPanel auth falhou para %s", self.base_url)
            else:
                snapshot.error = f"http_{status}"
                logger.error("Erro HTTP %s em %s", status, self.base_url)
        except httpx.ConnectError:
            snapshot.error = "connection_failed"
            logger.error("Não foi possível conectar em %s", self.base_url)
        except Exception as e:
            snapshot.error = str(e)
            logger.error("Erro inesperado ao coletar VPS %s: %s", self.base_url, e)

        return snapshot


def _to_float(val) -> Optional[float]:
    """Converte string ou número para float (EasyPanel retorna disk como string)."""
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None
