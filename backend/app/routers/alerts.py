"""
routers/alerts.py — Endpoints de alertas.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.alerts import Alert
from app.routers.auth import get_current_user
from app.models.users import User

router = APIRouter(prefix="/alerts", tags=["alerts"])


class AlertOut(BaseModel):
    id: str
    instance_id: Optional[str]
    severity: str
    type: str
    message: str
    notified_via: Optional[str]
    created_at: datetime
    resolved_at: Optional[datetime]
    acked_by: Optional[str]

    class Config:
        from_attributes = True


@router.get("/", response_model=list[AlertOut])
async def list_alerts(
    instance_id: Optional[uuid.UUID] = Query(None),
    severity: Optional[str] = Query(None, pattern="^(info|warning|critical)$"),
    resolved: Optional[bool] = Query(None),
    hours: int = Query(default=72, ge=1, le=8760),
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    query = select(Alert).where(Alert.created_at >= since)

    if instance_id:
        query = query.where(Alert.instance_id == instance_id)
    if severity:
        query = query.where(Alert.severity == severity)
    if resolved is not None:
        if resolved:
            query = query.where(Alert.resolved_at.isnot(None))
        else:
            query = query.where(Alert.resolved_at.is_(None))

    query = query.order_by(desc(Alert.created_at)).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/{alert_id}/ack", response_model=AlertOut)
async def acknowledge_alert(
    alert_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Marca alerta como reconhecido (ACK) pelo usuário atual."""
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalars().first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alerta não encontrado")

    alert.acked_by = current_user.id
    alert.resolved_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(alert)
    return alert


@router.get("/summary")
async def get_alerts_summary(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Resumo de alertas ativos por severidade (para o dashboard overview)."""
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    from sqlalchemy import func

    result = await db.execute(
        select(Alert.severity, func.count(Alert.id).label("count"))
        .where(Alert.created_at >= since, Alert.resolved_at.is_(None))
        .group_by(Alert.severity)
    )
    rows = result.fetchall()
    return {row.severity: row.count for row in rows}
