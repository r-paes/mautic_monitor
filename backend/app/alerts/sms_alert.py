"""
alerts/sms_alert.py — Envio de alertas por SMS via Avant SMS API.
Usado apenas para alertas CRITICAL.
"""

import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# Template de mensagem SMS — conciso por limitação de caracteres
SMS_MESSAGE_TEMPLATE = "[SpaceCRM] {severity}: {alert_type} — {message_short}"
SMS_MAX_MESSAGE_LENGTH = 160

AVANT_SEND_ENDPOINT = "/sms/send"


async def send_alert_sms(
    to_phone: str,
    severity: str,
    alert_type: str,
    message: str,
) -> bool:
    """Envia SMS de alerta via Avant SMS API."""
    severity_label = "CRITICO" if severity == "critical" else "ATENCAO"

    # Trunca mensagem para caber no SMS
    max_msg_len = SMS_MAX_MESSAGE_LENGTH - len(f"[SpaceCRM] {severity_label}: {alert_type} — ")
    message_short = message[:max_msg_len] if len(message) > max_msg_len else message

    sms_text = SMS_MESSAGE_TEMPLATE.format(
        severity=severity_label,
        alert_type=alert_type,
        message_short=message_short,
    )

    headers = {
        "Authorization": f"Bearer {settings.avant_sms_token}",
        "Content-Type": "application/json",
    }

    payload = {
        "to": to_phone,
        "from": settings.avant_sms_alert_from,
        "message": sms_text,
    }

    try:
        async with httpx.AsyncClient(
            base_url=settings.avant_sms_api_base_url.rstrip("/"),
            headers=headers,
            timeout=settings.mautic_timeout_seconds,
        ) as client:
            resp = await client.post(AVANT_SEND_ENDPOINT, json=payload)
            resp.raise_for_status()
            logger.info("SMS de alerta enviado para %s (%s)", to_phone, alert_type)
            return True
    except Exception as e:
        logger.error("Falha ao enviar SMS de alerta para %s: %s", to_phone, e)
        return False
