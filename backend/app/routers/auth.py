"""
routers/auth.py — Endpoints de autenticação JWT.

Refresh token armazenado em cookie HTTP-only (não acessível via JavaScript).
Access token retornado no body JSON (armazenado em memória no frontend).
"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.users import User

router = APIRouter(prefix="/auth", tags=["auth"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.api_v1_prefix}/auth/login")

REFRESH_COOKIE_NAME = "refresh_token"
REFRESH_COOKIE_MAX_AGE = settings.refresh_token_expire_days * 24 * 60 * 60  # em segundos


# ─── Schemas ─────────────────────────────────────────────────────────────────

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: str
    name: str
    email: str
    role: str

    class Config:
        from_attributes = True


# ─── Helpers ─────────────────────────────────────────────────────────────────

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    return jwt.encode(
        {"sub": user_id, "exp": expire},
        settings.secret_key,
        algorithm=settings.algorithm,
    )


def create_refresh_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.refresh_token_expire_days
    )
    return jwt.encode(
        {"sub": user_id, "exp": expire, "type": "refresh"},
        settings.secret_key,
        algorithm=settings.algorithm,
    )


def _set_refresh_cookie(response: Response, token: str) -> None:
    """Seta o refresh token como cookie HTTP-only seguro."""
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=token,
        max_age=REFRESH_COOKIE_MAX_AGE,
        httponly=True,
        secure=settings.is_production,  # HTTPS only em produção
        samesite="lax",
        path="/",
    )


def _clear_refresh_cookie(response: Response) -> None:
    """Remove o cookie de refresh token."""
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        path="/",
    )


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciais inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == user_id, User.active == True))
    user = result.scalars().first()
    if user is None:
        raise credentials_exception
    return user


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.post("/login", response_model=TokenOut)
async def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalars().first()

    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos",
        )

    if not user.active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuário inativo")

    user.last_login = datetime.now(timezone.utc)
    await db.commit()

    refresh = create_refresh_token(str(user.id))
    _set_refresh_cookie(response, refresh)

    return TokenOut(
        access_token=create_access_token(str(user.id)),
    )


@router.post("/refresh", response_model=TokenOut)
async def refresh_token(
    response: Response,
    refresh_token: str | None = Cookie(None, alias=REFRESH_COOKIE_NAME),
    db: AsyncSession = Depends(get_db),
):
    """Renova o access token usando o refresh token do cookie HTTP-only."""
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token não encontrado",
        )

    try:
        payload = jwt.decode(
            refresh_token, settings.secret_key, algorithms=[settings.algorithm]
        )
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")
    except JWTError:
        _clear_refresh_cookie(response)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expirado")

    result = await db.execute(select(User).where(User.id == user_id, User.active == True))
    user = result.scalars().first()
    if not user:
        _clear_refresh_cookie(response)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário não encontrado")

    # Rota o refresh token (emite um novo a cada refresh)
    new_refresh = create_refresh_token(str(user.id))
    _set_refresh_cookie(response, new_refresh)

    return TokenOut(
        access_token=create_access_token(str(user.id)),
    )


@router.post("/logout")
async def logout(response: Response):
    """Remove o cookie de refresh token."""
    _clear_refresh_cookie(response)
    return {"detail": "Logout realizado"}


@router.get("/me", response_model=UserOut)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user
