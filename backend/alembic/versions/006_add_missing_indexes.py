"""Adiciona índices faltantes em alerts.instance_id e avant_sms_logs.status

Revision ID: 006
Revises: 005
Create Date: 2026-04-06
"""

from typing import Sequence, Union
from alembic import op

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("ix_alerts_instance_id", "alerts", ["instance_id"])
    op.create_index("ix_avant_sms_logs_status", "avant_sms_logs", ["status"])


def downgrade() -> None:
    op.drop_index("ix_avant_sms_logs_status", table_name="avant_sms_logs")
    op.drop_index("ix_alerts_instance_id", table_name="alerts")
