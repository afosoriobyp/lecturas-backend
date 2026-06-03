from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response
from fastapi.security import HTTPBearer

from app.api.dependencies import SessionDep
from app.core.config import settings
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    TokenResponse,
    UserSessionOut,
)
from app.schemas.user import UserOut
from app.services import auth as auth_service
from app.services.audit import log_action

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/register",
    response_model=UserOut,
    status_code=201,
    summary="Registrar nuevo usuario",
)
async def register(
    db: SessionDep,
    payload: LoginRequest,
):
    user = await auth_service.register_user(
        db,
        username=payload.email,
        email=payload.email,
        password=payload.password,
    )
    return user


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Iniciar sesión (retorna JWT en body + cookie)",
)
async def login(
    db: SessionDep,
    payload: LoginRequest,
    response: Response,
):
    user = await auth_service.authenticate_user(
        db, email=payload.email, password=payload.password
    )
    tokens = auth_service.build_token_response(user)

    # Set httpOnly cookie para dev local
    response.set_cookie(
        key="access_token",
        value=tokens.access_token,
        httponly=True,
        secure=settings.JWT_COOKIE_SECURE,
        samesite=settings.JWT_COOKIE_SAMESITE,
        max_age=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )

    await log_action(
        db, accion="auth.login", entidad_tipo="user",
        entidad_id=user.id, actor_id=str(user.id),
    )

    return tokens


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refrescar token de acceso",
)
async def refresh(
    db: SessionDep,
    payload: RefreshRequest,
    response: Response,
):
    tokens = await auth_service.refresh_access_token(db, payload.refresh_token)

    response.set_cookie(
        key="access_token",
        value=tokens.access_token,
        httponly=True,
        secure=settings.JWT_COOKIE_SECURE,
        samesite=settings.JWT_COOKIE_SAMESITE,
        max_age=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )

    return tokens


@router.post(
    "/logout",
    summary="Cerrar sesión (elimina cookie)",
)
async def logout(
    response: Response,
    current_user: User = Depends(get_current_user),
):
    response.delete_cookie("access_token", path="/")
    return {"message": "Sesión cerrada"}


@router.get(
    "/me",
    response_model=UserSessionOut,
    summary="Obtener perfil del usuario autenticado",
)
async def me(
    current_user: User = Depends(get_current_user),
):
    return auth_service.user_to_session(current_user)


@router.get(
    "/perfil",
    response_model=UserSessionOut,
    summary="Obtener perfil del usuario autenticado",
)
async def perfil(
    current_user: User = Depends(get_current_user),
):
    return auth_service.user_to_session(current_user)
