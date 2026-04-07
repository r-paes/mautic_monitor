"""Adiciona tabela gateway_configs para credenciais de Sendpost e Avant SMS

Revision ID: 004
Revises: 003
Create Date: 2026-03-30
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "gateway_configs",
        sa.Column("key", sa.String(100), primary_key=True),
        sa.Column("value_enc", sa.Text(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("gateway_configs")
