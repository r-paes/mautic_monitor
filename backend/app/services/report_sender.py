"""
report_sender.py — Envio de relatórios por e-mail (Sendpost) e SMS (Avant).

Credenciais são lidas do banco (gateway_configs) com fallback para .env.
Cada função retorna True em caso de sucesso ou False em caso de falha,
registrando o erro no logger para rastreabilidade sem lançar exceções.
"""

import logging
from pathlib import Path

import httpx

from app.config import settings
from app.collectors.avant_sms import AVANT_SEND_URL
from app.models.reports import ReportConfig, ReportHistory

logger = logging.getLogger(__name__)

# ─── Timeouts ─────────────────────────────────────────────────────────────────

_HTTP_TIMEOUT = httpx.Timeout(30.0, connect=10.0)


# ─── E-mail via Sendpost ──────────────────────────────────────────────────────

async def send_report_email(
    config: ReportConfig,
    history: ReportHistory,
    api_key: str | None = None,
    from_email: str | None = None,
) -> bool:
    """
    Envia o relatório HTML por e-mail via API Sendpost.

    O arquivo HTML é embutido diretamente no corpo do e-mail (inline).
    Retorna True se enviado com sucesso.
    """
    if not config.send_email or not config.report_email:
        return False

    if not history.file_path or history.status != "success":
        logger.warning(
            "send_report_email: relatório %s não está disponível (status=%s)",
            history.id,
            history.status,
        )
        return False

    try:
        html_content = Path(history.file_path).read_text(encoding="utf-8")
    except OSError as e:
        logger.error("Não foi possível ler arquivo %s: %s", history.file_path, e)
        return False

    sendpost_key = api_key or settings.sendpost_api_key
    sendpost_from = from_email or settings.sendpost_alert_from_email

    period_label = history.period_start.strftime("%d/%m/%Y")
    subject = f"Relatório Mautic — {config.company_name} — {period_label}"

    payload = {
        "from": {
            "email": sendpost_from,
            "name": settings.sendpost_alert_from_name,
        },
        "to": [{"email": config.report_email}],
        "subject": subject,
        "htmlBody": html_content,
    }

    try:
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            response = await client.post(
                f"{settings.sendpost_api_base_url}/subaccount/email/",
                json=payload,
                headers={
                    "X-SubAccount-ApiKey": sendpost_key,
                    "Content-Type": "application/json",
                },
            )
            response.raise_for_status()

        logger.info(
            "E-mail enviado: %s → %s (relatório %s)",
            config.company_name,
            config.report_email,
            history.id,
        )
        return True

    except httpx.HTTPStatusError as e:
        logger.error(
            "Sendpost retornou erro %d para %s: %s",
            e.response.status_code,
            config.report_email,
            e.response.text[:300],
        )
    except httpx.RequestError as e:
        logger.error("Falha de conexão com Sendpost: %s", e)

    return False


# ─── SMS via Avant ────────────────────────────────────────────────────────────

async def send_report_sms(
    config: ReportConfig,
    history: ReportHistory,
    token: str | None = None,
) -> bool:
    """
    Envia notificação SMS via API Avant informando que o relatório está disponível.

    Avant não suporta links longos no corpo — envia um resumo compacto.
    Retorna True se enviado com sucesso.
    """
    if not config.send_sms or not config.report_phone:
        return False

    if history.status != "success":
        return False

    email_stats = history.email_stats_json or {}
    period_label = history.period_start.strftime("%d/%m")

    # Mensagem compacta (max ~160 chars para SMS simples)
    sent = email_stats.get("total_sent", 0)
    opened = email_stats.get("total_opened", 0)
    message = (
        f"Space CRM | {config.company_name} | {period_label}: "
        f"{sent} emails enviados, {opened} abertos. "
        f"Acesse o painel para ver o relatorio completo."
    )

    sms_token = token or settings.avant_sms_token

    payload = {
        "recipient": config.report_phone,
        "message": {"text": message},
        "costCenterCode": settings.avant_sms_alert_from,
    }

    try:
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            response = await client.post(
                AVANT_SEND_URL,
                json=payload,
                headers={
                    "Authorization": f"alpha {sms_token}",
                    "Content-Type": "application/json",
                },
            )
            response.raise_for_status()

        logger.info(
            "SMS enviado: %s → %s (relatório %s)",
            config.company_name,
            config.report_phone,
            history.id,
        )
        return True

    except httpx.HTTPStatusError as e:
        logger.error(
            "Avant retornou erro %d para %s: %s",
            e.response.status_code,
            config.report_phone,
            e.response.text[:300],
        )
    except httpx.RequestError as e:
        logger.error("Falha de conexão com Avant: %s", e)

    return False


# ─── Orquestrador ─────────────────────────────────────────────────────────────

async def dispatch_report(
    config: ReportConfig,
    history: ReportHistory,
    sendpost_api_key: str | None = None,
    sendpost_from_email: str | None = None,
    avant_token: str | None = None,
) -> tuple[bool, bool]:
    """
    Envia relatório pelos canais configurados (email e/ou SMS).

    Retorna:
        (email_sent, sms_sent): bool para cada canal.
    """
    email_sent = False
    sms_sent = False

    if config.send_email:
        email_sent = await send_report_email(
            config, history,
            api_key=sendpost_api_key,
            from_email=sendpost_from_email,
        )

    if config.send_sms:
        sms_sent = await send_report_sms(
            config, history,
            token=avant_token,
        )

    return email_sent, sms_sent
