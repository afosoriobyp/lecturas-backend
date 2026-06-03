from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import SessionDep
from app.core.exceptions import NotFoundException, ValidationException
from app.core.security import get_current_user, require_roles
from app.models.meter import Meter
from app.models.no_read_reason import NoReadReason
from app.models.reading import Reading
from app.models.user import User
from app.schemas.reading import ReadingCreate, ReadingOut, ReadingUpdate
from app.schemas.reading_extra import ReadingEstadoUpdate, ReadingObservacionAdmin
from app.services.audit import log_action

router = APIRouter(prefix="/readings", tags=["Lecturas"])


@router.get("/revisar", response_model=list[ReadingOut])
async def list_readings_to_review(
    session: SessionDep,
    current_user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
):
    query = select(Reading).where(
        Reading.estado_validacion == "requiere_revision"
    )
    if current_user.rol == "lector":
        query = query.where(Reading.lector_id == current_user.id)
    query = query.order_by(Reading.fecha_lectura.desc()).offset(skip).limit(limit)
    result = await session.execute(query)
    return list(result.scalars().all())


@router.get("/", response_model=list[ReadingOut])
async def list_readings(
    session: SessionDep,
    current_user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    meter_id: UUID | None = None,
    lector_id: UUID | None = None,
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    estado_validacion: str | None = Query(None),
):
    query = select(Reading)

    if meter_id:
        query = query.where(Reading.meter_id == meter_id)
    if lector_id:
        query = query.where(Reading.lector_id == lector_id)
    if fecha_desde:
        query = query.where(Reading.fecha_lectura >= fecha_desde)
    if fecha_hasta:
        query = query.where(Reading.fecha_lectura <= fecha_hasta)
    if estado_validacion:
        query = query.where(Reading.estado_validacion == estado_validacion)

    # Lector solo ve sus lecturas
    if current_user.rol == "lector":
        query = query.where(Reading.lector_id == current_user.id)

    query = query.order_by(Reading.fecha_lectura.desc()).offset(skip).limit(limit)
    result = await session.execute(query)
    return list(result.scalars().all())


@router.get("/{reading_id}", response_model=ReadingOut)
async def get_reading(
    session: SessionDep,
    reading_id: UUID,
    current_user: User = Depends(get_current_user),
):
    result = await session.execute(
        select(Reading).where(Reading.id == reading_id)
    )
    reading = result.scalar_one_or_none()
    if not reading:
        raise NotFoundException("Lectura")
    return reading


@router.post("/", response_model=ReadingOut, status_code=201)
async def create_reading(
    session: SessionDep,
    payload: ReadingCreate,
    current_user: User = Depends(get_current_user),
):
    # Validar que el medidor existe
    meter_result = await session.execute(
        select(Meter).where(Meter.id == payload.meter_id)
    )
    meter = meter_result.scalar_one_or_none()
    if not meter:
        raise NotFoundException("Medidor")

    if meter.estado != "activo":
        raise ValidationException(
            f"Medidor en estado '{meter.estado}' — no se pueden registrar lecturas"
        )

    # Obtener lectura anterior (obligatorio)
    lectura_anterior = payload.lectura_anterior
    lectura_actual = payload.lectura_actual

    # Calcular consumo
    consumo = lectura_actual - lectura_anterior if lectura_actual is not None and lectura_anterior is not None else None

    # Obtener promedio histórico del medidor (últimas 30 lecturas válidas)
    promedio_historico = None
    if consumo is not None and consumo > 0:
        historial_result = await session.execute(
            select(Reading.consumo)
            .where(
                Reading.meter_id == meter.id,
                Reading.consumo.isnot(None),
                Reading.consumo > 0,
                Reading.estado_validacion == "validada",
                Reading.id != None  # placeholder to avoid empty query
            )
            .order_by(Reading.fecha_lectura.desc())
            .limit(30)
        )
        consumos_hist = [float(r.consumo) for r in historial_result.scalars().all() if r.consumo is not None]
        if consumos_hist:
            promedio_historico = sum(consumos_hist) / len(consumos_hist)

    # Determinar categoría de consumo
    consumo_calculado = consumo
    consumo_categoria = None
    porcentaje = None

    if consumo is not None:
        if consumo <= 0:
            consumo_categoria = "Girado Sentido Contrario"
        elif promedio_historico is not None and promedio_historico > 0:
            porcentaje = (consumo / promedio_historico) * 100
            if porcentaje <= 50:
                consumo_categoria = "Consumo Bajo"
            elif porcentaje <= 100:
                consumo_categoria = "Consumo Normal"
            elif porcentaje <= 150:
                consumo_categoria = "Consumo Alto"
            else:  # porcentaje > 150
                consumo_categoria = "Consumo Elevado"

    reading = Reading(
        meter_id=payload.meter_id,
        lector_id=payload.lector_id or current_user.id,
        lectura_anterior=lectura_anterior,
        lectura_actual=lectura_actual,
        consumo=consumo,
        consumo_calculado=consumo_calculado,
        consumo_categoria=consumo_categoria,
        promedio_historico_usado=promedio_historico,
        timestamp_validacion=datetime.now(timezone.utc),
        usuario_id=current_user.id,
        version_app="1.0.0",  # This could come from settings
        fecha_lectura=payload.fecha_lectura,
        gps_json=payload.gps_json.model_dump() if payload.gps_json else None,
        foto_url=payload.foto_url,
        observaciones=payload.observaciones,
        metodo_captura=payload.metodo_captura,
        motivo_no_lectura_id=payload.motivo_no_lectura_id,
        estado_sync="synced",
        estado_validacion="validada" if consumo_categoria != "Girado Sentido Contrario" else "requiere_revision",
    )
    session.add(reading)
    await session.flush()

    await log_action(
        session, accion="reading.create", entidad_tipo="reading",
        entidad_id=reading.id, actor_id=str(current_user.id),
        detalle={
            "meter_id": str(payload.meter_id),
            "lectura_anterior": lectura_anterior,
            "lectura_actual": lectura_actual,
            "consumo": consumo,
            "consumo_calculado": consumo_calculado,
            "consumo_categoria": consumo_categoria,
            "promedio_historico_usado": promedio_historico,
            "porcentaje": porcentaje,
        },
    )

    return reading


@router.patch("/{reading_id}/estado", response_model=ReadingOut)
async def update_reading_estado(
    session: SessionDep,
    reading_id: UUID,
    payload: ReadingEstadoUpdate,
    current_user: User = Depends(require_roles("admin", "supervisor", "auditor")),
):
    result = await session.execute(
        select(Reading).where(Reading.id == reading_id)
    )
    reading = result.scalar_one_or_none()
    if not reading:
        raise NotFoundException("Lectura")

    old_estado = reading.estado_validacion
    reading.estado_validacion = payload.estado_validacion
    await session.flush()

    await log_action(
        session, accion="reading.estado_update", entidad_tipo="reading",
        entidad_id=reading.id, actor_id=str(current_user.id),
        detalle={
            "desde": old_estado,
            "hasta": payload.estado_validacion,
        },
    )

    return reading


@router.post("/{reading_id}/observacion-admin", response_model=ReadingOut)
async def add_observacion_admin(
    session: SessionDep,
    reading_id: UUID,
    payload: ReadingObservacionAdmin,
    current_user: User = Depends(require_roles("admin", "supervisor")),
):
    result = await session.execute(
        select(Reading).where(Reading.id == reading_id)
    )
    reading = result.scalar_one_or_none()
    if not reading:
        raise NotFoundException("Lectura")

    prev = reading.observaciones_admin
    nueva = f"[{current_user.username}] {payload.observacion}"
    reading.observaciones_admin = (
        f"{prev}\n{nueva}" if prev else nueva
    )
    await session.flush()

    await log_action(
        session, accion="reading.observacion_admin", entidad_tipo="reading",
        entidad_id=reading.id, actor_id=str(current_user.id),
        detalle={"observacion": payload.observacion},
    )

    return reading


@router.patch("/{reading_id}", response_model=ReadingOut)
async def update_reading(
    session: SessionDep,
    reading_id: UUID,
    payload: ReadingUpdate,
    current_user: User = Depends(require_roles("admin", "supervisor")),
):
    result = await session.execute(
        select(Reading).where(Reading.id == reading_id)
    )
    reading = result.scalar_one_or_none()
    if not reading:
        raise NotFoundException("Lectura")

    update_data = payload.model_dump(exclude_unset=True)
    if "gps_json" in update_data and update_data["gps_json"]:
        update_data["gps_json"] = update_data["gps_json"].model_dump()

    for key, value in update_data.items():
        if hasattr(reading, key):
            setattr(reading, key, value)

    await log_action(
        session, accion="reading.update", entidad_tipo="reading",
        entidad_id=reading.id, actor_id=str(current_user.id),
        detalle={"updated": list(update_data.keys())},
    )

    return reading


@router.delete("/{reading_id}", status_code=204)
async def delete_reading(
    session: SessionDep,
    reading_id: UUID,
    current_user: User = Depends(require_roles("admin", "supervisor")),
):
    result = await session.execute(
        select(Reading).where(Reading.id == reading_id)
    )
    reading = result.scalar_one_or_none()
    if not reading:
        raise NotFoundException("Lectura")

    await session.delete(reading)
    await log_action(
        session, accion="reading.delete", entidad_tipo="reading",
        entidad_id=reading.id, actor_id=str(current_user.id),
    )
