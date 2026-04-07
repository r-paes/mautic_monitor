"""
report_generator.py — Orquestra a geração de relatórios Mautic.

Fluxo:
  1. Recebe ReportConfig + período
  2. Busca TODAS as instâncias ativas com credenciais MySQL configuradas
  3. Coleta dados via MauticMySQLCollector em paralelo (asyncio.gather)
  4. Agrega totais e mantém breakdown por instância
  5. Renderiza HTML via Jinja2
  6. Salva arquivo em disco (report_storage_path)
  7. Atualiza ReportHistory no banco
"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.collectors.mautic_mysql import MauticMySQLCollector
from app.config import settings
from app.models.instance import Instance, InstanceDbCredential
from app.models.reports import ReportConfig, ReportHistory
from app.utils.crypto import decrypt_secret

logger = logging.getLogger(__name__)

# ─── Jinja2 ───────────────────────────────────────────────────────────────────

_TEMPLATES_DIR = Path(__file__).parent.parent / "templates"

_jinja_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATES_DIR)),
    autoescape=select_autoescape(["html", "j2"]),
    trim_blocks=True,
    lstrip_blocks=True,
)


def _render_report(context: dict) -> str:
    """Renderiza o template Jinja2 com o contexto fornecido."""
    template = _jinja_env.get_template("report.html.j2")
    return template.render(**context)


# ─── Período padrão ───────────────────────────────────────────────────────────

def default_period(now: Optional[datetime] = None) -> tuple[datetime, datetime]:
    """
    Retorna (period_start, period_end) para o relatório padrão:
    hoje das 00:00 até agora.
    """
    if now is None:
        now = datetime.now(tz=timezone.utc)
    period_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    period_end = now
    return period_start, period_end


# ─── Salvamento ───────────────────────────────────────────────────────────────

def _build_file_path(config: ReportConfig, generated_at: datetime) -> Path:
    """
    Monta o caminho absoluto onde o relatório será salvo.
    Estrutura: {report_storage_path}/{config_id}/{YYYY-MM}/{timestamp}.html
    """
    base = Path(settings.report_storage_path)
    subdir = base / str(config.id) / generated_at.strftime("%Y-%m")
    subdir.mkdir(parents=True, exist_ok=True)
    filename = f"report_{generated_at.strftime('%Y%m%d_%H%M%S')}.html"
    return subdir / filename


def _build_file_url(file_path: Path) -> str:
    """Constrói URL pública relativa ao report_storage_path."""
    base = Path(settings.report_storage_path)
    relative = file_path.relative_to(base)
    return f"/reports/{relative}"


# ─── Coleta cross-instance ────────────────────────────────────────────────────

async def _collect_instance(
    instance: Instance,
    company_id: Optional[int],
    period_start: datetime,
    period_end: datetime,
) -> dict:
    """
    Coleta dados de uma instância para a empresa informada.
    Retorna dict com instance_name, email, sms, contacts + error flag.
    """
    try:
        db_password = decrypt_secret(instance.db_password_enc or "")
        collector = MauticMySQLCollector(
            host=instance.db_host,
            port=instance.db_port or 3306,
            dbname=instance.db_name,
            user=instance.db_user,
            password=db_password,
        )
        data = await collector.collect_for_report(
            period_start=period_start,
            period_end=period_end,
            company_id=company_id,
        )
        return {
            "instance_id": str(instance.id),
            "instance_name": instance.name,
            "error": None,
            **data,
        }
    except Exception as exc:
        logger.warning(
            "Falha ao coletar instância %s para empresa id=%s: %s",
            instance.name,
            company_id,
            exc,
        )
        return {
            "instance_id": str(instance.id),
            "instance_name": instance.name,
            "error": str(exc),
            "email": {"total_sent": 0, "total_opened": 0, "total_clicked": 0, "total_failed": 0},
            "sms": {"total_sent": 0, "total_failed": 0},
            "contacts": {"new_contacts": 0, "active_contacts": 0},
        }


def _aggregate(instance_results: list[dict]) -> tuple[dict, dict, dict]:
    """
    Soma totais de email, sms e contatos entre instâncias.
    Retorna (email_totals, sms_totals, contacts_totals).
    """
    email = {"total_sent": 0, "total_opened": 0, "total_clicked": 0, "total_failed": 0}
    sms = {"total_sent": 0, "total_failed": 0}
    contacts = {"new_contacts": 0, "active_contacts": 0}

    for r in instance_results:
        for k in email:
            email[k] += r["email"].get(k, 0)
        for k in sms:
            sms[k] += r["sms"].get(k, 0)
        for k in contacts:
            contacts[k] += r["contacts"].get(k, 0)

    return email, sms, contacts


# ─── Gerador principal ────────────────────────────────────────────────────────

async def generate_report(
    db: AsyncSession,
    config: ReportConfig,
    trigger: str = "scheduled",
    period_start: Optional[datetime] = None,
    period_end: Optional[datetime] = None,
) -> ReportHistory:
    """
    Gera um relatório para a config fornecida, coletando dados de TODAS
    as instâncias ativas com MySQL configurado.

    Args:
        db:           sessão AsyncSession do banco principal
        config:       ReportConfig com company_name + mautic_company_id
        trigger:      'scheduled' | 'manual'
        period_start: início do período (padrão: hoje 00:00 UTC)
        period_end:   fim do período (padrão: agora UTC)

    Returns:
        ReportHistory com status='success' ou status='error'
    """
    now = datetime.now(tz=timezone.utc)

    if period_start is None or period_end is None:
        period_start, period_end = default_period(now)

    # Cria registro inicial como 'generating'
    history = ReportHistory(
        id=uuid.uuid4(),
        report_config_id=config.id,
        instance_id=config.instance_id,
        generated_at=now,
        period_start=period_start,
        period_end=period_end,
        trigger=trigger,
        status="generating",
    )
    db.add(history)
    await db.commit()
    await db.refresh(history)

    try:
        # ── Carrega todas as instâncias ativas com MySQL configurado ──────────
        result = await db.execute(
            select(Instance)
            .join(InstanceDbCredential)
            .where(Instance.active == True)
        )
        instances = result.scalars().all()

        if not instances:
            raise ValueError("Nenhuma instância ativa com MySQL configurado encontrada.")

        # ── Coleta em paralelo ────────────────────────────────────────────────
        tasks = [
            _collect_instance(inst, config.mautic_company_id, period_start, period_end)
            for inst in instances
        ]
        instance_results: list[dict] = await asyncio.gather(*tasks)

        # Separa instâncias com e sem dados para o relatório
        instances_with_data = [r for r in instance_results if r["error"] is None]
        instances_with_errors = [r for r in instance_results if r["error"] is not None]

        if not instances_with_data:
            errors = "; ".join(r["error"] for r in instances_with_errors)
            raise ValueError(f"Todas as instâncias falharam na coleta: {errors}")

        # ── Agrega totais ─────────────────────────────────────────────────────
        email_totals, sms_totals, contacts_totals = _aggregate(instance_results)

        # ── Renderiza HTML ────────────────────────────────────────────────────
        fmt = "%d/%m/%Y %H:%M"

        html_content = _render_report({
            "company_name": config.company_name,
            "generated_at": now.strftime(fmt) + " BRT",
            "period_start": period_start.strftime(fmt),
            "period_end": period_end.strftime(fmt),
            # Totais agregados (todas as instâncias)
            "email": email_totals,
            "sms": sms_totals,
            "contacts": contacts_totals,
            # Breakdown por instância
            "instances_data": instance_results,
            "instances_count": len(instances),
            "show_breakdown": len(instances) > 1,
            "show_sms": config.send_sms,
            "logo_url": f"https://{settings.easypanel_domain}/static/logo.png",
            "support_email": settings.sendpost_alert_from_email,
        })

        # ── Salva em disco ────────────────────────────────────────────────────
        file_path = _build_file_path(config, now)
        file_path.write_text(html_content, encoding="utf-8")
        file_url = _build_file_url(file_path)

        # ── Atualiza histórico ────────────────────────────────────────────────
        history.status = "success"
        history.file_path = str(file_path)
        history.file_url = file_url
        # Armazena totais + breakdown para auditoria
        history.email_stats_json = {
            **email_totals,
            "by_instance": [
                {
                    "instance_id": r["instance_id"],
                    "instance_name": r["instance_name"],
                    **r["email"],
                }
                for r in instance_results
            ],
        }
        history.sms_stats_json = {
            **sms_totals,
            "by_instance": [
                {
                    "instance_id": r["instance_id"],
                    "instance_name": r["instance_name"],
                    **r["sms"],
                }
                for r in instance_results
            ],
        }

        logger.info(
            "Relatório gerado: %s | %d instância(s) | email_sent=%d → %s",
            config.company_name,
            len(instances),
            email_totals["total_sent"],
            file_path.name,
        )

        if instances_with_errors:
            logger.warning(
                "Relatório %s gerado com %d instância(s) com erro: %s",
                config.id,
                len(instances_with_errors),
                [r["instance_name"] for r in instances_with_errors],
            )

    except Exception as exc:
        logger.exception("Erro ao gerar relatório config=%s: %s", config.id, exc)
        history.status = "error"
        history.error_message = str(exc)

    await db.commit()
    await db.refresh(history)
    return history


# ─── Limpeza de arquivos antigos ──────────────────────────────────────────────

async def purge_old_reports(db: AsyncSession) -> int:
    """
    Remove arquivos de relatório mais antigos que REPORT_RETENTION_DAYS.
    Retorna quantidade de arquivos removidos.
    """
    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=settings.report_retention_days)
    result = await db.execute(
        select(ReportHistory).where(
            ReportHistory.generated_at < cutoff,
            ReportHistory.file_path.isnot(None),
        )
    )
    old_entries = result.scalars().all()
    removed = 0

    for entry in old_entries:
        try:
            path = Path(entry.file_path)
            if path.exists():
                path.unlink()
                removed += 1
        except OSError as e:
            logger.warning("Não foi possível remover %s: %s", entry.file_path, e)

        entry.file_path = None
        entry.file_url = None

    if removed:
        await db.commit()
        logger.info("Limpeza: %d relatórios antigos removidos", removed)

    return removed
