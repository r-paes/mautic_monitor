"""
alerts/email_alert.py — Envio de alertas por email via Sendpost API.

Auth: Header X-SubAccount-ApiKey
"""

import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# Templates de email — centralizados aqui
EMAIL_SUBJECT_TEMPLATE = "[Space Monitor] {severity_label}: {alert_type}"

EMAIL_BODY_TEMPLATE = """
<html>
<body style="font-family: Inter, sans-serif; background: #F5EEE4; padding: 24px;">
  <div style="max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 10px; overflow: hidden; box-shadow: 0 2px 8px rgba(9,22,40,0.1);">
    <div style="background: {header_color}; padding: 20px 24px;">
      <h2 style="color: #ffffff; margin: 0; font-size: 18px;">
        {severity_emoji} Alerta {severity_label} — Space Monitor
      </h2>
    </div>
    <div style="padding: 24px;">
      <p style="color: #091628; font-size: 15px; margin: 0 0 16px 0;">
        <strong>Tipo:</strong> {alert_type}
      </p>
      <p style="color: #091628; font-size: 15px; margin: 0 0 16px 0;">
        <strong>Mensagem:</strong>
      </p>
      <div style="background: #f8f5ef; border-left: 4px solid {header_color}; padding: 12px 16px; border-radius: 4px;">
        <p style="color: #091628; font-size: 14px; margin: 0;">{message}</p>
      </div>
      <p style="color: #5a6a7e; font-size: 12px; margin: 24px 0 0 0;">
        Space Monitor — {domain}
      </p>
    </div>
  </div>
</body>
</html>
"""

SEVERITY_CONFIG = {
    "critical": {
        "label": "CRÍTICO",
        "emoji": "🚨",
        "color": "#e53e3e",
    },
    "warning": {
        "label": "ATENÇÃO",
        "emoji": "⚠️",
        "color": "#dd6b20",
    },
    "info": {
        "label": "INFO",
        "emoji": "ℹ️",
        "color": "#2F75B9",
    },
}

SENDPOST_EMAIL_ENDPOINT = "/subaccount/email"


async def send_alert_email(
    to_email: str,
    to_name: str,
    severity: str,
    alert_type: str,
    message: str,
    api_key: str | None = None,
    from_email: str | None = None,
) -> bool:
    """Envia email de alerta via Sendpost API."""
    config = SEVERITY_CONFIG.get(severity, SEVERITY_CONFIG["info"])

    sendpost_key = api_key or settings.sendpost_api_key
    sendpost_from = from_email or settings.sendpost_alert_from_email

    subject = EMAIL_SUBJECT_TEMPLATE.format(
        severity_label=config["label"],
        alert_type=alert_type,
    )

    html_body = EMAIL_BODY_TEMPLATE.format(
        severity_label=config["label"],
        severity_emoji=config["emoji"],
        header_color=config["color"],
        alert_type=alert_type,
        message=message,
        domain=settings.easypanel_domain,
    )

    payload = {
        "from": {
            "email": sendpost_from,
            "name": settings.sendpost_alert_from_name,
        },
        "to": [{"email": to_email, "name": to_name}],
        "subject": subject,
        "htmlBody": html_body,
    }

    headers = {
        "X-SubAccount-ApiKey": sendpost_key,
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(
            base_url=settings.sendpost_api_base_url.rstrip("/"),
            headers=headers,
            timeout=settings.mautic_timeout_seconds,
        ) as client:
            resp = await client.post(SENDPOST_EMAIL_ENDPOINT, json=payload)
            resp.raise_for_status()
            logger.info("Email de alerta enviado para %s (%s)", to_email, alert_type)
            return True
    except Exception as e:
        logger.error("Falha ao enviar email de alerta para %s: %s", to_email, e)
        return False
