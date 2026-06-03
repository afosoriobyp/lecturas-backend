from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DuplicateException, UnauthorizedException
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.schemas.auth import TokenResponse, UserSessionOut


async def register_user(
    db: AsyncSession,
    username: str,
    password: str,
    email: str | None = None,
    full_name: str | None = None,
    rol: str = "lector",
) -> User:
    existing = await db.execute(
        select(User).where(User.username == username)
    )
    if existing.scalar_one_or_none():
        raise DuplicateException("Usuario")

    user = User(
        username=username,
        email=email,
        full_name=full_name,
        hashed_password=hash_password(password),
        rol=rol,
    )
    db.add(user)
    await db.flush()
    return user


async def authenticate_user(
    db: AsyncSession, email: str, password: str
) -> User:
    result = await db.execute(
        select(User).where((User.email == email) | (User.username == email))
    )
    user = result.scalar_one_or_none()
    if not user or not verify_password(password, user.hashed_password):
        raise UnauthorizedException("Credenciales inválidas")
    if not user.is_active:
        raise UnauthorizedException("Usuario inactivo")
    return user


def build_token_response(user: User) -> TokenResponse:
    payload = {"sub": str(user.id), "rol": user.rol, "username": user.username}
    return TokenResponse(
        access_token=create_access_token(payload),
        refresh_token=create_refresh_token(payload),
        expires_in_minutes=30,
    )


async def refresh_access_token(db: AsyncSession, refresh_token: str) -> TokenResponse:
    payload = decode_token(refresh_token)
    if payload.get("type") != "refresh":
        raise UnauthorizedException("Tipo de token inválido")

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise UnauthorizedException("Usuario no encontrado o inactivo")

    return build_token_response(user)


def user_to_session(user: User) -> UserSessionOut:
    return UserSessionOut(
        id=user.id,
        username=user.username,
        full_name=user.full_name,
        rol=user.rol,
        telegram_id=user.telegram_id,
    )
