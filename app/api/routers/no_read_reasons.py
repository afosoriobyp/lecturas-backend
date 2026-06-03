from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import SessionDep
from app.core.exceptions import DuplicateException, NotFoundException
from app.core.security import get_current_user, require_roles
from app.models.no_read_reason import NoReadReason
from app.models.user import User
from app.schemas.no_read_reason import (
    NoReadReasonCreate,
    NoReadReasonOut,
    NoReadReasonUpdate,
)
from app.services.audit import log_action

router = APIRouter(
    prefix="/catalogos/motivos-no-lectura",
    tags=["Catálogos - Motivos No Lectura"],
)


@router.get("/", response_model=list[NoReadReasonOut])
async def list_no_read_reasons(
    session: SessionDep,
    current_user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    activo: bool | None = Query(None),
):
    query = select(NoReadReason)

    if activo is not None:
        query = query.where(NoReadReason.activo == activo)

    query = query.offset(skip).limit(limit).order_by(NoReadReason.codigo)
    result = await session.execute(query)
    reasons = list(result.scalars().all())
    return reasons


@router.get("/{reason_id}", response_model=NoReadReasonOut)
async def get_no_read_reason(
    session: SessionDep,
    reason_id: UUID,
    current_user: User = Depends(get_current_user),
):
    result = await session.execute(
        select(NoReadReason).where(NoReadReason.id == reason_id)
    )
    reason = result.scalar_one_or_none()
    if not reason:
        raise NotFoundException("Motivo no lectura")
    return reason


@router.post("/", response_model=NoReadReasonOut, status_code=201)
async def create_no_read_reason(
    session: SessionDep,
    payload: NoReadReasonCreate,
    current_user: User = Depends(require_roles("admin", "supervisor")),
):
    existing = await session.execute(
        select(NoReadReason).where(NoReadReason.codigo == payload.codigo)
    )
    if existing.scalar_one_or_none():
        raise DuplicateException("Motivo no lectura")

    reason = NoReadReason(
        codigo=payload.codigo,
        descripcion=payload.descripcion,
        activo=payload.activo,
    )
    session.add(reason)
    await session.flush()

    await log_action(
        session, accion="no_read_reason.create", entidad_tipo="no_read_reason",
        entidad_id=reason.id, actor_id=str(current_user.id),
        detalle={"codigo": reason.codigo},
    )

    return reason


@router.patch("/{reason_id}", response_model=NoReadReasonOut)
async def update_no_read_reason(
    session: SessionDep,
    reason_id: UUID,
    payload: NoReadReasonUpdate,
    current_user: User = Depends(require_roles("admin", "supervisor")),
):
    result = await session.execute(
        select(NoReadReason).where(NoReadReason.id == reason_id)
    )
    reason = result.scalar_one_or_none()
    if not reason:
        raise NotFoundException("Motivo no lectura")

    update_data = payload.model_dump(exclude_unset=True)

    if "codigo" in update_data:
        dup = await session.execute(
            select(NoReadReason).where(
                NoReadReason.codigo == update_data["codigo"],
                NoReadReason.id != reason_id,
            )
        )
        if dup.scalar_one_or_none():
            raise DuplicateException("Motivo no lectura")

    for key, value in update_data.items():
        setattr(reason, key, value)

    await session.flush()

    await log_action(
        session, accion="no_read_reason.update", entidad_tipo="no_read_reason",
        entidad_id=reason.id, actor_id=str(current_user.id),
        detalle={"updated_fields": list(update_data.keys())},
    )

    return reason


@router.delete("/{reason_id}", status_code=204)
async def delete_no_read_reason(
    session: SessionDep,
    reason_id: UUID,
    current_user: User = Depends(require_roles("admin", "supervisor")),
):
    result = await session.execute(
        select(NoReadReason).where(NoReadReason.id == reason_id)
    )
    reason = result.scalar_one_or_none()
    if not reason:
        raise NotFoundException("Motivo no lectura")

    await session.delete(reason)
    await log_action(
        session, accion="no_read_reason.delete", entidad_tipo="no_read_reason",
        entidad_id=reason.id, actor_id=str(current_user.id),
    )
