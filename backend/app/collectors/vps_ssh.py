"""
vps_ssh.py — Monitoramento de VPS via SSH (paramiko).

Coleta: CPU, memória, disco, load average, status de containers Docker,
        logs recentes de containers (filtra padrões de erro conhecidos).
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from io import StringIO
from typing import Optional

import paramiko

from app.config import settings

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Padrões de erro para análise de logs
# Cada entrada: (regex_pattern, log_level, alert_type)
# ─────────────────────────────────────────────────────────────────────────────
LOG_ERROR_PATTERNS = [
    (r"PHP Fatal error", "critical", "php_fatal"),
    (r"Out of memory|OOM|Killed process", "critical", "oom"),
    (r"disk quota exceeded|No space left on device", "critical", "disk_full"),
    (r"Segmentation fault", "critical", "segfault"),
    (r"Too many connections|max_connections", "warning", "db_connection"),
    (r"Connection refused|ECONNREFUSED", "warning", "connection_refused"),
    (r"SMTP Error|SMTP connect\(\) failed", "warning", "smtp_error"),
    (r"MySQL server has gone away|could not connect to server", "warning", "db_connection"),
    (r"PHP Warning|PHP Notice", "warning", "php_warning"),
    (r"Error while sending QUERY packet", "warning", "db_connection"),
]

# Comandos SSH — centralizados aqui para fácil manutenção
CMD_LOAD_AVG = "cat /proc/loadavg"
CMD_MEMORY = "free -m"
CMD_DISK = "df -h / --output=used,avail,size,pcent"
CMD_CPU = "grep 'cpu ' /proc/stat"
CMD_CPU_SLEEP = "sleep 0.5 && grep 'cpu ' /proc/stat"
CMD_DOCKER_PS = "docker ps --format '{{.Names}}|{{.Status}}|{{.Image}}|{{.RunningFor}}'"
CMD_DOCKER_LOGS = "docker logs --tail 200 --since {since} {container} 2>&1"

LOG_COLLECTION_SINCE = "15m"


@dataclass
class VpsSnapshot:
    """Dados coletados de uma VPS via SSH."""
    cpu_percent: Optional[float] = None
    memory_percent: Optional[float] = None
    memory_used_mb: Optional[int] = None
    memory_total_mb: Optional[int] = None
    disk_percent: Optional[float] = None
    disk_used_gb: Optional[float] = None
    disk_total_gb: Optional[float] = None
    load_avg_1m: Optional[float] = None
    load_avg_5m: Optional[float] = None
    load_avg_15m: Optional[float] = None
    containers: list = field(default_factory=list)
    log_entries: list = field(default_factory=list)
    error: Optional[str] = None


class VpsSSHCollector:
    """Coleta métricas e logs de uma VPS via SSH usando paramiko."""

    def __init__(self, host: str, port: int, username: str, key_path: str):
        self.host = host
        self.port = port
        self.username = username
        self.key_path = key_path

    def _create_client(self) -> paramiko.SSHClient:
        """Cria e conecta cliente SSH."""
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            hostname=self.host,
            port=self.port,
            username=self.username,
            key_filename=self.key_path,
            timeout=settings.mautic_timeout_seconds,
            look_for_keys=False,
            allow_agent=False,
        )
        return client

    def _exec(self, client: paramiko.SSHClient, command: str) -> str:
        """Executa comando remoto e retorna stdout."""
        _, stdout, stderr = client.exec_command(command, timeout=settings.mautic_timeout_seconds)
        output = stdout.read().decode("utf-8", errors="replace").strip()
        return output

    def _parse_load_avg(self, output: str) -> tuple[float, float, float]:
        """Extrai load averages de /proc/loadavg."""
        parts = output.split()
        return float(parts[0]), float(parts[1]), float(parts[2])

    def _parse_memory(self, output: str) -> tuple[int, int, float]:
        """Extrai uso de memória de 'free -m'."""
        for line in output.splitlines():
            if line.startswith("Mem:"):
                parts = line.split()
                total = int(parts[1])
                used = int(parts[2])
                percent = round((used / total) * 100, 1) if total > 0 else 0
                return used, total, percent
        return 0, 0, 0.0

    def _parse_disk(self, output: str) -> tuple[float, float, float]:
        """Extrai uso de disco de 'df -h'."""
        lines = output.strip().splitlines()
        if len(lines) < 2:
            return 0.0, 0.0, 0.0
        parts = lines[-1].split()
        # Formato: used avail size pcent
        def to_gb(s: str) -> float:
            s = s.upper().replace(",", ".")
            if s.endswith("G"):
                return float(s[:-1])
            if s.endswith("M"):
                return round(float(s[:-1]) / 1024, 2)
            if s.endswith("T"):
                return round(float(s[:-1]) * 1024, 2)
            return 0.0

        used_gb = to_gb(parts[0]) if len(parts) > 0 else 0.0
        total_gb = to_gb(parts[2]) if len(parts) > 2 else 0.0
        percent_str = parts[3].replace("%", "") if len(parts) > 3 else "0"
        percent = float(percent_str)
        return used_gb, total_gb, percent

    def _parse_cpu(self, output1: str, output2: str) -> float:
        """Calcula uso de CPU a partir de duas leituras de /proc/stat."""
        def parse_stat(line: str):
            parts = list(map(int, line.split()[1:]))
            idle = parts[3]
            total = sum(parts)
            return idle, total

        try:
            idle1, total1 = parse_stat(output1)
            idle2, total2 = parse_stat(output2)
            diff_idle = idle2 - idle1
            diff_total = total2 - total1
            if diff_total == 0:
                return 0.0
            return round((1 - diff_idle / diff_total) * 100, 1)
        except Exception:
            return 0.0

    def _parse_containers(self, output: str) -> list[dict]:
        """Analisa saída de 'docker ps'."""
        containers = []
        for line in output.splitlines():
            parts = line.split("|")
            if len(parts) < 2:
                continue
            name = parts[0].strip()
            status_raw = parts[1].strip()
            image = parts[2].strip() if len(parts) > 2 else ""
            running_for = parts[3].strip() if len(parts) > 3 else ""

            status = "running" if status_raw.lower().startswith("up") else "stopped"
            if "restarting" in status_raw.lower():
                status = "restarting"
            if "error" in status_raw.lower():
                status = "error"

            # Extrai contagem de restarts
            restart_match = re.search(r"Restarting \((\d+)\)", status_raw)
            restart_count = int(restart_match.group(1)) if restart_match else 0

            containers.append({
                "name": name,
                "status": status,
                "image": image,
                "running_for": running_for,
                "restart_count": restart_count,
            })
        return containers

    def _analyze_logs(self, container_name: str, log_output: str) -> list[dict]:
        """Filtra logs em busca de padrões de erro conhecidos."""
        entries = []
        captured_at = datetime.now(timezone.utc)

        for line in log_output.splitlines():
            for pattern, level, alert_type in LOG_ERROR_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    entries.append({
                        "container_name": container_name,
                        "log_level": level,
                        "message": line[:1000],  # limita tamanho
                        "pattern_matched": alert_type,
                        "captured_at": captured_at,
                    })
                    break  # um padrão por linha é suficiente

        return entries

    async def collect(self) -> VpsSnapshot:
        """Conecta via SSH e coleta todos os dados disponíveis."""
        snapshot = VpsSnapshot()

        try:
            client = self._create_client()

            # Load average
            load_output = self._exec(client, CMD_LOAD_AVG)
            snapshot.load_avg_1m, snapshot.load_avg_5m, snapshot.load_avg_15m = (
                self._parse_load_avg(load_output)
            )

            # Memória
            mem_output = self._exec(client, CMD_MEMORY)
            snapshot.memory_used_mb, snapshot.memory_total_mb, snapshot.memory_percent = (
                self._parse_memory(mem_output)
            )

            # Disco
            disk_output = self._exec(client, CMD_DISK)
            snapshot.disk_used_gb, snapshot.disk_total_gb, snapshot.disk_percent = (
                self._parse_disk(disk_output)
            )

            # CPU (duas leituras com intervalo de 0.5s)
            cpu1 = self._exec(client, CMD_CPU)
            cpu2 = self._exec(client, CMD_CPU_SLEEP)
            snapshot.cpu_percent = self._parse_cpu(cpu1, cpu2)

            # Containers Docker
            docker_output = self._exec(client, CMD_DOCKER_PS)
            snapshot.containers = self._parse_containers(docker_output)

            # Logs dos containers (apenas padrões de erro)
            log_entries = []
            for container in snapshot.containers:
                log_cmd = CMD_DOCKER_LOGS.format(
                    since=LOG_COLLECTION_SINCE,
                    container=container["name"],
                )
                log_output = self._exec(client, log_cmd)
                entries = self._analyze_logs(container["name"], log_output)
                log_entries.extend(entries)

            snapshot.log_entries = log_entries
            client.close()

        except paramiko.AuthenticationException:
            snapshot.error = "ssh_auth_failed"
            logger.error("SSH auth falhou para %s@%s", self.username, self.host)
        except paramiko.SSHException as e:
            snapshot.error = f"ssh_error: {e}"
            logger.error("Erro SSH em %s: %s", self.host, e)
        except Exception as e:
            snapshot.error = str(e)
            logger.error("Erro inesperado ao coletar VPS %s: %s", self.host, e)

        return snapshot
