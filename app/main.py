from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text as sa_text
from sqlalchemy.exc import IntegrityError, InterfaceError, OperationalError, SQLAlchemyError

from app.api.routers.admin import router as admin_router
from app.api.routers.auth import router as auth_router
from app.api.routers.audit import router as audit_router
from app.api.routers.dashboard import router as dashboard_router
from app.api.routers.export import router as export_router
from app.api.routers.historial_lecturas import router as historial_lecturas_router
from app.api.routers.meters import router as meters_router
from app.api.routers.no_read_reasons import router as no_read_reasons_router
from app.api.routers.readings import router as readings_router
from app.api.routers.sync import router as sync_router
from app.core.config import settings
from app.core.database import Base, engine
from app.core.exceptions import BusinessRuleError, DBConstraintError, SyncConflictError
from app.core.log_config import TraceIDMiddleware, error_code_var
from app.core.logging import register_middleware, setup_logging
from app.core.audit_events import register_audit_events
from app.core.security import AuthMiddleware, hash_password
from app.schemas.error import AppError
from app.services.alerts import send_critical_alert
from app.services.telegram import telegram_service

logger = logging.getLogger(__name__)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    register_audit_events()
    logger.info("Tablas sincronizadas — eventos de auditoría registrados")


SEED_USERS = [
    ("admin",       "admin@agua.com",         "admin123",       "Administrador",    "admin"),
    ("supervisor",  "supervisor@agua.com",    "super123",       "Supervisor",       "supervisor"),
    ("lecturista",  "lecturista@ejemplo.com", "lectura123",     "Lecturista Demo",  "lector"),
    ("auditor",     "auditor@agua.com",       "auditor123",     "Auditor",          "auditor"),
    ("nelson",      "nelson@agua.com",        "nelson",         "Nelson",           "lector"),
]

async def seed_default_users():
    try:
        logger.info("Ejecutando seed de usuarios...")
        async with engine.begin() as conn:
            created = 0
            for username, email, password, full_name, rol in SEED_USERS:
                result = await conn.execute(
                    sa_text("SELECT id FROM users WHERE email = :email OR username = :username"),
                    {"email": email, "username": username},
                )
                if result.first():
                    continue
                hashed = hash_password(password)
                await conn.execute(
                    sa_text("""
                        INSERT INTO users (username, email, full_name, hashed_password, rol, is_active)
                        VALUES (:username, :email, :full_name, :password, :rol, true)
                    """),
                    {
                        "username": username,
                        "email": email,
                        "full_name": full_name,
                        "password": hashed,
                        "rol": rol,
                    },
                )
                created += 1
        logger.info("Seed completado. Usuarios creados: %d", created)
    except Exception as e:
        logger.exception("Error creando usuarios semilla: %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("Starting %s v%s", settings.APP_NAME, settings.APP_VERSION)
    await init_db()
    await seed_default_users()
    await telegram_service.initialize()
    yield
    await telegram_service.shutdown()
    logger.info("Application shutdown complete")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.APP_DEBUG,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# ─── CORS ─────────────────────────────────────────────
cors_origins = settings.CORS_ORIGINS
cors_allow_all = cors_origins == ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=not cors_allow_all,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Trace ID middleware (inyecta trace_id en cada request) ─
app.add_middleware(TraceIDMiddleware)

# ─── Auth middleware (inyecta request.user.rol) ──────
app.add_middleware(AuthMiddleware)

# ─── Request logging middleware ───────────────────────
register_middleware(app)


# ─── Exception Handlers ─────────────────────────────

def _make_error(
    request: Request,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
    status_code: int = 500,
) -> JSONResponse:
    trace_id = getattr(request.state, "trace_id", "N/A")
    error_code_var.set(code)
    return JSONResponse(
        status_code=status_code,
        content=AppError(
            code=code,
            message=message,
            details=details or {},
            trace_id=trace_id,
        ).model_dump(mode="json"),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    errors = exc.errors()
    field_errors: dict[str, str] = {}
    for e in errors:
        loc = ".".join(str(x) for x in e.get("loc", []))
        field_errors[loc] = e.get("msg", "Error de validación")
    return _make_error(
        request,
        code="VALIDATION_ERROR",
        message="Error de validación en los datos enviados",
        details={"fields": field_errors, "errors": errors},
        status_code=400,
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(
    request: Request, exc: HTTPException
) -> JSONResponse:
    code_map: dict[int, str] = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        409: "CONFLICT",
        422: "UNPROCESSABLE_ENTITY",
        429: "TOO_MANY_REQUESTS",
    }
    error_code = code_map.get(exc.status_code, f"HTTP_{exc.status_code}")
    raw = exc.detail

    if isinstance(raw, dict):
        if "code" in raw:
            error_code = raw["code"]
        message = raw.get("message", raw.get("detail", str(raw)))
        details = {k: v for k, v in raw.items() if k not in ("code", "message", "detail")}
    else:
        message = str(raw)
        details = {}

    return _make_error(
        request,
        code=error_code,
        message=message,
        details=details,
        status_code=exc.status_code,
    )


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(
    request: Request, exc: SQLAlchemyError
) -> JSONResponse:
    raw = str(exc)
    error_code = "DB_ERROR"
    message = "Error de base de datos"
    details: dict[str, Any] = {"db_error": raw[:500]}
    status_code = 500
    is_critical = False

    if isinstance(exc, IntegrityError):
        if "duplicate key" in raw.lower() or "unique constraint" in raw.lower():
            error_code = "DB_DUPLICATE"
            message = "Registro duplicado — violación de unicidad"
            status_code = 409
        elif "foreign key" in raw.lower():
            error_code = "DB_FOREIGN_KEY"
            message = "Error de clave foránea — referencia inválida"
            status_code = 409
        else:
            error_code = "DB_CONSTRAINT"
            message = "Error de restricción de base de datos"
            status_code = 409
    elif isinstance(exc, OperationalError):
        if "timeout" in raw.lower():
            error_code = "DB_TIMEOUT"
            message = "Tiempo de espera agotado en la consulta"
            status_code = 504
        else:
            error_code = "DB_DOWN"
            message = "Base de datos no disponible"
            status_code = 503
            is_critical = True
    elif isinstance(exc, InterfaceError):
        error_code = "DB_INTERFACE"
        message = "Error de conexión con la base de datos"
        status_code = 503
        is_critical = True

    logger.exception("Error DB [%s]: %s", error_code, raw)

    if is_critical:
        trace_id = getattr(request.state, "trace_id", "N/A")
        await send_critical_alert(
            error_code=error_code,
            message=message,
            details=details,
            trace_id=trace_id,
        )

    return _make_error(
        request,
        code=error_code,
        message=message,
        details=details,
        status_code=status_code,
    )


@app.exception_handler(BusinessRuleError)
async def business_rule_handler(
    request: Request, exc: BusinessRuleError
) -> JSONResponse:
    return _make_error(
        request,
        code=exc.code,
        message=exc.message,
        details=exc.details,
        status_code=422,
    )


@app.exception_handler(SyncConflictError)
async def sync_conflict_handler(
    request: Request, exc: SyncConflictError
) -> JSONResponse:
    return _make_error(
        request,
        code=exc.code,
        message=exc.message,
        details={**exc.details, "options": ["override", "skip"]},
        status_code=409,
    )


@app.exception_handler(DBConstraintError)
async def db_constraint_handler(
    request: Request, exc: DBConstraintError
) -> JSONResponse:
    return _make_error(
        request,
        code=exc.code,
        message=exc.message,
        details=exc.details,
        status_code=409,
    )


@app.exception_handler(Exception)
async def global_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    if isinstance(exc, HTTPException):
        return await http_exception_handler(request, exc)

    logger.exception("Excepción no manejada: %s", exc)
    return _make_error(
        request,
        code="INTERNAL_ERROR",
        message="Error interno del servidor",
        status_code=500,
    )


# ─── Routers ──────────────────────────────────────────
app.include_router(admin_router, prefix=settings.API_PREFIX)
app.include_router(dashboard_router, prefix=settings.API_PREFIX)
app.include_router(export_router, prefix=settings.API_PREFIX)
app.include_router(auth_router, prefix=settings.API_PREFIX)
app.include_router(meters_router, prefix=settings.API_PREFIX)
app.include_router(readings_router, prefix=settings.API_PREFIX)
app.include_router(sync_router, prefix=settings.API_PREFIX)
app.include_router(audit_router, prefix=settings.API_PREFIX)
app.include_router(no_read_reasons_router, prefix=settings.API_PREFIX)
app.include_router(historial_lecturas_router, prefix=settings.API_PREFIX)


# ─── Static Files ─────────────────────────────────────
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")


# ─── Health check ─────────────────────────────────────
@app.get("/health", tags=["Health"])
async def health():
    db_ok = False
    try:
        async with engine.connect() as conn:
            await conn.execute(sa_text("SELECT 1"))
            db_ok = True
    except Exception:
        db_ok = False
    return {
        "status": "ok" if db_ok else "degraded",
        "version": settings.APP_VERSION,
        "database": "connected" if db_ok else "error",
    }
