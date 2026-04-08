"""012 — Migra VPS de SSH para EasyPanel API.

Remove campos SSH (host, ssh_port, ssh_user, private_key_enc, public_key).
Adiciona campos EasyPanel (easypanel_url, api_key_enc).
"""

from alembic import op
import sqlalchemy as sa


revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Adicionar novos campos EasyPanel
    op.add_column("vps_servers", sa.Column("easypanel_url", sa.String(255), nullable=True))
    op.add_column("vps_servers", sa.Column("api_key_enc", sa.Text(), nullable=True))

    # Migrar dados: usar host como base para easypanel_url
    op.execute(
        "UPDATE vps_servers SET easypanel_url = 'https://' || host WHERE easypanel_url IS NULL"
    )

    # Tornar easypanel_url NOT NULL após preencher
    op.alter_column("vps_servers", "easypanel_url", nullable=False)

    # Remover campos SSH
    op.drop_column("vps_servers", "ssh_port")
    op.drop_column("vps_servers", "ssh_user")
    op.drop_column("vps_servers", "private_key_enc")
    op.drop_column("vps_servers", "public_key")
    op.drop_column("vps_servers", "host")

    # Atualizar scheduler_configs key
    op.execute(
        "UPDATE scheduler_configs SET config_key = 'vps_interval', "
        "description = 'Métricas de VPS + containers via EasyPanel (minutos)' "
        "WHERE config_key = 'vps_ssh_interval'"
    )


def downgrade() -> None:
    # Restaurar campos SSH
    op.add_column("vps_servers", sa.Column("host", sa.String(255), nullable=True))
    op.add_column("vps_servers", sa.Column("ssh_port", sa.Integer(), server_default="22"))
    op.add_column("vps_servers", sa.Column("ssh_user", sa.String(100), server_default="root"))
    op.add_column("vps_servers", sa.Column("private_key_enc", sa.Text(), nullable=True))
    op.add_column("vps_servers", sa.Column("public_key", sa.Text(), nullable=True))

    # Migrar dados de volta
    op.execute(
        "UPDATE vps_servers SET host = REPLACE(REPLACE(easypanel_url, 'https://', ''), 'http://', '')"
    )
    op.alter_column("vps_servers", "host", nullable=False)

    # Reverter scheduler_configs key
    op.execute(
        "UPDATE scheduler_configs SET config_key = 'vps_ssh_interval', "
        "description = 'Métricas de VPS + containers via SSH (minutos)' "
        "WHERE config_key = 'vps_interval'"
    )

    # Remover campos EasyPanel
    op.drop_column("vps_servers", "api_key_enc")
    op.drop_column("vps_servers", "easypanel_url")
