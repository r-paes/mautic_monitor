"""Schema inicial — todas as tabelas do projeto (exceto módulo de relatórios)

Revision ID: 001
Revises: —
Create Date: 2026-03-28
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Extensões necessárias
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;")
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')

    # ── users ──────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("alert_email", sa.String(255), nullable=True),
        sa.Column("alert_phone", sa.String(20), nullable=True),
        sa.Column("role", sa.String(20), server_default="operator"),
        sa.Column("active", sa.Boolean(), server_default="true"),
        sa.Column("last_login", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # ── instances ──────────────────────────────────────────────────────────
    op.create_table(
        "instances",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("url", sa.String(255), nullable=False),
        sa.Column("api_user", sa.String(100), nullable=False),
        sa.Column("api_password_enc", sa.Text(), nullable=False),
        sa.Column("db_host", sa.String(255), nullable=True),
        sa.Column("db_port", sa.Integer(), server_default="3306"),  # MySQL default
        sa.Column("db_name", sa.String(100), nullable=True),
        sa.Column("db_user", sa.String(100), nullable=True),
        sa.Column("db_password_enc", sa.Text(), nullable=True),
        sa.Column("ssh_host", sa.String(255), nullable=True),
        sa.Column("ssh_port", sa.Integer(), server_default="22"),
        sa.Column("ssh_user", sa.String(100), nullable=True),
        sa.Column("ssh_key_path", sa.String(500), nullable=True),
        sa.Column("active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── companies ──────────────────────────────────────────────────────────
    op.create_table(
        "companies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("instance_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("instances.id", ondelete="CASCADE"), nullable=False),
        sa.Column("mautic_segment_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_companies_instance_id", "companies", ["instance_id"])

    # ── alerts ─────────────────────────────────────────────────────────────
    op.create_table(
        "alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("instance_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("instances.id", ondelete="SET NULL"), nullable=True),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("notified_via", sa.String(20), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("acked_by", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_index("ix_alerts_severity", "alerts", ["severity"])
    op.create_index("ix_alerts_type", "alerts", ["type"])
    op.create_index("ix_alerts_created_at", "alerts", ["created_at"])

    # ── health_metrics (hypertable) ────────────────────────────────────────
    # TimescaleDB exige que a coluna de particionamento (time) esteja na PK
    op.create_table(
        "health_metrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("time", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("instance_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("instances.id", ondelete="CASCADE"), nullable=False),
        sa.Column("new_contacts", sa.Integer(), nullable=True),
        sa.Column("active_campaigns", sa.Integer(), nullable=True),
        sa.Column("emails_queued", sa.Integer(), nullable=True),
        sa.Column("emails_sent_mautic", sa.Integer(), nullable=True),
        sa.Column("sms_sent_mautic", sa.Integer(), nullable=True),
        sa.Column("api_response_ms", sa.Integer(), nullable=True),
        sa.Column("db_response_ms", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(20), server_default="ok"),
        sa.PrimaryKeyConstraint("id", "time"),
    )
    op.create_index("ix_health_metrics_time", "health_metrics", ["time"])
    op.create_index("ix_health_metrics_time_instance",
                    "health_metrics", ["time", "instance_id"])
    op.execute(
        "SELECT create_hypertable('health_metrics', 'time', "
        "chunk_time_interval => INTERVAL '1 day', if_not_exists => TRUE);"
    )

    # ── gateway_metrics (hypertable) ──────────────────────────────────────
    op.create_table(
        "gateway_metrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("time", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("gateway_type", sa.String(30), nullable=False),
        sa.Column("emails_sent", sa.Integer(), nullable=True),
        sa.Column("emails_delivered", sa.Integer(), nullable=True),
        sa.Column("emails_bounced", sa.Integer(), nullable=True),
        sa.Column("emails_spam", sa.Integer(), nullable=True),
        sa.Column("emails_unsubscribed", sa.Integer(), nullable=True),
        sa.Column("open_rate", sa.Float(), nullable=True),
        sa.Column("click_rate", sa.Float(), nullable=True),
        sa.Column("sms_sent", sa.Integer(), nullable=True),
        sa.Column("sms_delivered", sa.Integer(), nullable=True),
        sa.Column("sms_failed", sa.Integer(), nullable=True),
        sa.Column("balance_credits", sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint("id", "time"),
    )
    op.create_index("ix_gateway_metrics_time", "gateway_metrics", ["time"])
    op.create_index("ix_gateway_metrics_time_type",
                    "gateway_metrics", ["time", "gateway_type"])
    op.execute(
        "SELECT create_hypertable('gateway_metrics', 'time', "
        "chunk_time_interval => INTERVAL '1 day', if_not_exists => TRUE);"
    )

    # ── vps_metrics (hypertable) ───────────────────────────────────────────
    op.create_table(
        "vps_metrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("time", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("instance_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("instances.id", ondelete="CASCADE"), nullable=False),
        sa.Column("cpu_percent", sa.Float(), nullable=True),
        sa.Column("memory_percent", sa.Float(), nullable=True),
        sa.Column("memory_used_mb", sa.Integer(), nullable=True),
        sa.Column("memory_total_mb", sa.Integer(), nullable=True),
        sa.Column("disk_percent", sa.Float(), nullable=True),
        sa.Column("disk_used_gb", sa.Float(), nullable=True),
        sa.Column("disk_total_gb", sa.Float(), nullable=True),
        sa.Column("load_avg_1m", sa.Float(), nullable=True),
        sa.Column("load_avg_5m", sa.Float(), nullable=True),
        sa.Column("load_avg_15m", sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint("id", "time"),
    )
    op.create_index("ix_vps_metrics_time", "vps_metrics", ["time"])
    op.create_index("ix_vps_metrics_time_instance", "vps_metrics", ["time", "instance_id"])
    op.execute(
        "SELECT create_hypertable('vps_metrics', 'time', "
        "chunk_time_interval => INTERVAL '1 day', if_not_exists => TRUE);"
    )

    # ── service_status (hypertable) ────────────────────────────────────────
    op.create_table(
        "service_status",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("time", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("instance_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("instances.id", ondelete="CASCADE"), nullable=False),
        sa.Column("container_name", sa.String(200), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("uptime_seconds", sa.Integer(), nullable=True),
        sa.Column("restart_count", sa.Integer(), nullable=True),
        sa.Column("image", sa.String(300), nullable=True),
        sa.PrimaryKeyConstraint("id", "time"),
    )
    op.create_index("ix_service_status_time", "service_status", ["time"])
    op.create_index("ix_service_status_time_instance",
                    "service_status", ["time", "instance_id"])
    op.execute(
        "SELECT create_hypertable('service_status', 'time', "
        "chunk_time_interval => INTERVAL '1 day', if_not_exists => TRUE);"
    )

    # ── service_logs ───────────────────────────────────────────────────────
    op.create_table(
        "service_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("instance_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("instances.id", ondelete="CASCADE"), nullable=False),
        sa.Column("container_name", sa.String(200), nullable=False),
        sa.Column("log_level", sa.String(20), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("pattern_matched", sa.String(100), nullable=True),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_service_logs_captured_at", "service_logs", ["captured_at"])
    op.create_index("ix_service_logs_instance_captured",
                    "service_logs", ["instance_id", "captured_at"])


def downgrade() -> None:
    op.drop_table("service_logs")
    op.drop_table("service_status")
    op.drop_table("vps_metrics")
    op.drop_table("gateway_metrics")
    op.drop_table("health_metrics")
    op.drop_table("alerts")
    op.drop_table("companies")
    op.drop_table("instances")
    op.drop_table("users")
