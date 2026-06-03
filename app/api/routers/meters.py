from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import SessionDep
from app.core.exceptions import NotFoundException
from app.core.security import get_current_user, require_roles
from app.models.meter import Meter
from app.models.ruta import Ruta
from app.models.ruta_asignada import RutaAsignada
from app.models.reading import Reading
from app.models.user import User
from app.schemas.meter import MeterCreate, MeterOut, MeterOutDetailed, MeterUpdate
from app.schemas.reading import ReadingOut
from app.services.audit import log_action

router = APIRouter(prefix="/meters", tags=["Medidores"])


@router.get("/mis-rutas", response_model=list[MeterOut])
async def mis_rutas(
    session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    subq = select(RutaAsignada.ruta_id).where(
        RutaAsignada.lector_id == current_user.id
    )
    result = await session.execute(
        select(Meter)
        .where(Meter.ruta_id.in_(subq))
        .order_by(Meter.ruta_id, Meter.orden)
    )
    return list(result.scalars().all())


@router.get("/mis-rutas/orden", response_model=list[MeterOut])
async def mis_rutas_orden(
    session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    subq = select(RutaAsignada.ruta_id).where(
        RutaAsignada.lector_id == current_user.id
    )
    result = await session.execute(
        select(Meter)
        .where(Meter.ruta_id.in_(subq))
        .order_by(Meter.ruta_id, Meter.orden.nullslast(), Meter.codigo_medidor)
    )
    return list(result.scalars().all())


@router.get("/", response_model=list[MeterOut])
async def list_meters(
    session: SessionDep,
    current_user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    estado: str | None = Query(None),
    tipo: str | None = Query(None),
    vereda: str | None = Query(None),
    ruta: str | None = Query(None),
    lector_id: UUID | None = Query(None),
):
    query = select(Meter)

    if estado:
        query = query.where(Meter.estado == estado)
    if tipo:
        query = query.where(Meter.tipo == tipo)
    if vereda:
        query = query.where(Meter.vereda == vereda)
    if ruta:
        query = query.where(Meter.ruta == ruta)
    if lector_id:
        query = query.where(Meter.lector_id == lector_id)

    # Lector solo ve sus medidores; supervisor/admin ve todos
    if current_user.rol == "lector":
        query = query.where(Meter.lector_id == current_user.id)

    query = query.offset(skip).limit(limit).order_by(Meter.codigo_medidor)
    result = await session.execute(query)
    return list(result.scalars().all())


@router.get("/{meter_id}", response_model=MeterOutDetailed)
async def get_meter(
    session: SessionDep,
    meter_id: UUID,
    current_user: User = Depends(get_current_user),
):
    result = await session.execute(
        select(Meter).where(Meter.id == meter_id)
    )
    meter = result.scalar_one_or_none()
    if not meter:
        raise NotFoundException("Medidor")

    # Cargar lecturas asociadas
    readings_result = await session.execute(
        select(Reading)
        .where(Reading.meter_id == meter_id)
        .order_by(Reading.fecha_lectura.desc())
        .limit(20)
    )
    meter.readings = list(readings_result.scalars().all())

    return meter


@router.get("/{meter_id}/history", summary="Historial de lecturas del medidor")
async def get_meter_history(
    session: SessionDep,
    meter_id: UUID,
    current_user: User = Depends(get_current_user),
    limit: int = Query(10, ge=1, le=100),
):
    # Verificar que el medidor existe
    meter_result = await session.execute(
        select(Meter).where(Meter.id == meter_id)
    )
    meter = meter_result.scalar_one_or_none()
    if not meter:
        raise NotFoundException("Medidor")

    readings_result = await session.execute(
        select(Reading)
        .where(Reading.meter_id == meter_id)
        .where(Reading.estado_validacion == "validada")
        .order_by(Reading.fecha_lectura.desc())
        .limit(limit)
    )
    readings = list(readings_result.scalars().all())

    # Calcular estadísticas
    valores = [r.lectura_actual for r in readings if r.lectura_actual is not None]
    stats = {}
    if valores:
        stats["promedio"] = round(sum(valores) / len(valores), 2)
        stats["min"] = min(valores)
        stats["max"] = max(valores)
        if len(valores) > 1:
            stats["desviacion_std"] = round(
                (sum((v - stats["promedio"]) ** 2 for v in valores) / len(valores)) ** 0.5,
                2,
            )

    return {
        "medidor": {"codigo": meter.codigo_medidor, "niud": meter.niud, "direccion": meter.direccion},
        "stats": stats,
        "lecturas": readings,
    }


@router.get("/{niud}/promedio-historico")
async def get_meter_historical_average(
    session: SessionDep,
    niud: str,
    current_user: User = Depends(get_current_user),
):
    from datetime import date, timedelta

    # Buscar medidor por niud
    meter_result = await session.execute(
        select(Meter).where(Meter.niud == niud)
    )
    meter = meter_result.scalar_one_or_none()
    if not meter:
        raise NotFoundException("Medidor")

    # Fecha hace 30 días
    fecha_desde = date.today() - timedelta(days=30)

    # Promedio de consumo válido (consumo > 0, estado validada) de los últimos 30 días
    result = await session.execute(
        select(func.avg(Reading.consumo))
        .where(Reading.meter_id == meter.id)
        .where(Reading.consumo.isnot(None))
        .where(Reading.consumo > 0)
        .where(Reading.estado_validacion == "validada")
        .where(Reading.fecha_lectura >= fecha_desde)
    )
    promedio = result.scalar_one_or_none()

    return {
        "niud": niud,
        "promedio_consumo_ultimos_30_dias": round(float(promedio), 2) if promedio is not None else 0.0,
        "fecha_desde": fecha_desde.isoformat(),
        "fecha_hasta": date.today().isoformat(),
    }


@router.post("/", response_model=MeterOut, status_code=201)
async def create_meter(
    session: SessionDep,
    payload: MeterCreate,
    current_user: User = Depends(get_current_user),
):
    meter = Meter(
        codigo_medidor=payload.codigo_medidor,
        niud=payload.niud,
        direccion=payload.direccion,
        vereda=payload.vereda,
        ruta=payload.ruta,
        latitud=payload.latitud,
        longitud=payload.longitud,
        gps_json=payload.gps_json.model_dump() if payload.gps_json else None,
        estado=payload.estado,
        tipo=payload.tipo,
        lector_id=payload.lector_id or current_user.id,
    )
    session.add(meter)
    await session.flush()

    await log_action(
        session, accion="meter.create", entidad_tipo="meter",
        entidad_id=meter.id, actor_id=str(current_user.id),
        detalle={"codigo": meter.codigo_medidor},
    )

    return meter


@router.patch("/{meter_id}", response_model=MeterOut)
async def update_meter(
    session: SessionDep,
    meter_id: UUID,
    payload: MeterUpdate,
    current_user: User = Depends(get_current_user),
):
    result = await session.execute(select(Meter).where(Meter.id == meter_id))
    meter = result.scalar_one_or_none()
    if not meter:
        raise NotFoundException("Medidor")

    update_data = payload.model_dump(exclude_unset=True)
    if "gps_json" in update_data and update_data["gps_json"]:
        update_data["gps_json"] = update_data["gps_json"].model_dump()

    for key, value in update_data.items():
        if hasattr(meter, key):
            setattr(meter, key, value)

    await session.flush()

    await log_action(
        session, accion="meter.update", entidad_tipo="meter",
        entidad_id=meter.id, actor_id=str(current_user.id),
        detalle={"updated_fields": list(update_data.keys())},
    )

    return meter


@router.delete("/{meter_id}", status_code=204)
async def delete_meter(
    session: SessionDep,
    meter_id: UUID,
    current_user: User = Depends(require_roles("admin", "supervisor")),
):
    result = await session.execute(select(Meter).where(Meter.id == meter_id))
    meter = result.scalar_one_or_none()
    if not meter:
        raise NotFoundException("Medidor")

    await session.delete(meter)
    await log_action(
        session, accion="meter.delete", entidad_tipo="meter",
        entidad_id=meter.id, actor_id=str(current_user.id),
    )
