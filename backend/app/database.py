"""
database.py — Configuração SQLAlchemy async + TimescaleDB.
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

# Engine assíncrono
engine = create_async_engine(
    settings.database_url,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_timeout=settings.db_pool_timeout,
    echo=settings.db_echo,
    pool_pre_ping=True,
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """Base para todos os modelos SQLAlchemy."""
    pass


async def get_db() -> AsyncSession:
    """Dependency injection para obter sessão de banco de dados."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def create_tables() -> None:
    """Cria todas as tabelas (usado apenas em dev/teste)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def enable_timescaledb_extensions(conn) -> None:
    """Habilita extensões TimescaleDB necessárias."""
    await conn.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;")
