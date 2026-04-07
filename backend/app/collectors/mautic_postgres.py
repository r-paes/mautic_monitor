"""
mautic_postgres.py — Coleta de dados via conexão direta ao banco PostgreSQL do Mautic.

Queries de leitura apenas. Fornece dados que a API REST não expõe:
fila de emails, histórico detalhado, estatísticas brutas.
"""

import logging
import time
from datetime import datetime, timedelta, timezone

import asyncpg

from app.config import settings

logger = logging.getLogger(__name__)

# Queries SQL — externalizadas como constantes para facilitar manutenção
QUERY_EMAIL_QUEUE = """
    SELECT COUNT(*) AS queued
    FROM email_stats
    WHERE is_failed = 0
      AND date_sent IS NULL
"""

QUERY_EMAILS_SENT_LAST_PERIOD = """
    SELECT COUNT(*) AS sent
    FROM email_stats
    WHERE is_failed = 0
      AND date_sent > NOW() - INTERVAL '{interval}'
"""

QUERY_SMS_SENT_LAST_PERIOD = """
    SELECT COUNT(*) AS sent
    FROM sms_messages
    WHERE date_sent > NOW() - INTERVAL '{interval}'
      AND status = 'sent'
"""

QUERY_NEW_CONTACTS_24H = """
    SELECT COUNT(*) AS total
    FROM leads
    WHERE date_added > NOW() - INTERVAL '24 hours'
      AND is_published = 1
"""


class MauticDBCollector:
    """Coleta métricas via conexão direta ao banco PostgreSQL do Mautic."""

    def __init__(self, host: str, port: int, dbname: str, user: str, password: str):
        # Parâmetros armazenados separadamente — nunca montar DSN string com senha
        # para evitar vazamento em logs e stack traces.
        self._host = host
        self._port = port
        self._dbname = dbname
        self._user = user
        self._password = password
        self.host = host  # mantido para uso em mensagens de log

    async def _connect(self):
        """Cria conexão asyncpg com timeout configurável."""
        return await asyncpg.connect(
            host=self._host,
            port=self._port,
            database=self._dbname,
            user=self._user,
            password=self._password,
            timeout=settings.mautic_timeout_seconds,
        )

    async def get_db_response_ms(self) -> int | None:
        """Mede latência de conexão ao banco."""
        start = time.monotonic()
        try:
            conn = await self._connect()
            await conn.fetchval("SELECT 1")
            await conn.close()
            return int((time.monotonic() - start) * 1000)
        except Exception as e:
            logger.warning("Erro ao medir latência DB %s: %s", self.host, e)
            return None

    async def get_email_queue_count(self) -> int | None:
        """Retorna número de emails na fila (não enviados, não falhados)."""
        try:
            conn = await self._connect()
            result = await conn.fetchval(QUERY_EMAIL_QUEUE)
            await conn.close()
            return int(result or 0)
        except Exception as e:
            logger.warning("Erro ao obter fila de emails: %s", e)
            return None

    async def get_emails_sent(self, interval: str = "1 hour") -> int | None:
        """Retorna emails enviados no intervalo especificado."""
        try:
            conn = await self._connect()
            query = QUERY_EMAILS_SENT_LAST_PERIOD.format(interval=interval)
            result = await conn.fetchval(query)
            await conn.close()
            return int(result or 0)
        except Exception as e:
            logger.warning("Erro ao obter emails enviados: %s", e)
            return None

    async def get_sms_sent(self, interval: str = "1 hour") -> int | None:
        """Retorna SMS enviados no intervalo especificado."""
        try:
            conn = await self._connect()
            query = QUERY_SMS_SENT_LAST_PERIOD.format(interval=interval)
            result = await conn.fetchval(query)
            await conn.close()
            return int(result or 0)
        except asyncpg.UndefinedTableError:
            # Instância pode não ter módulo SMS ativo
            logger.debug("Tabela sms_messages não encontrada em %s", self.host)
            return None
        except Exception as e:
            logger.warning("Erro ao obter SMS enviados: %s", e)
            return None

    async def collect(self) -> dict:
        """Executa todas as coletas e retorna snapshot consolidado."""
        db_response_ms = await self.get_db_response_ms()
        emails_queued = None
        emails_sent = None
        sms_sent = None

        if db_response_ms is not None:
            emails_queued = await self.get_email_queue_count()
            emails_sent = await self.get_emails_sent()
            sms_sent = await self.get_sms_sent()

        return {
            "db_response_ms": db_response_ms,
            "emails_queued": emails_queued,
            "emails_sent_mautic": emails_sent,
            "sms_sent_mautic": sms_sent,
        }
