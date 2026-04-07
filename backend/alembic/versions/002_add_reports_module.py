"""Módulo de relatórios — report_configs e report_history (hypertable)

Revision ID: 002
Revises: 001
Create Date: 2026-03-28
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── report_configs ─────────────────────────────────────────────────────
    op.create_table(
        "report_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("instance_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("instances.id", ondelete="CASCADE"), nullable=False),
        sa.Column("company_name", sa.String(200), nullable=False),
        sa.Column("mautic_company_id", sa.Integer(), nullable=True),
        sa.Column("report_email", sa.String(255), nullable=False),
        sa.Column("report_phone", sa.String(20), nullable=True),
        sa.Column("send_email", sa.Boolean(), server_default="true"),
        sa.Column("send_sms", sa.Boolean(), server_default="false"),
        sa.Column("active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_report_configs_instance_id", "report_configs", ["instance_id"])

    # ── report_history (hypertable em generated_at) ────────────────────────
    # TimescaleDB exige que a coluna de particionamento esteja na PK
    op.create_table(
        "report_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("report_config_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("report_configs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("instance_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("instances.id", ondelete="SET NULL"), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.func.now()),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("trigger", sa.String(20), nullable=False),   # scheduled | manual
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("file_path", sa.String(500), nullable=True),
        sa.Column("file_url", sa.String(500), nullable=True),
        sa.Column("email_stats_json", postgresql.JSONB(), nullable=True),
        sa.Column("sms_stats_json", postgresql.JSONB(), nullable=True),
        sa.Column("sent_email", sa.Boolean(), server_default="false"),
        sa.Column("sent_sms", sa.Boolean(), server_default="false"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id", "generated_at"),
    )

    # Índices
    op.create_index("ix_report_history_generated_at", "report_history", ["generated_at"])
    op.create_index("ix_report_history_config_instance",
                    "report_history", ["report_config_id", "instance_id"])

    # Configura como TimescaleDB hypertable (chunk de 7 dias)
    op.execute(
        "SELECT create_hypertable('report_history', 'generated_at', "
        "chunk_time_interval => INTERVAL '7 days', if_not_exists => TRUE);"
    )


def downgrade() -> None:
    op.drop_table("report_history")
    op.drop_table("report_configs")
