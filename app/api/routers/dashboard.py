from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import and_, case, select, func

from app.api.dependencies import SessionDep
from app.core.security import get_current_user, require_roles
from app.models.audit_log import AuditLog
from app.models.historial_lectura import HistorialLectura
from app.models.meter import Meter
from app.models.reading import Reading
from app.models.sync_job import SyncJob
from app.models.user import User

router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"],
)


@router.get("/lector")
async def dashboard_lector(
    session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    today = date.today()
    id_tercero = current_user.id_tercero

    filters = []
    if id_tercero:
        filters.append(HistorialLectura.id_tercero == id_tercero)

    row = await session.execute(
        select(
            func.count(HistorialLectura.id_lectura).label("total"),
            func.sum(case((HistorialLectura.fecha == today, 1), else_=0)).label("lecturas_hoy"),
            func.sum(case((HistorialLectura.status == "pendiente", 1), else_=0)).label("pendientes"),
            func.sum(case((HistorialLectura.status == "completado", 1), else_=0)).label("completados"),
            func.sum(case(
                (and_(HistorialLectura.fecha == today, HistorialLectura.id_novedad.isnot(None)), 1),
                else_=0
            )).label("sin_lectura_hoy"),
        ).select_from(HistorialLectura).where(*filters)
    )
    r = row.one()

    total_medidores = await session.scalar(
        select(func.count(Meter.id)).where(Meter.lector_id == current_user.id)
    )

    return {
        "lecturas_hoy": r.lecturas_hoy or 0,
        "completados": r.completados or 0,
        "pendientes": r.pendientes or 0,
        "total_medidores": total_medidores or 0,
        "sin_lectura_hoy": r.sin_lectura_hoy or 0,
        "_debug": {
            "id_tercero": id_tercero,
            "total": r.total or 0,
        },
    }


@router.get("/admin")
async def dashboard_admin(
    session: SessionDep,
    current_user: User = Depends(require_roles("admin", "supervisor")),
):
    today = date.today()

    row = await session.execute(
        select(
            func.sum(case((HistorialLectura.status == "completado", 1), else_=0)).label("completados"),
            func.sum(case((HistorialLectura.status == "pendiente", 1), else_=0)).label("pendientes"),
            func.sum(case((HistorialLectura.fecha == today, 1), else_=0)).label("lecturas_hoy"),
        ).select_from(HistorialLectura)
    )
    r = row.one()

    total_lecturistas = await session.scalar(
        select(func.count(User.id)).where(User.rol == "lector")
    )

    return {
        "completados": r.completados or 0,
        "pendientes": r.pendientes or 0,
        "lecturas_hoy": r.lecturas_hoy or 0,
        "total_lecturistas": total_lecturistas or 0,
    }


@router.get("/auditor")
async def dashboard_auditor(
    session: SessionDep,
    current_user: User = Depends(require_roles("admin", "supervisor", "auditor")),
):
    total_usuarios = await session.scalar(
        select(func.count(User.id))
    )
    total_medidores = await session.scalar(
        select(func.count(Meter.id))
    )
    total_lecturas = await session.scalar(
        select(func.count(Reading.id))
    )

    total_operaciones = await session.scalar(
        select(func.count(AuditLog.id))
    )

    operaciones_por_accion = await session.execute(
        select(
            AuditLog.accion,
            func.count(AuditLog.id).label("total"),
        )
        .group_by(AuditLog.accion)
        .order_by(func.count(AuditLog.id).desc())
        .limit(20)
    )

    total_syncs = await session.scalar(
        select(func.count(SyncJob.id))
    )

    syncs_ok = await session.scalar(
        select(func.count(SyncJob.id)).where(SyncJob.estado == "completed")
    )

    hoy = date.today()
    cambios_hoy = await session.scalar(
        select(func.count(AuditLog.id)).where(
            AuditLog.timestamp >= datetime.combine(hoy, datetime.min.time(), tzinfo=timezone.utc)
        )
    )

    return {
        "resumen": {
            "total_usuarios": total_usuarios or 0,
            "total_medidores": total_medidores or 0,
            "total_lecturas": total_lecturas or 0,
        },
        "operaciones": {
            "total": total_operaciones or 0,
            "cambios_hoy": cambios_hoy or 0,
            "top_acciones": [
                {"accion": row.accion, "total": row.total}
                for row in operaciones_por_accion.all()
            ],
        },
        "sincronizaciones": {
            "total": total_syncs or 0,
            "exitosas": syncs_ok or 0,
        },
    }
