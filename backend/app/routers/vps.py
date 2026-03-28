"""
routers/vps.py — Endpoints de métricas e logs de VPS.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.vps_metrics import VpsMetric, ServiceStatus, ServiceLog
from app.routers.auth import get_current_user
from app.models.users import User

router = APIRouter(prefix="/vps", tags=["vps"])


class VpsMetricOut(BaseModel):
    id: str
    time: datetime
    instance_id: str
    cpu_percent: Optional[float]
    memory_percent: Optional[float]
    memory_used_mb: Optional[int]
    memory_total_mb: Optional[int]
    disk_percent: Optional[float]
    disk_used_gb: Optional[float]
    disk_total_gb: Optional[float]
    load_avg_1m: Optional[float]
    load_avg_5m: Optional[float]
    load_avg_15m: Optional[float]

    class Config:
        from_attributes = True


class ServiceStatusOut(BaseModel):
    id: str
    time: datetime
    instance_id: str
    container_name: str
    status: str
    restart_count: Optional[int]
    image: Optional[str]

    class Config:
        from_attributes = True


class ServiceLogOut(BaseModel):
    id: str
    instance_id: str
    container_name: str
    log_level: str
    message: str
    pattern_matched: Optional[str]
    captured_at: datetime

    class Config:
        from_attributes = True


@router.get("/metrics", response_model=list[VpsMetricOut])
async def get_vps_metrics(
    instance_id: Optional[uuid.UUID] = Query(None),
    hours: int = Query(default=24, ge=1, le=720),
    limit: int = Query(default=100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Retorna métricas de recursos das VPS."""
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    query = select(VpsMetric).where(VpsMetric.time >= since)

    if instance_id:
        query = query.where(VpsMetric.instance_id == instance_id)

    query = query.order_by(desc(VpsMetric.time)).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/services", response_model=list[ServiceStatusOut])
async def get_service_status(
    instance_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Retorna status atual dos containers Docker por instância."""
    from sqlalchemy import text
    query = text("""
        SELECT DISTINCT ON (instance_id, container_name)
            id, time, instance_id, container_name, status,
            restart_count, image
        FROM service_status
        ORDER BY instance_id, container_name, time DESC
    """)
    result = await db.execute(query)
    return [dict(row._mapping) for row in result.fetchall()]


@router.get("/logs", response_model=list[ServiceLogOut])
async def get_service_logs(
    instance_id: Optional[uuid.UUID] = Query(None),
    log_level: Optional[str] = Query(None, pattern="^(info|warning|error|critical)$"),
    hours: int = Query(default=24, ge=1, le=168),
    limit: int = Query(default=200, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Retorna logs de serviços com padrões de erro detectados."""
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    query = select(ServiceLog).where(ServiceLog.captured_at >= since)

    if instance_id:
        query = query.where(ServiceLog.instance_id == instance_id)
    if log_level:
        query = query.where(ServiceLog.log_level == log_level)

    query = query.order_by(desc(ServiceLog.captured_at)).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()
