"""
alerts/engine.py — Motor de regras para geração e escalonamento de alertas.

Regras avaliadas a cada ALERT_ENGINE_INTERVAL_SECONDS.
Escalonamento:
  WARNING  → apenas email
  CRITICAL → email + SMS simultaneamente

Cooldown configurável via ALERT_COOLDOWN_MINUTES para evitar flood.
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.alerts import Alert
from app.models.metrics import HealthMetric, GatewayMetric
from app.models.users import User
from app.models.vps_metrics import VpsMetric, ServiceStatus
from app.alerts.email_alert import send_alert_email
from app.alerts.sms_alert import send_alert_sms
from app.utils.gateway_settings import get_gateway_setting

logger = logging.getLogger(__name__)

# Severidades e canais de notificação
SEVERITY_WARNING = "warning"
SEVERITY_CRITICAL = "critical"
SEVERITY_INFO = "info"

CHANNEL_EMAIL = "email"
CHANNEL_SMS = "sms"
CHANNEL_BOTH = "both"

# Mapa de severidade → canal(is) de notificação
SEVERITY_CHANNEL_MAP = {
    SEVERITY_INFO: None,                 # sem notificação externa
    SEVERITY_WARNING: CHANNEL_EMAIL,     # só email
    SEVERITY_CRITICAL: CHANNEL_BOTH,     # email + SMS
}


async def _is_in_cooldown(
    db: AsyncSession,
    instance_id: Optional[uuid.UUID],
    alert_type: str,
) -> bool:
    """Verifica se já existe alerta recente do mesmo tipo (cooldown)."""
    cooldown_since = datetime.now(timezone.utc) - timedelta(
        minutes=settings.alert_cooldown_minutes
    )
    query = select(Alert).where(
        and_(
            Alert.type == alert_type,
            Alert.instance_id == instance_id,
            Alert.created_at >= cooldown_since,
            Alert.resolved_at.is_(None),
        )
    )
    result = await db.execute(query)
    return result.scalars().first() is not None


async def _create_alert(
    db: AsyncSession,
    severity: str,
    alert_type: str,
    message: str,
    instance_id: Optional[uuid.UUID] = None,
) -> Alert | None:
    """Cria alerta no banco e dispara notificações conforme severidade."""

    # Verifica cooldown
    if await _is_in_cooldown(db, instance_id, alert_type):
        logger.debug("Alerta %s em cooldown para instância %s", alert_type, instance_id)
        return None

    # Define canal de notificação
    channel = SEVERITY_CHANNEL_MAP.get(severity)

    alert = Alert(
        instance_id=instance_id,
        severity=severity,
        type=alert_type,
        message=message,
        notified_via=channel,
    )
    db.add(alert)
    await db.flush()

    logger.warning("[ALERT %s] %s — %s", severity.upper(), alert_type, message)

    # Dispara notificações se acima do nível mínimo configurado
    min_severity = settings.alert_min_severity_to_notify
    if min_severity == SEVERITY_INFO or severity in (SEVERITY_WARNING, SEVERITY_CRITICAL):
        if channel in (CHANNEL_EMAIL, CHANNEL_BOTH):
            await _notify_users_email(db, severity, alert_type, message)

        if channel in (CHANNEL_SMS, CHANNEL_BOTH):
            await _notify_users_sms(db, severity, alert_type, message)

    return alert


async def _notify_users_email(db: AsyncSession, severity: str, alert_type: str, message: str):
    """Envia email para todos os usuários ativos com alert_email configurado."""
    # Credenciais do banco (prioridade) com fallback para .env
    api_key = await get_gateway_setting(db, "sendpost_api_key", settings.sendpost_api_key)
    from_email = await get_gateway_setting(db, "sendpost_alert_from_email", settings.sendpost_alert_from_email)

    result = await db.execute(
        select(User).where(User.active == True, User.alert_email.isnot(None))
    )
    users = result.scalars().all()
    for user in users:
        await send_alert_email(
            to_email=user.alert_email,
            to_name=user.name,
            severity=severity,
            alert_type=alert_type,
            message=message,
            api_key=api_key,
            from_email=from_email,
        )


async def _notify_users_sms(db: AsyncSession, severity: str, alert_type: str, message: str):
    """Envia SMS para todos os usuários ativos com alert_phone configurado."""
    # Credenciais do banco (prioridade) com fallback para .env
    sms_token = await get_gateway_setting(db, "avant_sms_token", settings.avant_sms_token)

    result = await db.execute(
        select(User).where(User.active == True, User.alert_phone.isnot(None))
    )
    users = result.scalars().all()
    for user in users:
        await send_alert_sms(
            to_phone=user.alert_phone,
            severity=severity,
            alert_type=alert_type,
            message=message,
            token=sms_token,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Regras de alerta
# ─────────────────────────────────────────────────────────────────────────────

async def check_instance_status(db: AsyncSession, instance_id: uuid.UUID, status: str):
    """Alerta se instância Mautic está offline ou degradada."""
    if status == "down":
        await _create_alert(
            db, SEVERITY_CRITICAL, "instance_down",
            f"Instância {instance_id} está OFFLINE — sem resposta da API.",
            instance_id=instance_id,
        )
    elif status == "degraded":
        await _create_alert(
            db, SEVERITY_WARNING, "instance_degraded",
            f"Instância {instance_id} está degradada — API respondendo com erros.",
            instance_id=instance_id,
        )


async def check_api_latency(db: AsyncSession, instance_id: uuid.UUID, latency_ms: int | None):
    """Alerta se latência da API Mautic está acima do threshold."""
    if latency_ms and latency_ms > settings.alert_threshold_api_latency_ms:
        await _create_alert(
            db, SEVERITY_WARNING, "high_api_latency",
            f"Latência da API elevada: {latency_ms}ms (threshold: {settings.alert_threshold_api_latency_ms}ms).",
            instance_id=instance_id,
        )


async def check_zero_contacts(db: AsyncSession, instance_id: uuid.UUID, new_contacts: int | None):
    """Alerta se não há novos contatos nas últimas N horas."""
    if new_contacts is not None and new_contacts == 0:
        await _create_alert(
            db, SEVERITY_WARNING, "zero_contacts",
            f"Nenhum novo contato nas últimas {settings.alert_no_contacts_hours}h na instância {instance_id}.",
            instance_id=instance_id,
        )


async def check_vps_cpu(db: AsyncSession, instance_id: uuid.UUID, cpu_percent: float | None):
    """Alerta por uso elevado de CPU."""
    if cpu_percent is None:
        return
    if cpu_percent >= settings.alert_threshold_cpu_critical:
        await _create_alert(
            db, SEVERITY_CRITICAL, "high_cpu",
            f"CPU crítica: {cpu_percent}% (threshold crítico: {settings.alert_threshold_cpu_critical}%).",
            instance_id=instance_id,
        )
    elif cpu_percent >= settings.alert_threshold_cpu_warning:
        await _create_alert(
            db, SEVERITY_WARNING, "high_cpu",
            f"CPU elevada: {cpu_percent}% (threshold: {settings.alert_threshold_cpu_warning}%).",
            instance_id=instance_id,
        )


async def check_vps_memory(db: AsyncSession, instance_id: uuid.UUID, memory_percent: float | None):
    """Alerta por uso elevado de memória."""
    if memory_percent is None:
        return
    if memory_percent >= settings.alert_threshold_memory_critical:
        await _create_alert(
            db, SEVERITY_CRITICAL, "high_memory",
            f"Memória crítica: {memory_percent}% (threshold crítico: {settings.alert_threshold_memory_critical}%).",
            instance_id=instance_id,
        )
    elif memory_percent >= settings.alert_threshold_memory_warning:
        await _create_alert(
            db, SEVERITY_WARNING, "high_memory",
            f"Memória elevada: {memory_percent}% (threshold: {settings.alert_threshold_memory_warning}%).",
            instance_id=instance_id,
        )


async def check_vps_disk(db: AsyncSession, instance_id: uuid.UUID, disk_percent: float | None):
    """Alerta por uso elevado de disco."""
    if disk_percent is None:
        return
    if disk_percent >= settings.alert_threshold_disk_critical:
        await _create_alert(
            db, SEVERITY_CRITICAL, "high_disk",
            f"Disco crítico: {disk_percent}% (threshold crítico: {settings.alert_threshold_disk_critical}%).",
            instance_id=instance_id,
        )
    elif disk_percent >= settings.alert_threshold_disk_warning:
        await _create_alert(
            db, SEVERITY_WARNING, "high_disk",
            f"Disco elevado: {disk_percent}% (threshold: {settings.alert_threshold_disk_warning}%).",
            instance_id=instance_id,
        )


async def check_container_stopped(db: AsyncSession, instance_id: uuid.UUID, container_name: str, status: str):
    """Alerta se container Docker está parado."""
    if status in ("stopped", "error"):
        await _create_alert(
            db, SEVERITY_CRITICAL, "container_stopped",
            f"Container '{container_name}' está {status} na instância {instance_id}.",
            instance_id=instance_id,
        )


async def check_low_balance(db: AsyncSession, balance: float | None, gateway: str):
    """Alerta se saldo do gateway está baixo."""
    LOW_BALANCE_THRESHOLD = 100  # ajuste conforme necessário
    if balance is not None and balance < LOW_BALANCE_THRESHOLD:
        await _create_alert(
            db, SEVERITY_WARNING, "low_balance",
            f"Saldo baixo no gateway {gateway}: {balance} créditos.",
        )


async def check_email_delta(
    db: AsyncSession,
    instance_id: uuid.UUID,
    mautic_sent: int | None,
    gateway_sent: int | None,
):
    """
    Delta Alert: compara emails enviados pelo Mautic vs. confirmados pelo Sendpost.
    Uma diferença acima do threshold indica falha silenciosa de entrega.
    """
    if mautic_sent is None or gateway_sent is None or mautic_sent == 0:
        return

    delta_pct = abs(mautic_sent - gateway_sent) / mautic_sent * 100

    if delta_pct > settings.alert_threshold_email_delta_pct:
        await _create_alert(
            db, SEVERITY_CRITICAL, "email_delta",
            f"Delta de email: Mautic={mautic_sent} vs Sendpost={gateway_sent} "
            f"({delta_pct:.1f}% — threshold: {settings.alert_threshold_email_delta_pct}%).",
            instance_id=instance_id,
        )


async def check_sms_delta(
    db: AsyncSession,
    instance_id: uuid.UUID,
    mautic_sent: int | None,
    gateway_sent: int | None,
):
    """
    Delta Alert: compara SMS enviados pelo Mautic vs. confirmados pelo Avant SMS.
    """
    if mautic_sent is None or gateway_sent is None or mautic_sent == 0:
        return

    delta_pct = abs(mautic_sent - gateway_sent) / mautic_sent * 100

    if delta_pct > settings.alert_threshold_sms_delta_pct:
        await _create_alert(
            db, SEVERITY_CRITICAL, "sms_delta",
            f"Delta de SMS: Mautic={mautic_sent} vs Avant={gateway_sent} "
            f"({delta_pct:.1f}% — threshold: {settings.alert_threshold_sms_delta_pct}%).",
            instance_id=instance_id,
        )


async def check_log_patterns(
    db: AsyncSession,
    instance_id: uuid.UUID,
    log_entries: list[dict],
):
    """Gera alertas para padrões críticos detectados nos logs das VPS."""
    for entry in log_entries:
        level = entry.get("log_level", "warning")
        severity = SEVERITY_CRITICAL if level == "critical" else SEVERITY_WARNING
        await _create_alert(
            db, severity, entry.get("pattern_matched", "log_error"),
            f"[{entry['container_name']}] {entry['message'][:200]}",
            instance_id=instance_id,
        )
