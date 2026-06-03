from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Cookie, Depends, Request, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp
import bcrypt as _bcrypt

from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit_events import current_actor_id, current_ip, current_ua
from app.core.config import settings
from app.core.log_config import user_id_var
from app.core.database import get_db
from app.core.exceptions import ForbiddenException, UnauthorizedException
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)

PUBLIC_PATHS = {
    "/health",
    "/api/health",
    "/auth/login",
    "/api/auth/login",
    "/auth/register",
    "/api/auth/register",
    "/auth/refresh",
    "/api/auth/refresh",
    "/docs",
    "/redoc",
    "/openapi.json",
}


class UserContext:
    """Ligero objeto de contexto para request.user."""

    def __init__(self, id: str, username: str, rol: str) -> None:
        self.id = id
        self.username = username
        self.rol = rol


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware que inyecta request.user (con .rol) en cada endpoint."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request.state.user = None
        current_actor_id.set(None)

        if request.method == "OPTIONS":
            return await call_next(request)

        path = request.url.path.rstrip("/")

        if path not in PUBLIC_PATHS:
            token: str | None = None

            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.removeprefix("Bearer ")

            if not token:
                token = request.cookies.get("access_token")

            if token:
                try:
                    payload = decode_token(token)
                    if payload.get("type") == "access":
                        user_id = payload.get("sub")
                        user_rol = payload.get("rol", "")
                        user_username = payload.get("username", "")

                        if user_id:
                            ctx = UserContext(
                                id=str(user_id),
                                username=user_username,
                                rol=str(user_rol),
                            )
                            request.state.user = ctx
                            current_actor_id.set(str(user_id))
                            user_id_var.set(str(user_id))
                            current_ip.set(request.client.host if request.client else None)
                            current_ua.set(request.headers.get("user-agent"))
                except UnauthorizedException:
                    pass

        return await call_next(request)


def hash_password(password: str) -> str:
    return _bcrypt.hashpw(password.encode(), _bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return _bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(data: dict[str, Any]) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(data: dict[str, Any]) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
    )
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except JWTError:
        raise UnauthorizedException("Token inválido o expirado")


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
    access_token: str | None = Cookie(default=None),
) -> User:
    token = None

    if credentials:
        token = credentials.credentials
    elif access_token:
        token = access_token

    if not token:
        raise UnauthorizedException("Token de acceso requerido")

    payload = decode_token(token)

    if payload.get("type") != "access":
        raise UnauthorizedException("Tipo de token inválido")

    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedException("Payload inválido")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise UnauthorizedException("Usuario no encontrado o inactivo")

    return user


def require_roles(*roles: str):
    """Dependency factory: verifica que el usuario tenga uno de los roles especificados."""

    async def _check(user: User = Depends(get_current_user)) -> User:
        if user.rol not in roles:
            raise ForbiddenException(
                f"Se requiere uno de estos roles: {', '.join(roles)}"
            )
        return user

    return _check
