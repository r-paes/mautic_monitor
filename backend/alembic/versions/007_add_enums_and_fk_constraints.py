"""Converte campos String para PostgreSQL ENUM e adiciona FK avant_sms_logs → avant_cost_centers

ENUMs criados:
  - alert_severity: info, warning, critical
  - notification_channel: email, sms, both
  - container_status: running, stopped, restarting, error, unknown
  - log_level: info, warning, error, critical
  - report_trigger: scheduled, manual
  - report_status: pending, generating, success, error
  - avant_sms_status: PENDING, DELIVRD, UNDELIV, EXPIRED, UNKNOWN, REJECTD

FK adicionada:
  - avant_sms_logs.cost_center_code → avant_cost_centers.code (ON DELETE SET NULL)

Revision ID: 007
Revises: 006
Create Date: 2026-04-06
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Criar tipos ENUM ─────────────────────────────────────────────────────
    alert_severity = sa.Enum("info", "warning", "critical", name="alert_severity")
    alert_severity.create(op.get_bind(), checkfirst=True)

    notification_channel = sa.Enum("email", "sms", "both", name="notification_channel")
    notification_channel.create(op.get_bind(), checkfirst=True)

    container_status = sa.Enum("running", "stopped", "restarting", "error", "unknown", name="container_status")
    container_status.create(op.get_bind(), checkfirst=True)

    log_level = sa.Enum("info", "warning", "error", "critical", name="log_level")
    log_level.create(op.get_bind(), checkfirst=True)

    report_trigger = sa.Enum("scheduled", "manual", name="report_trigger")
    report_trigger.create(op.get_bind(), checkfirst=True)

    report_status = sa.Enum("pending", "generating", "success", "error", name="report_status")
    report_status.create(op.get_bind(), checkfirst=True)

    avant_sms_status = sa.Enum("PENDING", "DELIVRD", "UNDELIV", "EXPIRED", "UNKNOWN", "REJECTD", name="avant_sms_status")
    avant_sms_status.create(op.get_bind(), checkfirst=True)

    # ── Converter colunas existentes: String → ENUM ──────────────────────────
    # alerts.severity
    op.execute("ALTER TABLE alerts ALTER COLUMN severity TYPE alert_severity USING severity::alert_severity")
    # alerts.notified_via
    op.execute("ALTER TABLE alerts ALTER COLUMN notified_via TYPE notification_channel USING notified_via::notification_channel")

    # service_status.status
    op.execute("ALTER TABLE service_status ALTER COLUMN status TYPE container_status USING status::container_status")

    # service_logs.log_level
    op.execute("ALTER TABLE service_logs ALTER COLUMN log_level TYPE log_level USING log_level::log_level")

    # report_history.trigger
    op.execute("ALTER TABLE report_history ALTER COLUMN trigger TYPE report_trigger USING trigger::report_trigger")
    # report_history.status
    op.execute("ALTER TABLE report_history ALTER COLUMN status TYPE report_status USING status::report_status")

    # avant_sms_logs.status
    op.execute("ALTER TABLE avant_sms_logs ALTER COLUMN status TYPE avant_sms_status USING status::avant_sms_status")

    # ── FK: avant_sms_logs.cost_center_code → avant_cost_centers.code ────────
    op.create_foreign_key(
        "fk_avant_sms_logs_cost_center",
        "avant_sms_logs",
        "avant_cost_centers",
        ["cost_center_code"],
        ["code"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    # ── Remover FK ───────────────────────────────────────────────────────────
    op.drop_constraint("fk_avant_sms_logs_cost_center", "avant_sms_logs", type_="foreignkey")

    # ── Reverter ENUM → String ───────────────────────────────────────────────
    op.execute("ALTER TABLE avant_sms_logs ALTER COLUMN status TYPE VARCHAR(20) USING status::text")
    op.execute("ALTER TABLE report_history ALTER COLUMN status TYPE VARCHAR(20) USING status::text")
    op.execute("ALTER TABLE report_history ALTER COLUMN trigger TYPE VARCHAR(20) USING trigger::text")
    op.execute("ALTER TABLE service_logs ALTER COLUMN log_level TYPE VARCHAR(20) USING log_level::text")
    op.execute("ALTER TABLE service_status ALTER COLUMN status TYPE VARCHAR(30) USING status::text")
    op.execute("ALTER TABLE alerts ALTER COLUMN notified_via TYPE VARCHAR(20) USING notified_via::text")
    op.execute("ALTER TABLE alerts ALTER COLUMN severity TYPE VARCHAR(20) USING severity::text")

    # ── Remover tipos ENUM ───────────────────────────────────────────────────
    sa.Enum(name="avant_sms_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="report_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="report_trigger").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="log_level").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="container_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="notification_channel").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="alert_severity").drop(op.get_bind(), checkfirst=True)
