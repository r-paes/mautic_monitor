"""
routers/vps_servers.py — CRUD de servidores VPS + conexão EasyPanel.

VPS é uma entidade independente que pode hospedar múltiplas instâncias Mautic.
Monitoramento via API tRPC do EasyPanel.
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.vps_server import VpsServer
from app.routers.auth import get_current_user
from app.models.users import User
from app.utils.crypto import encrypt_secret, decrypt_secret
from app.collectors.easypanel import EasyPanelCollector

router = APIRouter(prefix="/vps-servers", tags=["vps-servers"])


# ─── Schemas ────────────────────────────────────────────────────────────────

class VpsServerCreate(BaseModel):
    name: str
    easypanel_url: str
    api_key: str


class VpsServerOut(BaseModel):
    id: str
    name: str
    easypanel_url: str
    active: bool
    instance_count: int = 0

    model_config = {"from_attributes": True}


class VpsServerUpdate(BaseModel):
    name: Optional[str] = None
    easypanel_url: Optional[str] = None
    api_key: Optional[str] = None
    active: Optional[bool] = None


class ConnectionTestResult(BaseModel):
    success: bool
    message: str
    cpu_count: Optional[int] = None
    memory_total_mb: Optional[float] = None
    disk_total_gb: Optional[float] = None


class EasyPanelServiceOut(BaseModel):
    name: str
    project: str
    type: str
    status: str
    image: str


# ─── Helpers ────────────────────────────────────────────────────────────────

def _vps_to_out(vps: VpsServer) -> VpsServerOut:
    return VpsServerOut(
        id=str(vps.id),
        name=vps.name,
        easypanel_url=vps.easypanel_url,
        active=vps.active,
        instance_count=len(vps.instances) if vps.instances else 0,
    )


async def _get_collector(vps: VpsServer) -> EasyPanelCollector:
    """Cria collector EasyPanel a partir da VPS."""
    if not vps.api_key_enc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="API key não configurada.",
        )
    api_key = decrypt_secret(vps.api_key_enc)
    return EasyPanelCollector(easypanel_url=vps.easypanel_url, api_key=api_key)


# ─── Endpoints ──────────────────────────────────────────────────────────────

@router.get("/", response_model=list[VpsServerOut])
async def list_vps_servers(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(VpsServer).order_by(VpsServer.name))
    return [_vps_to_out(v) for v in result.scalars().unique().all()]


@router.post("/", response_model=VpsServerOut, status_code=status.HTTP_201_CREATED)
async def create_vps_server(
    data: VpsServerCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ("admin",):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão")

    vps = VpsServer(
        name=data.name,
        easypanel_url=data.easypanel_url.rstrip("/"),
        api_key_enc=encrypt_secret(data.api_key),
    )
    db.add(vps)
    await db.commit()
    await db.refresh(vps)
    return _vps_to_out(vps)


@router.get("/{vps_id}", response_model=VpsServerOut)
async def get_vps_server(
    vps_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(VpsServer).where(VpsServer.id == vps_id))
    vps = result.scalars().first()
    if not vps:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="VPS não encontrada")
    return _vps_to_out(vps)


@router.patch("/{vps_id}", response_model=VpsServerOut)
async def update_vps_server(
    vps_id: uuid.UUID,
    data: VpsServerUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ("admin",):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão")

    result = await db.execute(select(VpsServer).where(VpsServer.id == vps_id))
    vps = result.scalars().first()
    if not vps:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="VPS não encontrada")

    if data.name is not None:
        vps.name = data.name
    if data.easypanel_url is not None:
        vps.easypanel_url = data.easypanel_url.rstrip("/")
    if data.api_key is not None:
        vps.api_key_enc = encrypt_secret(data.api_key)
    if data.active is not None:
        vps.active = data.active

    await db.commit()
    await db.refresh(vps)
    return _vps_to_out(vps)


@router.delete("/{vps_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vps_server(
    vps_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ("admin",):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão")

    result = await db.execute(select(VpsServer).where(VpsServer.id == vps_id))
    vps = result.scalars().first()
    if not vps:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="VPS não encontrada")

    await db.delete(vps)
    await db.commit()


@router.post("/{vps_id}/test-connection", response_model=ConnectionTestResult)
async def test_connection(
    vps_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Testa conexão com o EasyPanel da VPS."""
    result = await db.execute(select(VpsServer).where(VpsServer.id == vps_id))
    vps = result.scalars().first()
    if not vps:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="VPS não encontrada")

    collector = await _get_collector(vps)

    try:
        info = await collector.test_connection()
        return ConnectionTestResult(
            success=True,
            message="Conexão estabelecida com sucesso.",
            cpu_count=info.get("cpu_count"),
            memory_total_mb=info.get("memory_total_mb"),
            disk_total_gb=float(info["disk_total_gb"]) if info.get("disk_total_gb") else None,
        )
    except Exception as e:
        return ConnectionTestResult(success=False, message=f"Erro: {e}")


@router.get("/{vps_id}/services", response_model=list[EasyPanelServiceOut])
async def list_easypanel_services(
    vps_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Lista serviços/containers disponíveis no EasyPanel desta VPS.

    Usado para descoberta automática ao cadastrar instâncias.
    """
    result = await db.execute(select(VpsServer).where(VpsServer.id == vps_id))
    vps = result.scalars().first()
    if not vps:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="VPS não encontrada")

    collector = await _get_collector(vps)

    try:
        data = await collector.get_projects_and_services()
        containers = collector._parse_services(data)
        return [
            EasyPanelServiceOut(
                name=c["name"],
                project=c["project"],
                type=c["type"],
                status=c["status"],
                image=c["image"],
            )
            for c in containers
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Erro ao consultar EasyPanel: {e}",
        )
