"""Adiciona tabelas avant_cost_centers e avant_sms_logs

Revision ID: 005
Revises: 004
Create Date: 2026-04-06
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Tabela de correlação costCenterCode → cliente
    op.create_table(
        "avant_cost_centers",
        sa.Column("code", sa.String(100), primary_key=True),
        sa.Column("client_name", sa.String(255), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # Log de eventos DLR (delivery receipts) via webhook
    op.create_table(
        "avant_sms_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("avant_message_id", sa.String(255), nullable=False, unique=True),
        sa.Column("cost_center_code", sa.String(100), nullable=True),
        sa.Column("recipient", sa.String(50), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'PENDING'")),
        sa.Column("error_code", sa.String(50), nullable=True),
        sa.Column(
            "sent_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("raw_payload", sa.String(2000), nullable=True),
    )

    op.create_index("ix_avant_sms_logs_sent_at", "avant_sms_logs", ["sent_at"])
    op.create_index("ix_avant_sms_logs_cost_center", "avant_sms_logs", ["cost_center_code"])
    op.create_index("ix_avant_sms_logs_avant_id", "avant_sms_logs", ["avant_message_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_avant_sms_logs_avant_id", table_name="avant_sms_logs")
    op.drop_index("ix_avant_sms_logs_cost_center", table_name="avant_sms_logs")
    op.drop_index("ix_avant_sms_logs_sent_at", table_name="avant_sms_logs")
    op.drop_table("avant_sms_logs")
    op.drop_table("avant_cost_centers")
