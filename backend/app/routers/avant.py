"""
routers/avant.py — Cost Centers Avant SMS + stats por cliente.

GET    /gateways/avant/cost-centers        — lista cost centers
POST   /gateways/avant/cost-centers        — cria/atualiza cost center
DELETE /gateways/avant/cost-centers/{code}  — remove cost center
GET    /gateways/avant/stats               — stats por costCenterCode (hoje)
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.avant import AvantCostCenter
from app.routers.auth import get_current_user
from app.models.users import User
from app.collectors.avant_sms import AvantSMSCollector
from app.utils.gateway_settings import get_gateway_setting
from app.config import settings

router = APIRouter(prefix="/gateways/avant", tags=["avant-sms"])


# ─── Schemas ──────────────────────────────────────────────────────────────────

class CostCenterIn(BaseModel):
    code: str
    client_name: str


class CostCenterOut(BaseModel):
    code: str
    client_name: str
    active: bool

    model_config = {"from_attributes": True}


class CostCenterStatsOut(BaseModel):
    cost_center_code: str
    client_name: str
    sms_sent: int
    sms_delivered: int
    sms_failed: int


class AvantStatsOut(BaseModel):
    balance: Optional[int] = None
    by_client: list[CostCenterStatsOut]


# ─── Cost Centers CRUD ───────────────────────────────────────────────────────

@router.get("/cost-centers", response_model=list[CostCenterOut])
async def list_cost_centers(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Lista todos os cost centers cadastrados."""
    result = await db.execute(
        select(AvantCostCenter).order_by(AvantCostCenter.client_name)
    )
    return result.scalars().all()


@router.post("/cost-centers", response_model=CostCenterOut, status_code=status.HTTP_201_CREATED)
async def create_cost_center(
    data: CostCenterIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cria ou atualiza um cost center (upsert por code)."""
    if current_user.role not in ("admin",):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão")

    existing = await db.get(AvantCostCenter, data.code)
    if existing:
        existing.client_name = data.client_name
        existing.active = True
        await db.commit()
        await db.refresh(existing)
        return existing

    cc = AvantCostCenter(
        code=data.code,
        client_name=data.client_name,
        active=True,
    )
    db.add(cc)
    await db.commit()
    await db.refresh(cc)
    return cc


@router.delete("/cost-centers/{code}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cost_center(
    code: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove um cost center."""
    if current_user.role not in ("admin",):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão")

    existing = await db.get(AvantCostCenter, code)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cost center não encontrado")

    await db.delete(existing)
    await db.commit()


# ─── Stats por cliente ────────────────────────────────────────────────────────

@router.get("/stats", response_model=AvantStatsOut)
async def get_avant_stats(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Retorna saldo real + stats por costCenterCode (hoje)."""
    token = await get_gateway_setting(db, "avant_sms_token", settings.avant_sms_token)
    collector = AvantSMSCollector(token=token)

    balance = await collector.get_balance()
    by_client = await collector.get_stats_by_cost_center(db)

    return AvantStatsOut(
        balance=balance,
        by_client=[CostCenterStatsOut(**row) for row in by_client],
    )
