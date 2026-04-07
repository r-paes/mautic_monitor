"""Adiciona colunas de chave SSH gerada automaticamente nas instâncias

Revision ID: 003
Revises: 002
Create Date: 2026-03-30
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "instances",
        sa.Column("ssh_private_key_enc", sa.Text(), nullable=True),
    )
    op.add_column(
        "instances",
        sa.Column("ssh_public_key", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("instances", "ssh_public_key")
    op.drop_column("instances", "ssh_private_key_enc")
