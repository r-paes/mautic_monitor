"""Separa VPS de Instâncias: cria vps_servers, instance_services, scheduler_configs

- Cria tabela vps_servers (entidade independente com SSH credentials)
- Cria tabela instance_services (containers monitorados por instância)
- Cria tabela scheduler_configs (intervalos de coleta editáveis via UI)
- Migra dados de instance_ssh_credentials → vps_servers
- Adiciona vps_id em instances, vps_metrics, service_status, service_logs
- Remove instance_id de vps_metrics (agora usa vps_id)
- Remove tabela instance_ssh_credentials

Revision ID: 010
Revises: 009
Create Date: 2026-04-07
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "010"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. Criar tabela vps_servers ─────────────────────────────────────────

    op.create_table(
        "vps_servers",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("host", sa.String(255), nullable=False),
        sa.Column("ssh_port", sa.Integer(), nullable=False, server_default="22"),
        sa.Column("ssh_user", sa.String(100), nullable=False, server_default="root"),
        sa.Column("private_key_enc", sa.Text(), nullable=True),
        sa.Column("public_key", sa.Text(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── 2. Criar ENUM service_type e tabela instance_services ───────────────

    # Cria ENUM e tabela via SQL puro para evitar problemas do SQLAlchemy com asyncpg
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE service_type AS ENUM ('database', 'crons', 'web');
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END $$
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS instance_services (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            instance_id UUID NOT NULL REFERENCES instances(id) ON DELETE CASCADE,
            service_type service_type NOT NULL,
            container_name VARCHAR(200) NOT NULL,
            active BOOLEAN NOT NULL DEFAULT true,
            created_at TIMESTAMPTZ DEFAULT now()
        )
    """)

    op.create_index("ix_instance_services_instance", "instance_services", ["instance_id"])

    # ── 3. Criar tabela scheduler_configs ───────────────────────────────────

    op.create_table(
        "scheduler_configs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("config_key", sa.String(50), unique=True, nullable=False),
        sa.Column("interval_minutes", sa.Integer(), nullable=False),
        sa.Column("description", sa.String(200), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Popula com valores default
    op.execute("""
        INSERT INTO scheduler_configs (config_key, interval_minutes, description) VALUES
        ('mautic_api_interval',    5,  'Coleta via REST API do Mautic (minutos)'),
        ('mautic_db_interval',     15, 'Coleta via MySQL direto do Mautic (minutos)'),
        ('vps_ssh_interval',       15, 'Métricas de VPS + containers via SSH (minutos)'),
        ('gateway_interval',       5,  'Coleta de gateways Sendpost/Avant (minutos)'),
        ('alert_engine_interval',  1,  'Avaliação do motor de alertas (minutos)')
    """)

    # ── 4. Migrar instance_ssh_credentials → vps_servers ────────────────────

    # Para cada SSH credential existente, cria um VpsServer e vincula à instância
    op.execute("""
        INSERT INTO vps_servers (id, name, host, ssh_port, ssh_user, private_key_enc, public_key, created_at, updated_at)
        SELECT
            gen_random_uuid(),
            i.name || ' — VPS',
            sc.host,
            sc.port,
            sc.username,
            sc.private_key_enc,
            sc.public_key,
            NOW(),
            NOW()
        FROM instance_ssh_credentials sc
        JOIN instances i ON i.id = sc.instance_id
    """)

    # ── 5. Adicionar vps_id em instances ────────────────────────────────────

    op.add_column("instances", sa.Column("vps_id", UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_instances_vps_id", "instances", "vps_servers",
        ["vps_id"], ["id"], ondelete="SET NULL"
    )

    # Vincular instâncias às VPS recém-criadas (match por host SSH)
    op.execute("""
        UPDATE instances i
        SET vps_id = v.id
        FROM instance_ssh_credentials sc
        JOIN vps_servers v ON v.host = sc.host
        WHERE i.id = sc.instance_id
    """)

    # ── 6. Adicionar vps_id em vps_metrics ──────────────────────────────────

    op.add_column("vps_metrics", sa.Column("vps_id", UUID(as_uuid=True), nullable=True))

    # Migrar: vps_metrics.instance_id → vps_id via instances.vps_id
    op.execute("""
        UPDATE vps_metrics vm
        SET vps_id = i.vps_id
        FROM instances i
        WHERE vm.instance_id = i.id AND i.vps_id IS NOT NULL
    """)

    # Remover coluna instance_id de vps_metrics (agora usa vps_id)
    # Primeiro dropar o index antigo
    op.drop_index("ix_vps_metrics_time_instance", table_name="vps_metrics")
    op.drop_column("vps_metrics", "instance_id")

    # Tornar vps_id NOT NULL após migração
    op.alter_column("vps_metrics", "vps_id", nullable=False)

    # Criar novo index
    op.create_index("ix_vps_metrics_time_vps", "vps_metrics", ["time", "vps_id"])

    # ── 7. Adicionar vps_id em service_status ───────────────────────────────

    op.add_column("service_status", sa.Column("vps_id", UUID(as_uuid=True), nullable=True))

    # Migrar: via instance_id → instances.vps_id
    op.execute("""
        UPDATE service_status ss
        SET vps_id = i.vps_id
        FROM instances i
        WHERE ss.instance_id = i.id AND i.vps_id IS NOT NULL
    """)

    op.create_index("ix_service_status_time_vps", "service_status", ["time", "vps_id"])

    # ── 8. Adicionar vps_id em service_logs ─────────────────────────────────

    op.add_column("service_logs", sa.Column("vps_id", UUID(as_uuid=True), nullable=True))

    # Migrar: via instance_id → instances.vps_id
    op.execute("""
        UPDATE service_logs sl
        SET vps_id = i.vps_id
        FROM instances i
        WHERE sl.instance_id = i.id AND i.vps_id IS NOT NULL
    """)

    op.create_index("ix_service_logs_vps_captured", "service_logs", ["vps_id", "captured_at"])

    # ── 9. Remover tabela instance_ssh_credentials ──────────────────────────

    op.drop_table("instance_ssh_credentials")


def downgrade() -> None:
    # ── Recriar instance_ssh_credentials ────────────────────────────────────

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

    # Restaurar SSH credentials das VPS
    op.execute("""
        INSERT INTO instance_ssh_credentials (instance_id, host, port, username, private_key_enc, public_key)
        SELECT i.id, v.host, v.ssh_port, v.ssh_user, v.private_key_enc, v.public_key
        FROM instances i
        JOIN vps_servers v ON v.id = i.vps_id
    """)

    # ── Remover vps_id de service_logs ──────────────────────────────────────

    op.drop_index("ix_service_logs_vps_captured", table_name="service_logs")
    op.drop_column("service_logs", "vps_id")

    # ── Remover vps_id de service_status ────────────────────────────────────

    op.drop_index("ix_service_status_time_vps", table_name="service_status")
    op.drop_column("service_status", "vps_id")

    # ── Restaurar instance_id em vps_metrics ────────────────────────────────

    op.add_column("vps_metrics", sa.Column("instance_id", UUID(as_uuid=True), nullable=True))
    op.drop_index("ix_vps_metrics_time_vps", table_name="vps_metrics")

    # Migrar vps_id → instance_id (pega primeira instância da VPS)
    op.execute("""
        UPDATE vps_metrics vm
        SET instance_id = (
            SELECT i.id FROM instances i WHERE i.vps_id = vm.vps_id LIMIT 1
        )
    """)

    op.create_index("ix_vps_metrics_time_instance", "vps_metrics", ["time", "instance_id"])
    op.drop_column("vps_metrics", "vps_id")

    # ── Remover vps_id de instances ─────────────────────────────────────────

    op.drop_constraint("fk_instances_vps_id", "instances", type_="foreignkey")
    op.drop_column("instances", "vps_id")

    # ── Remover tabelas novas ───────────────────────────────────────────────

    op.drop_table("scheduler_configs")
    op.drop_index("ix_instance_services_instance", table_name="instance_services")
    op.drop_table("instance_services")

    # Drop ENUM
    sa.Enum(name="service_type").drop(op.get_bind(), checkfirst=True)

    op.drop_table("vps_servers")
