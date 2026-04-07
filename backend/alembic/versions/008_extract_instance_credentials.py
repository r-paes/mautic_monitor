"""Extrai credenciais de API, MySQL e SSH da tabela instances para tabelas dedicadas

Cria: instance_api_credentials, instance_db_credentials, instance_ssh_credentials
Migra dados existentes e remove colunas da tabela instances.

Revision ID: 008
Revises: 007
Create Date: 2026-04-06
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Criar tabelas de credenciais ─────────────────────────────────────────

    op.create_table(
        "instance_api_credentials",
        sa.Column("instance_id", UUID(as_uuid=True), sa.ForeignKey("instances.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("username", sa.String(100), nullable=False),
        sa.Column("password_enc", sa.Text(), nullable=False),
    )

    op.create_table(
        "instance_db_credentials",
        sa.Column("instance_id", UUID(as_uuid=True), sa.ForeignKey("instances.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("host", sa.String(255), nullable=False),
        sa.Column("port", sa.Integer(), nullable=False, server_default="3306"),
        sa.Column("dbname", sa.String(100), nullable=False),
        sa.Column("username", sa.String(100), nullable=False),
        sa.Column("password_enc", sa.Text(), nullable=False),
    )

    op.create_table(
        "instance_ssh_credentials",
        sa.Column("instance_id", UUID(as_uuid=True), sa.ForeignKey("instances.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("host", sa.String(255), nullable=False),
        sa.Column("port", sa.Integer(), nullable=False, server_default="22"),
        sa.Column("username", sa.String(100), nullable=False, server_default="root"),
        sa.Column("key_path", sa.String(500), nullable=True),
        sa.Column("private_key_enc", sa.Text(), nullable=True),
        sa.Column("public_key", sa.Text(), nullable=True),
    )

    # ── Migrar dados existentes ──────────────────────────────────────────────

    # API credentials (todos os instances têm api_user obrigatório)
    op.execute("""
        INSERT INTO instance_api_credentials (instance_id, username, password_enc)
        SELECT id, api_user, api_password_enc
        FROM instances
        WHERE api_user IS NOT NULL
    """)

    # DB credentials (apenas instances com db_host configurado)
    op.execute("""
        INSERT INTO instance_db_credentials (instance_id, host, port, dbname, username, password_enc)
        SELECT id, db_host, COALESCE(db_port, 3306), COALESCE(db_name, ''), COALESCE(db_user, ''), COALESCE(db_password_enc, '')
        FROM instances
        WHERE db_host IS NOT NULL
    """)

    # SSH credentials (apenas instances com ssh_host configurado)
    op.execute("""
        INSERT INTO instance_ssh_credentials (instance_id, host, port, username, key_path, private_key_enc, public_key)
        SELECT id, ssh_host, COALESCE(ssh_port, 22), COALESCE(ssh_user, 'root'), ssh_key_path, ssh_private_key_enc, ssh_public_key
        FROM instances
        WHERE ssh_host IS NOT NULL
    """)

    # ── Remover colunas antigas da tabela instances ──────────────────────────

    op.drop_column("instances", "api_user")
    op.drop_column("instances", "api_password_enc")
    op.drop_column("instances", "db_host")
    op.drop_column("instances", "db_port")
    op.drop_column("instances", "db_name")
    op.drop_column("instances", "db_user")
    op.drop_column("instances", "db_password_enc")
    op.drop_column("instances", "ssh_host")
    op.drop_column("instances", "ssh_port")
    op.drop_column("instances", "ssh_user")
    op.drop_column("instances", "ssh_key_path")
    op.drop_column("instances", "ssh_private_key_enc")
    op.drop_column("instances", "ssh_public_key")


def downgrade() -> None:
    # ── Recriar colunas na tabela instances ──────────────────────────────────

    op.add_column("instances", sa.Column("api_user", sa.String(100), nullable=True))
    op.add_column("instances", sa.Column("api_password_enc", sa.Text(), nullable=True))
    op.add_column("instances", sa.Column("db_host", sa.String(255), nullable=True))
    op.add_column("instances", sa.Column("db_port", sa.Integer(), server_default="3306"))
    op.add_column("instances", sa.Column("db_name", sa.String(100), nullable=True))
    op.add_column("instances", sa.Column("db_user", sa.String(100), nullable=True))
    op.add_column("instances", sa.Column("db_password_enc", sa.Text(), nullable=True))
    op.add_column("instances", sa.Column("ssh_host", sa.String(255), nullable=True))
    op.add_column("instances", sa.Column("ssh_port", sa.Integer(), server_default="22"))
    op.add_column("instances", sa.Column("ssh_user", sa.String(100), nullable=True))
    op.add_column("instances", sa.Column("ssh_key_path", sa.String(500), nullable=True))
    op.add_column("instances", sa.Column("ssh_private_key_enc", sa.Text(), nullable=True))
    op.add_column("instances", sa.Column("ssh_public_key", sa.Text(), nullable=True))

    # ── Restaurar dados ──────────────────────────────────────────────────────

    op.execute("""
        UPDATE instances SET
            api_user = ac.username,
            api_password_enc = ac.password_enc
        FROM instance_api_credentials ac
        WHERE instances.id = ac.instance_id
    """)

    op.execute("""
        UPDATE instances SET
            db_host = dc.host,
            db_port = dc.port,
            db_name = dc.dbname,
            db_user = dc.username,
            db_password_enc = dc.password_enc
        FROM instance_db_credentials dc
        WHERE instances.id = dc.instance_id
    """)

    op.execute("""
        UPDATE instances SET
            ssh_host = sc.host,
            ssh_port = sc.port,
            ssh_user = sc.username,
            ssh_key_path = sc.key_path,
            ssh_private_key_enc = sc.private_key_enc,
            ssh_public_key = sc.public_key
        FROM instance_ssh_credentials sc
        WHERE instances.id = sc.instance_id
    """)

    # ── Remover tabelas de credenciais ────────────────────────────────────────

    op.drop_table("instance_ssh_credentials")
    op.drop_table("instance_db_credentials")
    op.drop_table("instance_api_credentials")
