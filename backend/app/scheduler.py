"""
scheduler.py — APScheduler jobs registry.

Jobs registrados:
  1. collect_mautic_api     — a cada METRICS_COLLECT_INTERVAL_MINUTES
  2. collect_sendpost       — a cada METRICS_COLLECT_INTERVAL_MINUTES
  3. collect_avant_sms      — a cada METRICS_COLLECT_INTERVAL_MINUTES
  4. collect_mautic_db      — a cada MAUTIC_DB_COLLECT_INTERVAL_MINUTES
  5. collect_vps_ssh        — a cada VPS_COLLECT_INTERVAL_MINUTES
  6. run_alert_engine       — a cada ALERT_ENGINE_INTERVAL_SECONDS segundos
"""

import logging
import uuid
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import AsyncSessionLocal
from app.collectors.mautic_api import MauticAPICollector
from app.collectors.mautic_db import MauticDBCollector
from app.collectors.sendpost import SendpostCollector
from app.collectors.avant_sms import AvantSMSCollector
from app.collectors.vps_ssh import VpsSSHCollector
from app.models.instance import Instance
from app.models.metrics import HealthMetric, GatewayMetric
from app.models.vps_metrics import VpsMetric, ServiceStatus, ServiceLog
from app.alerts import engine as alert_engine

from sqlalchemy import select

logger = logging.getLogger(__name__)


def create_scheduler() -> AsyncIOScheduler:
    """Cria e configura o scheduler com todos os jobs."""
    scheduler = AsyncIOScheduler(
        jobstores={"default": MemoryJobStore()},
        job_defaults={
            "coalesce": settings.scheduler_job_defaults_coalesce,
            "max_instances": settings.scheduler_job_defaults_max_instances,
            "misfire_grace_time": settings.scheduler_misfire_grace_time,
        },
        timezone=settings.scheduler_timezone,
    )

    # Job 1: API Mautic + Job 2: Sendpost + Job 3: Avant SMS
    scheduler.add_job(
        job_collect_mautic_api,
        "interval",
        minutes=settings.metrics_collect_interval_minutes,
        id="collect_mautic_api",
        name="Coleta API Mautic",
        next_run_time=datetime.now(),
    )

    scheduler.add_job(
        job_collect_gateways,
        "interval",
        minutes=settings.metrics_collect_interval_minutes,
        id="collect_gateways",
        name="Coleta Gateways (Sendpost + Avant SMS)",
        next_run_time=datetime.now(),
    )

    # Job 4: Banco Mautic
    scheduler.add_job(
        job_collect_mautic_db,
        "interval",
        minutes=settings.mautic_db_collect_interval_minutes,
        id="collect_mautic_db",
        name="Coleta DB Mautic",
        next_run_time=datetime.now(),
    )

    # Job 5: VPS SSH
    scheduler.add_job(
        job_collect_vps_ssh,
        "interval",
        minutes=settings.vps_collect_interval_minutes,
        id="collect_vps_ssh",
        name="Coleta VPS via SSH",
        next_run_time=datetime.now(),
    )

    # Job 6: Motor de alertas
    scheduler.add_job(
        job_run_alert_engine,
        "interval",
        seconds=settings.alert_engine_interval_seconds,
        id="alert_engine",
        name="Motor de Alertas",
        next_run_time=datetime.now(),
    )

    return scheduler


async def _get_active_instances(db: AsyncSession) -> list[Instance]:
    """Retorna todas as instâncias ativas do banco."""
    result = await db.execute(select(Instance).where(Instance.active == True))
    return result.scalars().all()


async def _decrypt_password(encrypted: str) -> str:
    """
    Decripta senha armazenada no banco.
    Implementação simplificada — em produção use Fernet com SECRET_KEY.
    """
    # TODO: implementar criptografia Fernet com settings.secret_key
    return encrypted


# ─────────────────────────────────────────────────────────────────────────────
# Jobs
# ─────────────────────────────────────────────────────────────────────────────

async def job_collect_mautic_api():
    """Coleta status e métricas via API REST de cada instância Mautic."""
    logger.debug("Job: collect_mautic_api iniciado")
    async with AsyncSessionLocal() as db:
        instances = await _get_active_instances(db)
        now = datetime.now(timezone.utc)

        for instance in instances:
            try:
                password = await _decrypt_password(instance.api_password_enc)
                collector = MauticAPICollector(
                    instance_url=instance.url,
                    username=instance.api_user,
                    password=password,
                )
                data = await collector.collect()

                metric = HealthMetric(
                    time=now,
                    instance_id=instance.id,
                    new_contacts=data.get("new_contacts"),
                    active_campaigns=data.get("active_campaigns"),
                    api_response_ms=data.get("api_response_ms"),
                    status=data.get("status", "ok"),
                )
                db.add(metric)

                # Verifica alertas imediatos
                await alert_engine.check_instance_status(db, instance.id, data["status"])
                if data.get("api_response_ms"):
                    await alert_engine.check_api_latency(db, instance.id, data["api_response_ms"])
                await alert_engine.check_zero_contacts(db, instance.id, data.get("new_contacts"))

            except Exception as e:
                logger.error("Erro ao coletar API Mautic para %s: %s", instance.name, e)

        await db.commit()


async def job_collect_gateways():
    """Coleta métricas dos gateways Sendpost e Avant SMS."""
    logger.debug("Job: collect_gateways iniciado")
    async with AsyncSessionLocal() as db:
        now = datetime.now(timezone.utc)

        # Sendpost
        try:
            sendpost = SendpostCollector()
            data = await sendpost.collect()
            metric = GatewayMetric(time=now, gateway_type="sendpost", **data)
            db.add(metric)

            await alert_engine.check_low_balance(db, data.get("balance_credits"), "Sendpost")
        except Exception as e:
            logger.error("Erro ao coletar Sendpost: %s", e)

        # Avant SMS
        try:
            avant = AvantSMSCollector()
            data = await avant.collect()
            metric = GatewayMetric(time=now, gateway_type="avant_sms", **data)
            db.add(metric)

            await alert_engine.check_low_balance(db, data.get("balance_credits"), "Avant SMS")
        except Exception as e:
            logger.error("Erro ao coletar Avant SMS: %s", e)

        await db.commit()


async def job_collect_mautic_db():
    """Coleta métricas diretamente dos bancos PostgreSQL Mautic."""
    logger.debug("Job: collect_mautic_db iniciado")
    async with AsyncSessionLocal() as db:
        instances = await _get_active_instances(db)
        now = datetime.now(timezone.utc)

        for instance in instances:
            if not all([instance.db_host, instance.db_name, instance.db_user]):
                continue
            try:
                db_pass = await _decrypt_password(instance.db_password_enc or "")
                collector = MauticDBCollector(
                    host=instance.db_host,
                    port=instance.db_port,
                    dbname=instance.db_name,
                    user=instance.db_user,
                    password=db_pass,
                )
                data = await collector.collect()

                # Atualiza métricas existentes do período com dados do banco
                metric = HealthMetric(
                    time=now,
                    instance_id=instance.id,
                    emails_queued=data.get("emails_queued"),
                    emails_sent_mautic=data.get("emails_sent_mautic"),
                    sms_sent_mautic=data.get("sms_sent_mautic"),
                    db_response_ms=data.get("db_response_ms"),
                    status="ok" if data.get("db_response_ms") else "degraded",
                )
                db.add(metric)

            except Exception as e:
                logger.error("Erro ao coletar DB Mautic para %s: %s", instance.name, e)

        await db.commit()


async def job_collect_vps_ssh():
    """Coleta métricas de VPS e logs de containers via SSH."""
    logger.debug("Job: collect_vps_ssh iniciado")
    async with AsyncSessionLocal() as db:
        instances = await _get_active_instances(db)
        now = datetime.now(timezone.utc)

        for instance in instances:
            if not all([instance.ssh_host, instance.ssh_user, instance.ssh_key_path]):
                logger.debug("Instância %s sem configuração SSH, pulando.", instance.name)
                continue
            try:
                collector = VpsSSHCollector(
                    host=instance.ssh_host,
                    port=instance.ssh_port,
                    username=instance.ssh_user,
                    key_path=instance.ssh_key_path,
                )
                snapshot = await collector.collect()

                if snapshot.error:
                    logger.warning("VPS %s: %s", instance.name, snapshot.error)

                # Salva métricas VPS
                vps_metric = VpsMetric(
                    time=now,
                    instance_id=instance.id,
                    cpu_percent=snapshot.cpu_percent,
                    memory_percent=snapshot.memory_percent,
                    memory_used_mb=snapshot.memory_used_mb,
                    memory_total_mb=snapshot.memory_total_mb,
                    disk_percent=snapshot.disk_percent,
                    disk_used_gb=snapshot.disk_used_gb,
                    disk_total_gb=snapshot.disk_total_gb,
                    load_avg_1m=snapshot.load_avg_1m,
                    load_avg_5m=snapshot.load_avg_5m,
                    load_avg_15m=snapshot.load_avg_15m,
                )
                db.add(vps_metric)

                # Salva status dos containers
                for container in snapshot.containers:
                    svc_status = ServiceStatus(
                        time=now,
                        instance_id=instance.id,
                        container_name=container["name"],
                        status=container["status"],
                        restart_count=container.get("restart_count"),
                        image=container.get("image"),
                    )
                    db.add(svc_status)

                    # Alerta container parado
                    await alert_engine.check_container_stopped(
                        db, instance.id, container["name"], container["status"]
                    )

                # Salva logs filtrados
                for entry in snapshot.log_entries:
                    svc_log = ServiceLog(
                        instance_id=instance.id,
                        container_name=entry["container_name"],
                        log_level=entry["log_level"],
                        message=entry["message"],
                        pattern_matched=entry.get("pattern_matched"),
                        captured_at=entry["captured_at"],
                    )
                    db.add(svc_log)

                # Verifica alertas de recursos
                await alert_engine.check_vps_cpu(db, instance.id, snapshot.cpu_percent)
                await alert_engine.check_vps_memory(db, instance.id, snapshot.memory_percent)
                await alert_engine.check_vps_disk(db, instance.id, snapshot.disk_percent)
                await alert_engine.check_log_patterns(db, instance.id, snapshot.log_entries)

            except Exception as e:
                logger.error("Erro ao coletar VPS SSH para %s: %s", instance.name, e)

        await db.commit()


async def job_run_alert_engine():
    """
    Motor de alertas periódico — avalia Delta Alerts entre Mautic e Gateways.
    Roda com mais frequência para detectar anomalias rapidamente.
    """
    logger.debug("Job: alert_engine iniciado")
    # Delta alerts são avaliados aqui comparando os últimos registros
    # do health_metrics com os gateway_metrics
    # Implementação detalhada na Fase 2
    pass
