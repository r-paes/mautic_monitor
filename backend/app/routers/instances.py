"""
routers/instances.py — CRUD de instâncias Mautic.
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.instance import Instance, Company
from app.routers.auth import get_current_user
from app.models.users import User

router = APIRouter(prefix="/instances", tags=["instances"])


# ─── Schemas ─────────────────────────────────────────────────────────────────

class InstanceCreate(BaseModel):
    name: str
    url: str
    api_user: str
    api_password: str
    db_host: Optional[str] = None
    db_port: int = 5432
    db_name: Optional[str] = None
    db_user: Optional[str] = None
    db_password: Optional[str] = None
    ssh_host: Optional[str] = None
    ssh_port: int = 22
    ssh_user: Optional[str] = None
    ssh_key_path: Optional[str] = None


class InstanceOut(BaseModel):
    id: str
    name: str
    url: str
    api_user: str
    db_host: Optional[str]
    ssh_host: Optional[str]
    active: bool

    class Config:
        from_attributes = True


class InstanceUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    api_user: Optional[str] = None
    api_password: Optional[str] = None
    active: Optional[bool] = None


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.get("/", response_model=list[InstanceOut])
async def list_instances(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(Instance).order_by(Instance.name))
    return result.scalars().all()


@router.post("/", response_model=InstanceOut, status_code=status.HTTP_201_CREATED)
async def create_instance(
    data: InstanceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ("admin",):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão")

    instance = Instance(
        name=data.name,
        url=data.url,
        api_user=data.api_user,
        api_password_enc=data.api_password,  # TODO: encriptar com Fernet
        db_host=data.db_host,
        db_port=data.db_port,
        db_name=data.db_name,
        db_user=data.db_user,
        db_password_enc=data.db_password,
        ssh_host=data.ssh_host,
        ssh_port=data.ssh_port,
        ssh_user=data.ssh_user,
        ssh_key_path=data.ssh_key_path,
    )
    db.add(instance)
    await db.commit()
    await db.refresh(instance)
    return instance


@router.get("/{instance_id}", response_model=InstanceOut)
async def get_instance(
    instance_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(Instance).where(Instance.id == instance_id))
    instance = result.scalars().first()
    if not instance:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instância não encontrada")
    return instance


@router.patch("/{instance_id}", response_model=InstanceOut)
async def update_instance(
    instance_id: uuid.UUID,
    data: InstanceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ("admin",):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão")

    result = await db.execute(select(Instance).where(Instance.id == instance_id))
    instance = result.scalars().first()
    if not instance:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instância não encontrada")

    for field, value in data.model_dump(exclude_none=True).items():
        if field == "api_password":
            setattr(instance, "api_password_enc", value)
        else:
            setattr(instance, field, value)

    await db.commit()
    await db.refresh(instance)
    return instance


@router.delete("/{instance_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_instance(
    instance_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ("admin",):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão")

    result = await db.execute(select(Instance).where(Instance.id == instance_id))
    instance = result.scalars().first()
    if not instance:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instância não encontrada")

    await db.delete(instance)
    await db.commit()
