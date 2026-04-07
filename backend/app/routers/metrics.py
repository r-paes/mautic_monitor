"""
routers/metrics.py — Endpoints de métricas Mautic e gateways.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.metrics import HealthMetric, GatewayMetric
from app.routers.auth import get_current_user
from app.models.users import User

router = APIRouter(prefix="/metrics", tags=["metrics"])


class HealthMetricOut(BaseModel):
    id: uuid.UUID
    time: datetime
    instance_id: uuid.UUID
    new_contacts: Optional[int]
    active_campaigns: Optional[int]
    emails_queued: Optional[int]
    emails_sent_mautic: Optional[int]
    sms_sent_mautic: Optional[int]
    api_response_ms: Optional[int]
    db_response_ms: Optional[int]
    status: str

    model_config = {"from_attributes": True}


class GatewayMetricOut(BaseModel):
    id: uuid.UUID
    time: datetime
    gateway_type: str
    # Sub-account (Sendpost)
    subaccount_id: Optional[int]
    subaccount_name: Optional[str]
    # Email (Sendpost)
    emails_sent: Optional[int]
    emails_delivered: Optional[int]
    emails_dropped: Optional[int]
    emails_hard_bounced: Optional[int]
    emails_soft_bounced: Optional[int]
    emails_opened: Optional[int]
    emails_clicked: Optional[int]
    emails_unsubscribed: Optional[int]
    emails_spam: Optional[int]
    open_rate: Optional[float]
    click_rate: Optional[float]
    # SMS (Avant)
    sms_sent: Optional[int]
    sms_delivered: Optional[int]
    sms_failed: Optional[int]
    # Saldo
    balance_credits: Optional[float]

    model_config = {"from_attributes": True}


@router.get("/health", response_model=list[HealthMetricOut])
async def get_health_metrics(
    instance_id: Optional[uuid.UUID] = Query(None),
    hours: int = Query(default=24, ge=1, le=720),
    limit: int = Query(default=100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Retorna métricas de saúde das instâncias Mautic."""
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    query = select(HealthMetric).where(HealthMetric.time >= since)

    if instance_id:
        query = query.where(HealthMetric.instance_id == instance_id)

    query = query.order_by(desc(HealthMetric.time)).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/gateways", response_model=list[GatewayMetricOut])
async def get_gateway_metrics(
    gateway_type: Optional[str] = Query(None, pattern="^(sendpost|avant_sms)$"),
    start: Optional[str] = Query(None, description="ISO datetime inicio (ex: 2026-04-07T00:00:00)"),
    end: Optional[str] = Query(None, description="ISO datetime fim"),
    hours: int = Query(default=24, ge=1, le=720),
    limit: int = Query(default=500, ge=1, le=5000),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Retorna métricas dos gateways de envio."""
    if start:
        since = datetime.fromisoformat(start.replace("Z", "+00:00"))
    else:
        since = datetime.now(timezone.utc) - timedelta(hours=hours)

    query = select(GatewayMetric).where(GatewayMetric.time >= since)

    if end:
        until = datetime.fromisoformat(end.replace("Z", "+00:00"))
        query = query.where(GatewayMetric.time <= until)

    if gateway_type:
        query = query.where(GatewayMetric.gateway_type == gateway_type)

    query = query.order_by(desc(GatewayMetric.time)).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/health/latest")
async def get_latest_health(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Retorna último snapshot de saúde por instância (para o dashboard overview)."""
    # Retorna o registro mais recente de cada instância
    from sqlalchemy import func, text
    query = text("""
        SELECT DISTINCT ON (instance_id)
            id, time, instance_id, new_contacts, active_campaigns,
            emails_queued, emails_sent_mautic, sms_sent_mautic,
            api_response_ms, db_response_ms, status
        FROM health_metrics
        ORDER BY instance_id, time DESC
    """)
    result = await db.execute(query)
    return [dict(row._mapping) for row in result.fetchall()]
