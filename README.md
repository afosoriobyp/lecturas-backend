# Lectura Medidor API

API REST para el sistema de gestión de lecturas de medidores de agua, construida con **FastAPI** (asíncrono), **SQLAlchemy 2.0** (async), **PostgreSQL** y **JWT**. Soporta sincronización offline/online, subida de fotos, auditoría completa, control de acceso por roles, exportación de datos y **sistema centralizado de errores con trazabilidad**.

---

## Stack Tecnológico

| Capa          | Tecnología                                    |
|---------------|-----------------------------------------------|
| Framework     | FastAPI 0.111+                                |
| ORM           | SQLAlchemy 2.0+ (asyncio)                     |
| Base de Datos | PostgreSQL 15+ con asyncpg                    |
| Migraciones   | Alembic 1.13+                                 |
| Autenticación | JWT (python-jose + bcrypt)                    |
| Validación    | Pydantic v2                                   |
| Archivos      | Subida multipart con validación de tipo/tamaño |
| Notificaciones| python-telegram-bot v20+ (placeholder)        |
| Exportación   | CSV / XLSX (openpyxl)                         |
| Contenedores  | Docker + docker-compose                       |
| Proxy         | opcional: Nginx / Caddy                        |
| Logging       | JSON estructurado con rotación diaria         |
| Alertas       | Telegram solo para fallos críticos (throttle 5 min) |

---

## Arquitectura

```
app/
├── api/
│   ├── dependencies.py        # SessionDep (AsyncSession injectable)
│   └── routers/               # 11 módulos de endpoints
├── core/
│   ├── config.py              # Settings (pydantic-settings)
│   ├── database.py            # Engine, session factory, Base
│   ├── security.py            # JWT, bcrypt, AuthMiddleware, RBAC
│   ├── exceptions.py          # HTTPException + BusinessRuleError, SyncConflictError, DBConstraintError
│   ├── logging.py             # RequestLoggingMiddleware
│   ├── log_config.py          # Context vars (trace_id, user_id), JSON formatter, rotation diaria, TraceIDMiddleware
│   └── audit_events.py        # Eventos ORM automáticos
├── models/                    # 11 modelos SQLAlchemy
├── schemas/                   # Pydantic request/response
│   ├── error.py               # AppError — formato unificado de errores
│   ├── sync.py                # BulkSyncResponse con synced/conflicts/trace_id
│   └── ...
└── services/                  # Lógica de negocio
    ├── auth.py                # Login, registro, refresh
    ├── audit.py               # log_action centralizado
    ├── conflict_resolver.py   # Resolución LWW en bulk sync
    ├── background_tasks.py    # Procesamiento post-sync
    ├── alerts.py              # Alertas críticas vía Telegram con throttle
    └── telegram.py            # Placeholder bot
```

---

## Formato de Errores

Todas las respuestas de error siguen el esquema unificado `AppError`:

```json
{
  "code": "SYNC_CONFLICT",
  "message": "Se detectaron conflictos de sincronización — elija acción",
  "details": {
    "options": ["override", "skip"],
    "conflicts": [{"niud": "MTR001", "message": "Descartado por LWW"}]
  },
  "trace_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "timestamp": "2026-06-03T14:30:15.123Z"
}
```

### Tabla de Códigos de Error

| Código | HTTP | Descripción | `details` | Acción Frontend |
|---|---|---|---|---|
| `VALIDATION_ERROR` | 400 | Datos inválidos (schemas Pydantic) | `{"fields": {"body.nombre": "field required"}}` | Corregir campos señalados |
| `BAD_REQUEST` | 400 | Solicitud mal formada | `{}` | Revisar payload |
| `UNAUTHORIZED` | 401 | Token ausente/inválido | `{}` | Redirigir a login |
| `FORBIDDEN` | 403 | Rol sin permiso | `{}` | Mostrar "sin acceso" |
| `NOT_FOUND` | 404 | Entidad no existe | `{}` | Mostrar "no encontrado" |
| `SYNC_CONFLICT` | 409 | Duplicado mismo día | `{"options": ["override", "skip"], "conflicts": [...]}` | Modal con opciones |
| `DB_DUPLICATE` | 409 | Unique constraint | `{"db_error": "..."}` | Mostrar "registro duplicado" |
| `DB_FOREIGN_KEY` | 409 | FK violation | `{"db_error": "..."}` | Mostrar "referencia inválida" |
| `DB_CONSTRAINT` | 409 | Restricción BD | `{"db_error": "..."}` | Mostrar error de restricción |
| `SYNC_ANOMALY` | 422 | Lectura fuera de rango histórico | `{"requires_review": true, "items": [...]}` | Banner amarillo + "Enviar de todos modos" |
| `UNPROCESSABLE_ENTITY` | 422 | Error de negocio genérico | `{}` | Mostrar mensaje |
| `DB_TIMEOUT` | 504 | Query timeout | `{"db_error": "..."}` | Reintentar más tarde |
| `DB_DOWN` | 503 | BD no disponible (crítico) | `{"db_error": "..."}` | Modo offline + alerta Telegram |
| `DB_INTERFACE` | 503 | Error de conexión (crítico) | `{"db_error": "..."}` | Modo offline + alerta Telegram |
| `INTERNAL_ERROR` | 500 | Error no manejado | `{}` | Mostrar "error inesperado" + `trace_id` |

### Headers de Respuesta

| Header | Valor | Descripción |
|---|---|---|
| `X-Trace-Id` | UUID v4 | Correlacionar con logs del backend |
| `Content-Type` | `application/json` | Siempre |

---

## Configuración Rápida

### 1. Clonar y entorno virtual

```bash
python -m venv .venv
.venv\Scripts\activate    # Windows
pip install -r requirements.txt
```

### 2. Variables de entorno

Crear `.env` (ver `.env.example`):

```env
APP_NAME="Lectura Medidor API"
APP_VERSION="0.2.0"
APP_DEBUG=true

POSTGRES_USER=lectura_user
POSTGRES_PASSWORD=lectura_pass
POSTGRES_SERVER=localhost
POSTGRES_PORT=5432
POSTGRES_DB=lectura_medidor

DATABASE_URL=postgresql+asyncpg://lectura_user:lectura_pass@localhost:5432/lectura_medidor

JWT_SECRET_KEY=dev-secret-change-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

UPLOAD_DIR=uploads
MAX_IMAGE_SIZE_MB=5

LOG_LEVEL=INFO
LOG_FORMAT=json
```

### 3. Base de datos

```bash
# Iniciar PostgreSQL (Docker)
docker compose up -d db

# Ejecutar migraciones
alembic upgrade head
```

### 4. Iniciar servidor

```bash
uvicorn app.main:app --reload --port 8000
```

Documentación interactiva: http://localhost:8000/docs

---

## Usuarios Semilla

Al iniciar por primera vez, se crean automáticamente estos usuarios:

| Usuario      | Email                        | Contraseña  | Rol         |
|--------------|------------------------------|-------------|-------------|
| admin        | admin@agua.com               | admin123    | admin       |
| supervisor   | supervisor@agua.com          | super123    | supervisor  |
| lecturista   | lecturista@ejemplo.com       | lectura123  | lector      |
| auditor      | auditor@agua.com             | auditor123  | auditor     |

**Roles**:
- `admin` — acceso completo
- `supervisor` — gestión de lectores, revisión de lecturas
- `lector` — toma de lecturas en campo (solo ve sus datos)
- `auditor` — consulta de logs y dashboard

---

## Autenticación

**Flujo JWT**:
1. `POST /auth/login` → obtiene `access_token` (30 min) + `refresh_token` (7 días)
2. Enviar token vía header `Authorization: Bearer <token>` o cookie `access_token`
3. `POST /auth/refresh` → renueva ambos tokens
4. `POST /auth/logout` → elimina cookie

**Middleware**: `AuthMiddleware` inyecta `request.user` con `.id`, `.username`, `.rol`. Las rutas públicas (`/health`, `/auth/login`, `/docs`, etc.) no requieren token. `user_id` se propaga automáticamente al logging y al contexto de errores.

---

## Logging

Formato JSON estructurado con rotación diaria. Cada línea incluye contexto de trazabilidad:

```json
{
  "timestamp": "2026-06-03T14:30:15.123Z",
  "level": "ERROR",
  "logger": "app.main",
  "message": "Error DB [DB_DOWN]: could not connect to server",
  "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "endpoint": "/api/sync/bulk",
  "error_code": "DB_DOWN",
  "exception": "Traceback (most recent call last):\n  ..."
}
```

**Archivos de log**:
- `logs/app.log` — rotación diaria, retención 30 días
- `logs/error.log` — solo nivel ERROR+, rotación diaria, retención 90 días
- Consola stdout en desarrollo, con formato JSON o texto según `LOG_FORMAT`

**Contexto de trazabilidad** (`trace_id`):
- Se genera un UUID v4 por cada request
- Se inyecta en el header de respuesta `X-Trace-Id`
- Se propaga a todos los logs generados durante ese request
- Permite correlacionar errores entre frontend y backend

---

## API Endpoints

### Auth (`/auth`)

| Método | Ruta             | Roles        | Descripción                     |
|--------|------------------|--------------|---------------------------------|
| POST   | `/auth/register` | público      | Registrar nuevo usuario         |
| POST   | `/auth/login`    | público      | Iniciar sesión (JWT + cookie)   |
| POST   | `/auth/refresh`  | público      | Refrescar token                 |
| POST   | `/auth/logout`   | cualquiera   | Cerrar sesión                   |
| GET    | `/auth/me`       | cualquiera   | Perfil del usuario autenticado  |
| GET    | `/auth/perfil`   | cualquiera   | Alias de `/auth/me`             |

### Admin - Lectores (`/admin`)

| Método | Ruta                                    | Roles              | Descripción                          |
|--------|-----------------------------------------|--------------------|--------------------------------------|
| GET    | `/admin/lectores`                       | admin, supervisor  | Listar lectores                      |
| POST   | `/admin/lectores`                       | admin, supervisor  | Crear lector                         |
| PATCH  | `/admin/lectores/{lector_id}`           | admin, supervisor  | Actualizar lector                    |
| DELETE | `/admin/lectores/{lector_id}`           | admin, supervisor  | Eliminar lector                      |
| POST   | `/admin/lectores/{lector_id}/reset-password` | admin, supervisor | Resetear contraseña              |

### Admin - Asignaciones (`/admin`)

| Método | Ruta                                | Roles              | Descripción                                  |
|--------|-------------------------------------|--------------------|----------------------------------------------|
| POST   | `/admin/asignaciones`               | admin, supervisor  | Asignar ruta a lector                        |
| PUT    | `/admin/asignaciones`               | admin, supervisor  | Reemplazar todas las rutas de un lector      |
| GET    | `/admin/asignaciones/{lector_id}`   | admin, supervisor  | Ver asignaciones de un lector                |

### Admin - Carga Masiva (`/admin`)

| Método | Ruta                       | Roles              | Descripción                      |
|--------|----------------------------|--------------------|----------------------------------|
| POST   | `/admin/cargar-medidores`  | admin, supervisor  | Cargar medidores desde CSV/XLSX  |
| POST   | `/admin/cargar-lecturas`   | admin, supervisor  | Cargar lecturas desde CSV/XLSX   |

### Medidores (`/meters`)

| Método | Ruta                                   | Roles        | Descripción                               |
|--------|----------------------------------------|--------------|-------------------------------------------|
| GET    | `/meters/`                             | cualquiera   | Listar medidores (con filtros)            |
| GET    | `/meters/mis-rutas`                    | lector       | Medidores de las rutas asignadas          |
| GET    | `/meters/mis-rutas/orden`              | lector       | Igual pero ordenado por ruta+orden        |
| GET    | `/meters/{meter_id}`                   | cualquiera   | Detalle del medidor + últimas lecturas    |
| GET    | `/meters/{meter_id}/history`           | cualquiera   | Historial de lecturas + estadísticas      |
| GET    | `/meters/{niud}/promedio-historico`    | cualquiera   | Promedio de consumo últimos 30 días       |
| POST   | `/meters/`                             | cualquiera   | Crear medidor                             |
| PATCH  | `/meters/{meter_id}`                   | cualquiera   | Actualizar medidor                        |
| DELETE | `/meters/{meter_id}`                   | admin, supervisor | Eliminar medidor                     |

### Lecturas (`/readings`)

| Método | Ruta                                      | Roles                        | Descripción                              |
|--------|-------------------------------------------|------------------------------|------------------------------------------|
| GET    | `/readings/`                              | cualquiera                   | Listar lecturas (con filtros)            |
| GET    | `/readings/revisar`                       | cualquiera                   | Lecturas que requieren revisión          |
| GET    | `/readings/{reading_id}`                  | cualquiera                   | Detalle de lectura                       |
| POST   | `/readings/`                              | cualquiera                   | Crear lectura (con validación automática)|
| PATCH  | `/readings/{reading_id}`                  | admin, supervisor            | Actualizar lectura                       |
| PATCH  | `/readings/{reading_id}/estado`           | admin, supervisor, auditor   | Cambiar estado de validación             |
| POST   | `/readings/{reading_id}/observacion-admin` | admin, supervisor           | Agregar observación interna              |
| DELETE | `/readings/{reading_id}`                  | admin, supervisor            | Eliminar lectura                         |

### Historial Lecturas (`/historial-lecturas`)

| Método | Ruta                                              | Roles                 | Descripción                                    |
|--------|---------------------------------------------------|-----------------------|------------------------------------------------|
| GET    | `/historial-lecturas/`                            | cualquiera            | Listar (filtros: nuis, ruta_lectura, nombre)   |
| GET    | `/historial-lecturas/{id_lectura}`                | cualquiera            | Detalle                                        |
| PATCH  | `/historial-lecturas/{id_lectura}`                | lector, admin, supervisor | Actualizar (lectura, consumo, estado, etc)  |
| POST   | `/historial-lecturas/{id_lectura}/fotos`          | lector, admin, supervisor | Subir fotos (multipart, máx 5, JPG/PNG/WebP) |
| DELETE | `/historial-lecturas/{id_lectura}/fotos`          | lector, admin, supervisor | Eliminar fotos (query: filenames)           |

### Sincronización (`/sync`)

| Método | Ruta                       | Roles        | Descripción                                      |
|--------|----------------------------|--------------|--------------------------------------------------|
| POST   | `/sync/bulk`               | cualquiera   | Sincronización masiva (hasta 500 lecturas, LWW)  |
| GET    | `/sync/status`             | cualquiera   | Estado de la cola de sincronización              |
| POST   | `/sync/force/{type}/{id}`  | cualquiera   | Forzar sincronización de una entidad             |
| POST   | `/sync/telegram-webhook`   | público      | Webhook para Telegram Bot (placeholder)          |

El endpoint `POST /sync/bulk` puede devolver:
- **200**: Sincronización exitosa → `{ "synced": N, "conflicts": M, "trace_id": "...", "resultados": [...] }`
- **409**: Todos los items son conflictos (duplicado mismo día) → `{ "code": "SYNC_CONFLICT", "details": { "options": ["override", "skip"] } }`
- **422**: Todos los items tienen anomalías → `{ "code": "SYNC_ANOMALY", "details": { "requires_review": true } }`

### Auditoría (`/audit`)

| Método | Ruta                   | Roles                     | Descripción                     |
|--------|------------------------|---------------------------|---------------------------------|
| GET    | `/audit/logs`          | admin, supervisor         | Logs de auditoría (con filtros) |
| GET    | `/audit/sync-logs`     | admin, supervisor, auditor| Registros de sincronización     |

### Dashboard (`/dashboard`)

| Método | Ruta                 | Roles                     | Descripción                          |
|--------|----------------------|---------------------------|--------------------------------------|
| GET    | `/dashboard/lector`  | lector                    | Estadísticas del lector (hoy)        |
| GET    | `/dashboard/admin`   | admin, supervisor         | Totales de completados/pendientes    |
| GET    | `/dashboard/auditor` | admin, supervisor, auditor | Panorama completo del sistema       |

### Exportación (`/export`)

| Método | Ruta                          | Roles                     | Descripción              |
|--------|-------------------------------|---------------------------|--------------------------|
| GET    | `/export/readings/csv`       | admin, supervisor, auditor | Exportar lecturas a CSV |
| GET    | `/export/meters/csv`         | admin, supervisor, auditor | Exportar medidores a CSV|

### Health

| Método | Ruta       | Descripción           |
|--------|------------|-----------------------|
| GET    | `/health`  | Health check público  |

---

## Subida de Fotos

### POST `/historial-lecturas/{id_lectura}/fotos`

- **Content-Type**: `multipart/form-data`
- **Body**: `files` (hasta 5 archivos, mínimo 1)
- **Tipos permitidos**: `image/jpeg`, `image/png`, `image/webp`
- **Tamaño máximo**: 5 MB por archivo
- **Almacenamiento**: `uploads/historial-lecturas/{id_predio}/{id_predio}_{n}.ext`
- **Respuesta**: `{ "fotos": ["795_1.jpg", "795_2.jpg"] }`
- La columna `fotos_pendientes` se resetea a 0 al subir

### DELETE `/historial-lecturas/{id_lectura}/fotos?filenames=795_1.jpg,795_3.jpg`

- Elimina los archivos del disco y actualiza el JSON en BD
- Re-indexa los archivos restantes (ej: `_3` → `_2`)
- Requiere auth (lector, admin, supervisor)

Los archivos subidos se sirven estáticamente desde `GET /uploads/historial-lecturas/{id_predio}/{filename}`.

---

## Modelos de Datos

| Modelo               | Tabla                | Descripción                                  |
|----------------------|----------------------|----------------------------------------------|
| `User`               | `users`              | Usuarios con roles, Telegram binding         |
| `Meter`              | `meters`             | Medidores con GPS, ruta, orden, stats cache  |
| `Reading`            | `readings`           | Lecturas con validación, consumo, foto       |
| `HistorialLectura`   | `historial_lecturas` | Historial legacy con fotos (JSON)            |
| `NoReadReason`       | `no_read_reasons`    | Catálogo de motivos de no lectura            |
| `AuditLog`           | `audit_logs`         | Trazabilidad de todas las operaciones        |
| `SyncJob`            | `sync_jobs`          | Cola de trabajos de sincronización           |
| `NotificationQueue`  | `notification_queue` | Payloads de notificación (Telegram)          |
| `Ruta`               | `rutas`              | Catálogo de rutas                            |
| `RutaAsignada`       | `rutas_asignadas`    | Asignación lector ↔ ruta                     |

### HistorialLectura — Campos de Fotos

```python
fotos: str | None           # JSON array: ["795_1.jpg", "795_2.jpg"]
fotos_pendientes: int | None  # Contador de fotos locales sin subir (offline)
```

---

## Sincronización Offline/Online

El endpoint `POST /sync/bulk` maneja sincronización masiva:

1. **Validación**: cada ítem requiere `niud` (medidor existente)
2. **Detección de duplicados**: por `(meter_id, fecha)`
3. **Resolución de conflictos**: last-write-wins (LWW) basado en `timestamp_local`
4. **Detección de anomalías**: si `|lectura - promedio_últimas_3| > 30%` → `requiere_revision`
5. **Respuestas diferenciadas**:
   - `200 OK`: todo procesado, incluye `synced`, `conflicts`, `trace_id`
   - `409 Conflict`: todos los items son conflictos → frontend muestra modal con `options: ["override", "skip"]`
   - `422 Unprocessable`: todos los items tienen anomalías → frontend muestra `requires_review: true`
6. **Post-procesamiento** (background tasks):
   - Recalcular consumos (`_finalize_readings`)
   - Actualizar cache_stats del medidor (`_update_meter_cache`)
   - Generar cola de notificaciones (`_generate_notifications`)

---

## Sistema de Errores

### Mecanismo

1. **TraceIDMiddleware**: genera UUID v4 por request, disponible en `request.state.trace_id`, header `X-Trace-Id`, y contexto de logging
2. **Exception Handlers** (orden de precedencia):
   - `RequestValidationError` → 400 + campos inválidos
   - `HTTPException` → mapeo a `AppError` (incluye `BusinessRuleError`, `SyncConflictError`, `DBConstraintError`)
   - `SQLAlchemyError` → traducción a `DB_*` con status apropiado
   - `Exception` → 500 con `trace_id` (sin stack trace en producción)
3. **Alertas críticas**: solo `DB_DOWN`, `SYNC_QUEUE_FULL`, `AUTH_SYSTEM_FAIL` disparan notificación Telegram, con throttle de 5 min por código

### Excepciones Personalizadas

| Clase | HTTP | Constructor | Uso |
|---|---|---|---|
| `BusinessRuleError` | 422 | `(code, message, details)` | Validaciones de negocio |
| `SyncConflictError` | 409 | `(message, details)` | Conflictos de sincronización |
| `DBConstraintError` | 409 | `(code, message, details)` | Errores de BD traducidos |

---

## Auditoría

Dos mecanismos complementarios:

### 1. Logging manual (`app/services/audit.py`)
```python
await log_action(db, accion="reading.create", entidad_tipo="reading",
                 entidad_id=reading.id, actor_id=str(current_user.id),
                 detalle={...})
```

### 2. Eventos ORM automáticos (`app/core/audit_events.py`)
- Captura `after_insert` / `after_update` / `after_delete` en modelos registrados
- Requiere `current_actor_id` (inyectado por AuthMiddleware)
- Omite campos sensibles (`hashed_password`, `telegram_id`, etc.)

---

## Alertas Críticas (Telegram)

Solo se envían para:
- `DB_DOWN` — base de datos no disponible
- `SYNC_QUEUE_FULL` — cola de sincronización llena (reservado)
- `AUTH_SYSTEM_FAIL` — fallo del sistema de autenticación (reservado)

**Throttle**: máximo 1 alerta cada 5 minutos por código de error.

Requiere configurar `TELEGRAM_BOT_TOKEN` en `.env`.

---

## Deployment

### Docker Compose

```bash
docker compose up -d
```

Inicia:
- **api**: FastAPI en `:8000` con recarga automática
- **db**: PostgreSQL 15 en `:5432`
- **pgadmin**: pgAdmin 4 en `:5050` (admin@lectura.local / admin123)

### Dockerfile

Imagen optimizada con Python 3.12-slim + gcc + libpq-dev.

---

## Migraciones (Alembic)

```bash
# Crear nueva migración
alembic revision --autogenerate -m "descripcion"

# Aplicar pendientes
alembic upgrade head

# Revertir una
alembic downgrade -1
```

---

## Variables de Entorno

| Variable                         | Descripción                              | Default                          |
|----------------------------------|------------------------------------------|----------------------------------|
| `APP_NAME`                       | Nombre de la aplicación                  | Lectura Medidor API              |
| `APP_VERSION`                    | Versión                                  | 0.2.0                            |
| `APP_DEBUG`                      | Modo debug                               | false                            |
| `POSTGRES_USER`                  | Usuario PostgreSQL                       | lectura_user                     |
| `POSTGRES_PASSWORD`              | Contraseña PostgreSQL                    | lectura_pass                     |
| `POSTGRES_SERVER`                | Host PostgreSQL                          | localhost                        |
| `POSTGRES_PORT`                  | Puerto PostgreSQL                        | 5432                             |
| `POSTGRES_DB`                    | Base de datos                            | lectura_medidor                  |
| `DATABASE_URL`                   | URL completa (opcional)                  | construida automáticamente       |
| `DB_POOL_SIZE`                   | Pool de conexiones                       | 5                                |
| `DB_MAX_OVERFLOW`                | Overflow del pool                        | 10                               |
| `DB_STATEMENT_TIMEOUT_MS`       | Timeout de consultas (ms)                | 10000                            |
| `JWT_SECRET_KEY`                 | Clave secreta JWT                        | dev-secret-change-in-production  |
| `JWT_ALGORITHM`                  | Algoritmo JWT                            | HS256                            |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`| Expiración access token (minutos)        | 30                               |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS`  | Expiración refresh token (días)          | 7                                |
| `JWT_COOKIE_SECURE`              | Cookie secure (HTTPS)                    | false                            |
| `JWT_COOKIE_SAMESITE`            | SameSite cookie                          | lax                              |
| `UPLOAD_DIR`                     | Directorio de subida de archivos         | uploads                          |
| `MAX_IMAGE_SIZE_MB`             | Tamaño máximo de imagen (MB)             | 5                                |
| `ALLOWED_IMAGE_TYPES`           | Tipos MIME permitidos                    | image/jpeg, image/png, image/webp |
| `MAX_FOTOS_PER_LECTURA`         | Máximo de fotos por lectura              | 5                                |
| `TELEGRAM_BOT_TOKEN`            | Token del bot de Telegram                | (vacio)                          |
| `TELEGRAM_WEBHOOK_URL`          | URL del webhook Telegram                 | (vacio)                          |
| `TELEGRAM_WEBHOOK_SECRET`       | Secreto del webhook Telegram             | (vacio)                          |
| `CORS_ORIGINS`                  | Orígenes permitidos CORS                 | localhost:3000,5173,8000         |
| `LOG_LEVEL`                     | Nivel de logging                         | INFO                             |
| `LOG_FORMAT`                    | Formato: json o text                     | json                             |

---

## Pruebas Locales

### Obtener token
```bash
curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "lecturista", "password": "lectura123"}' | jq -r '.access_token'
```

### Verificar `trace_id` en headers
```bash
curl -s -D - -X POST http://localhost:8000/api/sync/bulk \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"items": []}' | head -20
```

### Probar error de validación (400)
```bash
curl -s -X POST http://localhost:8000/api/sync/bulk \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"items": [{}]}' | jq .
```

### Probar 404
```bash
curl -s http://localhost:8000/api/nonexistent \
  -H "Authorization: Bearer <token>" | jq .
```

### Verificar logs JSON
```bash
Get-Content logs\app.log -Tail 10 | ConvertFrom-Json
```
