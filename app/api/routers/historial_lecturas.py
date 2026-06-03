from __future__ import annotations

import csv
import io
import json
import os
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, Query, UploadFile, File, HTTPException, Response
from sqlalchemy import cast, delete, Integer, select, text

from app.api.dependencies import SessionDep
from app.core.config import settings
from app.core.exceptions import ForbiddenException, NotFoundException
from app.core.security import get_current_user, require_roles
from app.models.historial_lectura import HistorialLectura
from app.models.no_read_reason import NoReadReason
from app.models.user import User
from app.schemas.historial_lectura import HistorialLecturaOut, HistorialLecturaUpdate
from app.services.audit import log_action

router = APIRouter(prefix="/historial-lecturas", tags=["Historial Lecturas"])


def validar_consumo(consumo: float, promedio: float | None) -> dict:
    if consumo <= 0:
        return {"categoria": "Girado Sentido Contrario", "porcentaje": 0}
    if not promedio or promedio <= 0:
        return {"categoria": None, "porcentaje": None}
    pct = (consumo / promedio) * 100
    if pct <= 50:
        return {"categoria": "Consumo Bajo", "porcentaje": round(pct, 2)}
    elif pct <= 100:
        return {"categoria": "Consumo Normal", "porcentaje": round(pct, 2)}
    elif pct <= 150:
        return {"categoria": "Consumo Alto", "porcentaje": round(pct, 2)}
    else:
        return {"categoria": "Consumo Elevado", "porcentaje": round(pct, 2)}


@router.get("/", response_model=list[HistorialLecturaOut])
async def list_historial_lecturas(
    session: SessionDep,
    current_user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=5000),
    nuis: str | None = Query(None),
    ruta_lectura: str | None = Query(None),
    nom_suscriptor: str | None = Query(None),
):
    query = select(HistorialLectura)

    if current_user.rol == "lector" and current_user.id_tercero:
        query = query.where(HistorialLectura.id_tercero == current_user.id_tercero)

    if nuis:
        query = query.where(HistorialLectura.nuis == nuis)
    if ruta_lectura:
        query = query.where(HistorialLectura.ruta_lectura == ruta_lectura)
    if nom_suscriptor:
        query = query.where(HistorialLectura.nom_suscriptor.ilike(f"%{nom_suscriptor}%"))

    query = query.order_by(cast(HistorialLectura.orden_lectura, Integer)).offset(skip).limit(limit)
    result = await session.execute(query)
    return list(result.scalars().all())


CSV_HEADERS = [
    "LECTURA_ANT", "LECTURA", "CONSUMO", "SOLUCION_CONSUMO", "PROMEDIO",
    "ID_NOVEDAD", "NOM_SUSCRIPTOR", "SERIAL_MEDIDOR", "NOM_MARCA",
    "ID_CICLO", "ORDEN_LECTURA", "RUTA_LECTURA",
    "CONSUMO_1", "CONSUMO_2", "CONSUMO_3",
]

COLUMN_MAP = {
    "LECTURA_ANT": "lectura_ant",
    "LECTURA": "lectura",
    "CONSUMO": "consumo",
    "SOLUCION_CONSUMO": "solucion_consumo",
    "PROMEDIO": "promedio",
    "ID_NOVEDAD": "id_novedad",
    "NOM_SUSCRIPTOR": "nom_suscriptor",
    "SERIAL_MEDIDOR": "serial_medidor",
    "NOM_MARCA": "nom_marca",
    "ID_CICLO": "id_ciclo",
    "ORDEN_LECTURA": "orden_lectura",
    "RUTA_LECTURA": "ruta_lectura",
    "CONSUMO_1": "consumo_1",
    "CONSUMO_2": "consumo_2",
    "CONSUMO_3": "consumo_3",
}

LOOKUP_FIELDS = ["ID_CICLO", "ORDEN_LECTURA", "RUTA_LECTURA"]

IMPORT_COLUMNS = ["LECTURA", "CONSUMO", "SOLUCION_CONSUMO", "ID_NOVEDAD"]


@router.get("/export")
async def export_historial_lecturas_csv(
    session: SessionDep,
    current_user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(5000, ge=1, le=50000),
    nuis: str | None = Query(None),
    nom_suscriptor: str | None = Query(None),
):
    query = select(HistorialLectura)

    if current_user.rol == "lector" and current_user.id_tercero:
        query = query.where(HistorialLectura.id_tercero == current_user.id_tercero)

    if nuis:
        query = query.where(HistorialLectura.nuis == nuis)
    if nom_suscriptor:
        query = query.where(HistorialLectura.nom_suscriptor.ilike(f"%{nom_suscriptor}%"))

    query = query.order_by(cast(HistorialLectura.orden_lectura, Integer)).offset(skip).limit(limit)
    result = await session.execute(query)
    rows = list(result.scalars().all())

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(CSV_HEADERS)

    for r in rows:
        writer.writerow([
            r.lectura_ant,
            r.lectura,
            r.consumo,
            r.solucion_consumo,
            r.promedio,
            r.id_novedad,
            r.nom_suscriptor,
            r.serial_medidor,
            r.nom_marca,
            r.id_ciclo,
            r.orden_lectura,
            r.ruta_lectura,
            r.consumo_1,
            r.consumo_2,
            r.consumo_3,
        ])

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=\"historial_lecturas.csv\""},
    )


@router.patch("/{id_lectura}", response_model=HistorialLecturaOut)
async def update_historial_lectura(
    session: SessionDep,
    id_lectura: str,
    payload: HistorialLecturaUpdate,
    current_user: User = Depends(get_current_user),
):
    if current_user.rol not in ("lector", "admin", "supervisor"):
        raise ForbiddenException("No autorizado")

    result = await session.execute(
        select(HistorialLectura).where(HistorialLectura.id_lectura == id_lectura)
    )
    historial = result.scalar_one_or_none()
    if not historial:
        raise NotFoundException("HistorialLectura")

    update_data: dict[str, object] = {}

    if payload.lectura is not None:
        update_data["lectura"] = payload.lectura
        lectura_ant = historial.lectura_ant or 0
        update_data["consumo"] = payload.lectura - lectura_ant
    elif payload.consumo is not None:
        update_data["consumo"] = payload.consumo

    if payload.id_novedad is not None and payload.id_novedad != "":
        update_data["id_novedad"] = payload.id_novedad
        motivo_result = await session.execute(
            text("SELECT sugiere_promedio FROM no_read_reasons WHERE codigo = CAST(:codigo AS integer)"),
            {"codigo": int(payload.id_novedad)},
        )
        row = motivo_result.one_or_none()
        if row:
            update_data["solucion_consumo"] = (
                "POR PROMEDIO" if row.sugiere_promedio.strip().upper() == "S" else "POR DIFERENCIA"
            )
    elif payload.id_novedad == "" and payload.solucion_consumo is None:
        update_data["id_novedad"] = None
        update_data["solucion_consumo"] = None

    if payload.solucion_consumo is not None:
        update_data["solucion_consumo"] = payload.solucion_consumo

    if payload.status is not None:
        update_data["status"] = payload.status

    if payload.observacion is not None:
        update_data["observacion"] = payload.observacion

    if payload.fecha is not None:
        update_data["fecha"] = payload.fecha

    if payload.fotos is not None:
        update_data["fotos"] = json.dumps(payload.fotos)

    if payload.fotos_pendientes is not None:
        update_data["fotos_pendientes"] = payload.fotos_pendientes

    for key, value in update_data.items():
        setattr(historial, key, value)

    await session.flush()
    await session.refresh(historial)

    consumo = historial.consumo
    promedio = historial.promedio
    validacion = validar_consumo(consumo, promedio) if consumo is not None else {}

    await log_action(
        session, accion="historial_lectura.update", entidad_tipo="historial_lectura",
        entidad_id=id_lectura, actor_id=str(current_user.id),
        detalle={k: str(v) for k, v in update_data.items()},
    )

    if validacion.get("categoria"):
        await log_action(
            session, accion="historial_lectura.validation", entidad_tipo="historial_lectura",
            entidad_id=id_lectura, actor_id=str(current_user.id),
            detalle={
                "categoria": validacion["categoria"],
                "porcentaje": validacion.get("porcentaje"),
                "consumo": consumo,
                "promedio": promedio,
                "version_app": "1.0.0",
            },
        )

    return historial


@router.get("/{id_lectura}", response_model=HistorialLecturaOut)
async def get_historial_lectura(
    session: SessionDep,
    id_lectura: str,
    current_user: User = Depends(get_current_user),
):
    result = await session.execute(
        select(HistorialLectura).where(HistorialLectura.id_lectura == id_lectura)
    )
    historial = result.scalar_one_or_none()
    if not historial:
        raise NotFoundException("HistorialLectura")
    return historial


@router.post("/{id_lectura}/fotos", response_model=dict)
async def upload_fotos(
    id_lectura: str,
    session: SessionDep,
    files: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
):
    if current_user.rol not in ("lector", "admin", "supervisor"):
        raise ForbiddenException("No autorizado")

    result = await session.execute(
        select(HistorialLectura).where(HistorialLectura.id_lectura == id_lectura)
    )
    historial = result.scalar_one_or_none()
    if not historial:
        raise NotFoundException("HistorialLectura")

    if len(files) > settings.MAX_FOTOS_PER_LECTURA:
        raise HTTPException(
            status_code=400,
            detail=f"Máximo {settings.MAX_FOTOS_PER_LECTURA} fotos permitidas",
        )

    existing_fotos: list[str] = []
    if historial.fotos:
        try:
            existing_fotos = json.loads(historial.fotos)
        except (json.JSONDecodeError, TypeError):
            existing_fotos = []

    total_fotos = len(existing_fotos) + len(files)
    if total_fotos > settings.MAX_FOTOS_PER_LECTURA:
        raise HTTPException(
            status_code=400,
            detail=f"Máximo {settings.MAX_FOTOS_PER_LECTURA} fotos permitidas. Ya tienes {len(existing_fotos)}.",
        )

    for file in files:
        if file.content_type not in settings.ALLOWED_IMAGE_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Tipo de archivo no permitido: {file.content_type}. Permitidos: {settings.ALLOWED_IMAGE_TYPES}",
            )

        content = await file.read()
        if len(content) > settings.MAX_IMAGE_SIZE_MB * 1024 * 1024:
            raise HTTPException(
                status_code=400,
                detail=f"Archivo muy grande. Máximo {settings.MAX_IMAGE_SIZE_MB}MB",
            )

    id_predio = historial.id_predio or "sin_predio"
    upload_dir = Path(settings.UPLOAD_DIR) / "historial-lecturas" / id_predio
    upload_dir.mkdir(parents=True, exist_ok=True)

    next_index = len(existing_fotos) + 1
    new_fotos = []

    for file in files:
        ext = file.filename.rsplit(".", 1)[-1] if "." in file.filename else "jpg"
        filename = f"{id_predio}_{next_index}.{ext}"
        filepath = upload_dir / filename

        with open(filepath, "wb") as f:
            f.write(await file.read())

        new_fotos.append(filename)
        next_index += 1

    all_fotos = existing_fotos + new_fotos
    historial.fotos = json.dumps(all_fotos)
    historial.fotos_pendientes = 0

    await session.flush()

    await log_action(
        session,
        accion="historial_lectura.upload_fotos",
        entidad_tipo="historial_lectura",
        entidad_id=id_lectura,
        actor_id=str(current_user.id),
        detalle={"fotos_subidas": len(new_fotos), "total_fotos": len(all_fotos)},
    )

    return {"fotos": all_fotos}


@router.delete("/{id_lectura}/fotos", response_model=dict)
async def delete_fotos(
    id_lectura: str,
    session: SessionDep,
    filenames: str = Query(..., description="Comma-separated list of filenames to delete"),
    current_user: User = Depends(get_current_user),
):
    if current_user.rol not in ("lector", "admin", "supervisor"):
        raise ForbiddenException("No autorizado")

    result = await session.execute(
        select(HistorialLectura).where(HistorialLectura.id_lectura == id_lectura)
    )
    historial = result.scalar_one_or_none()
    if not historial:
        raise NotFoundException("HistorialLectura")

    if not historial.fotos:
        raise HTTPException(status_code=404, detail="No hay fotos para eliminar")

    try:
        existing_fotos: list[str] = json.loads(historial.fotos)
    except (json.JSONDecodeError, TypeError):
        raise HTTPException(status_code=500, detail="Error al leer las fotos almacenadas")

    files_to_delete = [f.strip() for f in filenames.split(",") if f.strip()]
    remaining_fotos = [f for f in existing_fotos if f not in files_to_delete]

    id_predio = historial.id_predio or "sin_predio"
    upload_dir = Path(settings.UPLOAD_DIR) / "historial-lecturas" / id_predio

    for filename in files_to_delete:
        filepath = upload_dir / filename
        if filepath.exists():
            filepath.unlink()

    reindexed_fotos = []
    for idx, foto in enumerate(remaining_fotos, start=1):
        ext = foto.rsplit(".", 1)[-1] if "." in foto else "jpg"
        new_filename = f"{id_predio}_{idx}.{ext}"
        old_filepath = upload_dir / foto
        new_filepath = upload_dir / new_filename

        if old_filepath.exists() and old_filepath != new_filepath:
            old_filepath.rename(new_filepath)

        reindexed_fotos.append(new_filename)

    historial.fotos = json.dumps(reindexed_fotos)

    await session.flush()

    await log_action(
        session,
        accion="historial_lectura.delete_fotos",
        entidad_tipo="historial_lectura",
        entidad_id=id_lectura,
        actor_id=str(current_user.id),
        detalle={"fotos_eliminadas": len(files_to_delete), "total_fotos": len(reindexed_fotos)},
    )

    return {"fotos": reindexed_fotos}


@router.post("/import")
async def import_historial_lecturas_csv(
    session: SessionDep,
    current_user: User = Depends(require_roles("admin", "supervisor")),
    archivo: UploadFile = File(...),
):
    if not archivo.filename or not archivo.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="El archivo debe tener extensión .csv")

    content = await archivo.read()
    try:
        decoded = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        decoded = content.decode("latin-1")

    reader = csv.DictReader(io.StringIO(decoded))
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="CSV vacío o sin encabezados")

    csv_headers = [h.strip().upper() for h in reader.fieldnames]

    missing = [h for h in LOOKUP_FIELDS if h not in csv_headers]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Faltan columnas obligatorias en el CSV: {', '.join(missing)}",
        )

    detalles: list[str] = []
    procesados = 0
    errores = 0
    total = 0

    for idx, row in enumerate(reader, start=1):
        total += 1
        try:
            id_ciclo = row.get("ID_CICLO", "").strip()
            orden_lectura = row.get("ORDEN_LECTURA", "").strip()
            ruta_lectura = row.get("RUTA_LECTURA", "").strip()

            if not id_ciclo or not orden_lectura or not ruta_lectura:
                detalles.append(f"fila {idx}: ID_CICLO, ORDEN_LECTURA y RUTA_LECTURA son requeridos")
                errores += 1
                continue

            result = await session.execute(
                select(HistorialLectura).where(
                    HistorialLectura.id_ciclo == id_ciclo,
                    HistorialLectura.orden_lectura == orden_lectura,
                    HistorialLectura.ruta_lectura == ruta_lectura,
                )
            )
            historial = result.scalar_one_or_none()

            if not historial:
                serial = row.get("SERIAL_MEDIDOR", "").strip()
                if serial:
                    result = await session.execute(
                        select(HistorialLectura).where(
                            HistorialLectura.serial_medidor == serial,
                        )
                    )
                    historial = result.scalar_one_or_none()

            if not historial:
                detalles.append(f"fila {idx}: registro no encontrado")
                errores += 1
                continue

            update_data: dict[str, object] = {}

            lectura_raw = row.get("LECTURA", "").strip()
            if lectura_raw:
                try:
                    lectura_val = float(lectura_raw)
                    update_data["lectura"] = lectura_val
                    lectura_ant = historial.lectura_ant or 0
                    update_data["consumo"] = lectura_val - lectura_ant
                except ValueError:
                    detalles.append(f"fila {idx}: LECTURA inválido '{lectura_raw}'")
                    errores += 1
                    continue

            consumo_raw = row.get("CONSUMO", "").strip()
            if consumo_raw and "lectura" not in update_data:
                try:
                    update_data["consumo"] = float(consumo_raw)
                except ValueError:
                    detalles.append(f"fila {idx}: CONSUMO inválido '{consumo_raw}'")
                    errores += 1
                    continue

            solucion_raw = row.get("SOLUCION_CONSUMO", "").strip()
            if solucion_raw:
                update_data["solucion_consumo"] = solucion_raw

            id_novedad_raw = row.get("ID_NOVEDAD", "").strip()
            if id_novedad_raw:
                update_data["id_novedad"] = id_novedad_raw

            for key, value in update_data.items():
                setattr(historial, key, value)

            procesados += 1

        except Exception as exc:
            detalles.append(f"fila {idx}: error interno - {exc}")
            errores += 1

    if procesados > 0:
        await session.flush()
        await log_action(
            session,
            accion="historial_lectura.import_csv",
            entidad_tipo="historial_lectura",
            actor_id=str(current_user.id),
            detalle={"procesados": procesados, "errores": errores, "total": total},
        )

    return {"procesados": procesados, "errores": errores, "total": total, "detalles": detalles}


@router.delete("/all")
async def delete_all_historial_lecturas(
    session: SessionDep,
    current_user: User = Depends(require_roles("admin", "supervisor")),
):
    result = await session.execute(select(HistorialLectura).limit(1))
    if result.first() is None:
        return {"eliminados": 0, "message": "No hay registros para eliminar"}

    result = await session.execute(delete(HistorialLectura))
    count = result.rowcount

    await log_action(
        session,
        accion="historial_lectura.delete_all",
        entidad_tipo="historial_lectura",
        actor_id=str(current_user.id),
        detalle={"eliminados": count},
    )

    return {"eliminados": count, "message": f"Se eliminaron {count} registros"}
