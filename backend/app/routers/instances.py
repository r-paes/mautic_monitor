"""
routers/instances.py — CRUD de instâncias Mautic + gerenciamento de chaves SSH.

A API mantém formato flat (campos de credencial no mesmo nível) para
compatibilidade com o frontend. Internamente, credenciais vivem em
tabelas separadas (1:1 com Instance).
"""

import uuid
from io import StringIO
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.instance import (
    Instance, InstanceApiCredential, InstanceDbCredential, InstanceSshCredential,
)
from app.routers.auth import get_current_user
from app.models.users import User
from app.utils.crypto import encrypt_secret, decrypt_secret

router = APIRouter(prefix="/instances", tags=["instances"])


# ─── Schemas (API flat — frontend não muda) ─────────────────────────────────

class InstanceCreate(BaseModel):
    name: str
    url: str
    api_user: str
    api_password: str
    db_host: Optional[str] = None
    db_port: int = 3306
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
    api_user: Optional[str] = None
    db_host: Optional[str] = None
    ssh_host: Optional[str] = None
    ssh_port: int = 22
    ssh_user: Optional[str] = None
    ssh_key_path: Optional[str] = None
    ssh_public_key: Optional[str] = None
    active: bool


class InstanceUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    api_user: Optional[str] = None
    api_password: Optional[str] = None
    active: Optional[bool] = None
    db_host: Optional[str] = None
    db_port: Optional[int] = None
    db_name: Optional[str] = None
    db_user: Optional[str] = None
    db_password: Optional[str] = None
    ssh_host: Optional[str] = None
    ssh_port: Optional[int] = None
    ssh_user: Optional[str] = None
    ssh_key_path: Optional[str] = None


class SshKeyOut(BaseModel):
    public_key: str


class SshTestResult(BaseModel):
    success: bool
    message: str


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _instance_to_out(inst: Instance) -> InstanceOut:
    """Converte Instance (com relationships) para resposta flat."""
    return InstanceOut(
        id=str(inst.id),
        name=inst.name,
        url=inst.url,
        api_user=inst.api_user,
        db_host=inst.db_host,
        ssh_host=inst.ssh_host,
        ssh_port=inst.ssh_port,
        ssh_user=inst.ssh_user,
        ssh_key_path=inst.ssh_key_path,
        ssh_public_key=inst.ssh_public_key,
        active=inst.active,
    )


def _generate_rsa_keypair() -> tuple[str, str]:
    """Gera par de chaves RSA 4096 bits. Retorna (private_pem, public_openssh)."""
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.backends import default_backend

    private_key = rsa.generate_private_key(
        public_exponent=65537, key_size=4096, backend=default_backend(),
    )
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.OpenSSH,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")
    public_openssh = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.OpenSSH,
        format=serialization.PublicFormat.OpenSSH,
    ).decode("utf-8")
    return private_pem, public_openssh


def _get_instance_or_404(instance, instance_id: uuid.UUID) -> Instance:
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Instância não encontrada",
        )
    return instance


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.get("/", response_model=list[InstanceOut])
async def list_instances(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(Instance).order_by(Instance.name))
    return [_instance_to_out(i) for i in result.scalars().unique().all()]


@router.post("/", response_model=InstanceOut, status_code=status.HTTP_201_CREATED)
async def create_instance(
    data: InstanceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ("admin",):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão")

    instance = Instance(name=data.name, url=data.url)

    # API credentials (obrigatório)
    instance.api_creds = InstanceApiCredential(
        username=data.api_user,
        password_enc=encrypt_secret(data.api_password),
    )

    # DB credentials (opcional)
    if data.db_host and data.db_name and data.db_user:
        instance.db_creds = InstanceDbCredential(
            host=data.db_host,
            port=data.db_port,
            dbname=data.db_name,
            username=data.db_user,
            password_enc=encrypt_secret(data.db_password) if data.db_password else "",
        )

    # SSH credentials (opcional)
    if data.ssh_host:
        instance.ssh_creds = InstanceSshCredential(
            host=data.ssh_host,
            port=data.ssh_port,
            username=data.ssh_user or "root",
            key_path=data.ssh_key_path,
        )

    db.add(instance)
    await db.commit()
    await db.refresh(instance)
    return _instance_to_out(instance)


@router.get("/{instance_id}", response_model=InstanceOut)
async def get_instance(
    instance_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(Instance).where(Instance.id == instance_id))
    instance = _get_instance_or_404(result.scalars().first(), instance_id)
    return _instance_to_out(instance)


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
    instance = _get_instance_or_404(result.scalars().first(), instance_id)

    updates = data.model_dump(exclude_none=True)

    # Instance fields
    for field in ("name", "url", "active"):
        if field in updates:
            setattr(instance, field, updates[field])

    # API credentials
    api_fields = {k: updates[k] for k in ("api_user", "api_password") if k in updates}
    if api_fields:
        if not instance.api_creds:
            instance.api_creds = InstanceApiCredential(
                instance_id=instance.id,
                username=api_fields.get("api_user", ""),
                password_enc="",
            )
        if "api_user" in api_fields:
            instance.api_creds.username = api_fields["api_user"]
        if "api_password" in api_fields:
            instance.api_creds.password_enc = encrypt_secret(api_fields["api_password"])

    # DB credentials
    db_fields = {k: updates[k] for k in ("db_host", "db_port", "db_name", "db_user", "db_password") if k in updates}
    if db_fields:
        if not instance.db_creds:
            instance.db_creds = InstanceDbCredential(
                instance_id=instance.id,
                host=db_fields.get("db_host", ""),
                port=db_fields.get("db_port", 3306),
                dbname=db_fields.get("db_name", ""),
                username=db_fields.get("db_user", ""),
                password_enc="",
            )
        if "db_host" in db_fields:
            instance.db_creds.host = db_fields["db_host"]
        if "db_port" in db_fields:
            instance.db_creds.port = db_fields["db_port"]
        if "db_name" in db_fields:
            instance.db_creds.dbname = db_fields["db_name"]
        if "db_user" in db_fields:
            instance.db_creds.username = db_fields["db_user"]
        if "db_password" in db_fields:
            instance.db_creds.password_enc = encrypt_secret(db_fields["db_password"])

    # SSH credentials
    ssh_fields = {k: updates[k] for k in ("ssh_host", "ssh_port", "ssh_user", "ssh_key_path") if k in updates}
    if ssh_fields:
        if not instance.ssh_creds:
            instance.ssh_creds = InstanceSshCredential(
                instance_id=instance.id,
                host=ssh_fields.get("ssh_host", ""),
                port=ssh_fields.get("ssh_port", 22),
                username=ssh_fields.get("ssh_user", "root"),
            )
        if "ssh_host" in ssh_fields:
            instance.ssh_creds.host = ssh_fields["ssh_host"]
        if "ssh_port" in ssh_fields:
            instance.ssh_creds.port = ssh_fields["ssh_port"]
        if "ssh_user" in ssh_fields:
            instance.ssh_creds.username = ssh_fields["ssh_user"]
        if "ssh_key_path" in ssh_fields:
            instance.ssh_creds.key_path = ssh_fields["ssh_key_path"]

    await db.commit()
    await db.refresh(instance)
    return _instance_to_out(instance)


@router.delete("/{instance_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_instance(
    instance_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ("admin",):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão")

    result = await db.execute(select(Instance).where(Instance.id == instance_id))
    instance = _get_instance_or_404(result.scalars().first(), instance_id)
    await db.delete(instance)
    await db.commit()


@router.post("/{instance_id}/generate-ssh-key", response_model=SshKeyOut)
async def generate_ssh_key(
    instance_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Gera novo par RSA 4096. Privada armazenada Fernet. Pública retornada."""
    if current_user.role not in ("admin",):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão")

    result = await db.execute(select(Instance).where(Instance.id == instance_id))
    instance = _get_instance_or_404(result.scalars().first(), instance_id)

    private_pem, public_openssh = _generate_rsa_keypair()

    if not instance.ssh_creds:
        instance.ssh_creds = InstanceSshCredential(
            instance_id=instance.id,
            host=instance.ssh_host or "",
            username=instance.ssh_user or "root",
        )

    instance.ssh_creds.private_key_enc = encrypt_secret(private_pem)
    instance.ssh_creds.public_key = public_openssh

    await db.commit()
    return SshKeyOut(public_key=public_openssh)


@router.post("/{instance_id}/test-ssh", response_model=SshTestResult)
async def test_ssh_connection(
    instance_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Testa conexão SSH com a VPS usando a chave privada armazenada."""
    import asyncio
    import paramiko

    result = await db.execute(select(Instance).where(Instance.id == instance_id))
    instance = _get_instance_or_404(result.scalars().first(), instance_id)

    if not instance.ssh_host:
        return SshTestResult(success=False, message="Host SSH não configurado.")

    if not instance.ssh_private_key_enc:
        return SshTestResult(success=False, message="Chave SSH não gerada. Clique em 'Gerar Chave' primeiro.")

    private_pem = decrypt_secret(instance.ssh_private_key_enc)
    if not private_pem:
        return SshTestResult(success=False, message="Falha ao decriptar chave privada.")

    def _do_test() -> SshTestResult:
        try:
            key = paramiko.RSAKey.from_private_key(StringIO(private_pem))
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(
                hostname=instance.ssh_host,
                port=instance.ssh_port or 22,
                username=instance.ssh_user or "root",
                pkey=key, timeout=10,
                look_for_keys=False, allow_agent=False,
            )
            _, stdout, _ = client.exec_command("echo ok", timeout=5)
            output = stdout.read().decode().strip()
            client.close()
            if output == "ok":
                return SshTestResult(success=True, message="Conexão SSH estabelecida com sucesso.")
            return SshTestResult(success=False, message=f"Resposta inesperada: {output}")
        except paramiko.AuthenticationException:
            return SshTestResult(
                success=False,
                message="Autenticação negada. Verifique se a chave pública foi adicionada em ~/.ssh/authorized_keys na VPS.",
            )
        except Exception as e:
            return SshTestResult(success=False, message=f"Erro de conexão: {e}")

    return await asyncio.get_event_loop().run_in_executor(None, _do_test)
