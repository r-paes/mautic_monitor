"""
scheduler.py — APScheduler jobs registry.

Jobs registrados:
  1. collect_mautic_api     — intervalo configurável (scheduler_configs)
  2. collect_gateways       — intervalo configurável
  3. collect_mautic_db      — intervalo configurável
  4. collect_vps_easypanel   — intervalo configurável (itera por VPS, não instâncias)
  5. run_alert_engine       — intervalo configurável
  6. generate_reports_am    — cron diário HH:00 BRT (REPORT_CRON_MORNING)
  7. generate_reports_pm    — cron diário HH:00 BRT (REPORT_CRON_EVENING)

Intervalos são lidos do banco (scheduler_configs) no startup.
Alterações via API requerem restart do scheduler para aplicar.
"""

import logging
import uuid
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import AsyncSessionLocal
from app.collectors.mautic_api import MauticAPICollector
from app.collectors.mautic_postgres import MauticDBCollector
from app.collectors.sendpost import SendpostCollector
from app.collectors.avant_sms import AvantSMSCollector
from app.collectors.easypanel import EasyPanelCollector
from app.models.instance import Instance
from app.models.vps_server import VpsServer
from app.models.instance_service import InstanceService
from app.models.scheduler_config import SchedulerConfig
from app.models.metrics import HealthMetric, GatewayMetric
from app.models.vps_metrics import VpsMetric, ServiceStatus, ServiceLog
from app.models.reports import ReportConfig
from app.alerts import engine as alert_engine
from app.utils.crypto import decrypt_secret
from app.utils.gateway_settings import get_gateway_setting
from app.services.report_generator import generate_report, purge_old_reports
from app.services.report_sender import dispatch_report

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Intervalos default (fallback se scheduler_configs ainda não existe)
# ─────────────────────────────────────────────────────────────────────────────
DEFAULT_INTERVALS = {
    "mautic_api_interval": 5,
    "mautic_db_interval": 15,
    "vps_interval": 15,
    "gateway_interval": 5,
    "alert_engine_interval": 1,
}


async def _get_interval(key: str) -> int:
    """Lê intervalo do banco (scheduler_configs) com fallback para default."""
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(SchedulerConfig.interval_minutes)
                .where(SchedulerConfig.config_key == key)
            )
            value = result.scalar()
            return value if value is not None else DEFAULT_INTERVALS.get(key, 5)
    except Exception:
        return DEFAULT_INTERVALS.get(key, 5)


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

    # Intervalos são lidos do banco no startup via _setup_jobs
    # Os jobs são adicionados com defaults e reschedulados após leitura do banco
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

    scheduler.add_job(
        job_collect_mautic_db,
        "interval",
        minutes=settings.mautic_db_collect_interval_minutes,
        id="collect_mautic_db",
        name="Coleta DB Mautic",
        next_run_time=datetime.now(),
    )

    scheduler.add_job(
        job_collect_vps_easypanel,
        "interval",
        minutes=settings.vps_collect_interval_minutes,
        id="collect_vps_easypanel",
        name="Coleta VPS via EasyPanel",
        next_run_time=datetime.now(),
    )

    scheduler.add_job(
        job_run_alert_engine,
        "interval",
        seconds=settings.alert_engine_interval_seconds,
        id="alert_engine",
        name="Motor de Alertas",
        next_run_time=datetime.now(),
    )

    scheduler.add_job(
        job_generate_reports,
        "cron",
        hour=settings.report_cron_morning,
        minute=0,
        timezone=settings.scheduler_timezone,
        id="generate_reports_am",
        name=f"Relatórios Manhã ({settings.report_cron_morning:02d}:00 BRT)",
    )

    scheduler.add_job(
        job_generate_reports,
        "cron",
        hour=settings.report_cron_evening,
        minute=0,
        timezone=settings.scheduler_timezone,
        id="generate_reports_pm",
        name=f"Relatórios Tarde ({settings.report_cron_evening:02d}:00 BRT)",
    )

    return scheduler


async def reschedule_from_db(scheduler: AsyncIOScheduler):
    """Lê intervalos do banco e reagenda jobs. Chamar após startup."""
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(SchedulerConfig))
            configs = {c.config_key: c.interval_minutes for c in result.scalars().all()}

        job_map = {
            "mautic_api_interval": "collect_mautic_api",
            "gateway_interval": "collect_gateways",
            "mautic_db_interval": "collect_mautic_db",
            "vps_interval": "collect_vps_easypanel",
            "alert_engine_interval": "alert_engine",
        }

        for config_key, job_id in job_map.items():
            if config_key in configs:
                minutes = configs[config_key]
                job = scheduler.get_job(job_id)
                if job:
                    if config_key == "alert_engine_interval":
                        scheduler.reschedule_job(job_id, trigger="interval", seconds=minutes * 60)
                    else:
                        scheduler.reschedule_job(job_id, trigger="interval", minutes=minutes)
                    logger.info("Job '%s' reagendado para %d min", job_id, minutes)
    except Exception as e:
        logger.warning("Não foi possível ler intervalos do banco: %s (usando defaults)", e)


async def _get_active_instances(db: AsyncSession) -> list[Instance]:
    """Retorna todas as instâncias ativas do banco."""
    result = await db.execute(select(Instance).where(Instance.active == True))
    return result.scalars().all()


async def _get_active_vps_servers(db: AsyncSession) -> list[VpsServer]:
    """Retorna todas as VPS ativas do banco."""
    result = await db.execute(select(VpsServer).where(VpsServer.active == True))
    return result.scalars().unique().all()


async def _get_instance_services(db: AsyncSession, instance_id: uuid.UUID) -> list[InstanceService]:
    """Retorna serviços ativos de uma instância."""
    result = await db.execute(
        select(InstanceService).where(
            InstanceService.instance_id == instance_id,
            InstanceService.active == True,
        )
    )
    return result.scalars().all()


async def _decrypt_password(encrypted: str) -> str:
    """Decripta senha armazenada no banco via Fernet (SECRET_KEY)."""
    return decrypt_secret(encrypted)


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

        # Sendpost — coleta por sub-account
        try:
            sendpost_key = await get_gateway_setting(db, "sendpost_api_key", settings.sendpost_api_key)
            sendpost = SendpostCollector(account_api_key=sendpost_key)
            results = await sendpost.collect()
            for data in results:
                sub_id = data.pop("subaccount_id", None)
                sub_name = data.pop("subaccount_name", None)
                metric = GatewayMetric(
                    time=now,
                    gateway_type="sendpost",
                    subaccount_id=sub_id,
                    subaccount_name=sub_name,
                    **data,
                )
                db.add(metric)
        except Exception as e:
            logger.error("Erro ao coletar Sendpost: %s", e)

        # Avant SMS
        try:
            avant_token = await get_gateway_setting(db, "avant_sms_token", settings.avant_sms_token)
            avant_base_url = await get_gateway_setting(db, "avant_sms_api_base_url", settings.avant_sms_api_base_url)
            avant = AvantSMSCollector(token=avant_token, base_url=avant_base_url)
            data = await avant.collect(db_session=db)
            metric = GatewayMetric(time=now, gateway_type="avant_sms", **data)
            db.add(metric)

            await alert_engine.check_low_balance(db, data.get("balance_credits"), "Avant SMS")
        except Exception as e:
            logger.error("Erro ao coletar Avant SMS: %s", e)

        await db.commit()


async def job_collect_mautic_db():
    """Coleta métricas diretamente dos bancos MySQL Mautic."""
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


async def job_collect_vps_easypanel():
    """Coleta métricas de VPS e status de containers via EasyPanel API.

    Itera por VPS ativas (não por instâncias).
    Para cada VPS, coleta métricas de recursos e status dos serviços.
    Usa o mapeamento instance_services para associar containers às instâncias.
    """
    logger.debug("Job: collect_vps_easypanel iniciado")
    async with AsyncSessionLocal() as db:
        vps_servers = await _get_active_vps_servers(db)
        now = datetime.now(timezone.utc)

        for vps in vps_servers:
            if not vps.easypanel_url or not vps.api_key_enc:
                logger.debug("VPS %s sem URL/API key EasyPanel, pulando.", vps.name)
                continue

            try:
                api_key = decrypt_secret(vps.api_key_enc)
                collector = EasyPanelCollector(
                    easypanel_url=vps.easypanel_url,
                    api_key=api_key,
                )
                snapshot = await collector.collect()

                if snapshot.error:
                    logger.warning("VPS %s: %s", vps.name, snapshot.error)

                # Salva métricas VPS (por vps_id)
                vps_metric = VpsMetric(
                    time=now,
                    vps_id=vps.id,
                    cpu_percent=snapshot.cpu_percent,
                    memory_percent=snapshot.memory_percent,
                    memory_used_mb=snapshot.memory_used_mb,
                    memory_total_mb=snapshot.memory_total_mb,
                    disk_percent=snapshot.disk_percent,
                    disk_used_gb=snapshot.disk_used_gb,
                    disk_total_gb=snapshot.disk_total_gb,
                    load_avg_1m=snapshot.load_avg_1m,
                )
                db.add(vps_metric)

                # Monta mapeamento container_name → instance_id
                container_to_instance: dict[str, uuid.UUID] = {}
                for instance in (vps.instances or []):
                    if not instance.active:
                        continue
                    services = await _get_instance_services(db, instance.id)
                    for svc in services:
                        container_to_instance[svc.container_name] = instance.id

                # Salva status dos containers
                for container in snapshot.containers:
                    container_name = container["name"]
                    instance_id = container_to_instance.get(container_name)

                    if instance_id:
                        svc_status = ServiceStatus(
                            time=now,
                            instance_id=instance_id,
                            vps_id=vps.id,
                            container_name=container_name,
                            status=container["status"],
                            restart_count=container.get("restart_count"),
                            image=container.get("image"),
                        )
                        db.add(svc_status)

                        # Alerta container parado
                        await alert_engine.check_container_stopped(
                            db, instance_id, container_name, container["status"]
                        )

                # Verifica alertas de recursos da VPS
                await alert_engine.check_vps_cpu(db, vps.id, snapshot.cpu_percent)
                await alert_engine.check_vps_memory(db, vps.id, snapshot.memory_percent)
                await alert_engine.check_vps_disk(db, vps.id, snapshot.disk_percent)

            except Exception as e:
                logger.error("Erro ao coletar VPS EasyPanel para %s: %s", vps.name, e)

        await db.commit()


async def job_generate_reports():
    """
    Gera e envia relatórios para todas as ReportConfigs ativas.
    """
    logger.info("Job: generate_reports iniciado")
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(ReportConfig).where(ReportConfig.active == True)
        )
        configs = result.scalars().all()

        if not configs:
            logger.info("Nenhuma ReportConfig ativa encontrada.")
            return

        logger.info("Gerando relatórios para %d config(s) ativa(s).", len(configs))

        for config in configs:
            try:
                history = await generate_report(db=db, config=config, trigger="scheduled")

                if history.status == "success":
                    sp_key = await get_gateway_setting(db, "sendpost_subaccount_api_key", settings.sendpost_api_key)
                    sp_from = await get_gateway_setting(db, "sendpost_alert_from_email", settings.sendpost_alert_from_email)
                    av_token = await get_gateway_setting(db, "avant_sms_token", settings.avant_sms_token)
                    email_sent, sms_sent = await dispatch_report(
                        config, history,
                        sendpost_api_key=sp_key,
                        sendpost_from_email=sp_from,
                        avant_token=av_token,
                    )
                    history.sent_email = email_sent
                    history.sent_sms = sms_sent
                    await db.commit()
                    logger.info(
                        "Relatório OK: %s | email=%s sms=%s",
                        config.company_name,
                        email_sent,
                        sms_sent,
                    )
                else:
                    logger.warning(
                        "Relatório com erro: %s — %s",
                        config.company_name,
                        history.error_message,
                    )

            except Exception as e:
                logger.exception(
                    "Erro inesperado ao processar config %s: %s", config.id, e
                )

        try:
            removed = await purge_old_reports(db)
            if removed:
                logger.info("Purga: %d arquivo(s) antigo(s) removido(s).", removed)
        except Exception as e:
            logger.warning("Erro na purga de relatórios antigos: %s", e)


async def job_run_alert_engine():
    """
    Motor de alertas periódico — avalia Delta Alerts entre Mautic e Gateways.
    """
    logger.debug("Job: alert_engine iniciado")
    pass
