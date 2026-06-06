# Guía de Trabajo Local

## Estructura de Ramas

```
main        → Código estable en producción
develop     → Cambios en integración
feature/*   → Ramas temporales para nuevas funcionalidades
fix/*       → Ramas temporales para correcciones
```

Regla: **nunca trabajes directamente en `main`**.

---

## Flujo Diario

### 1. Actualizar rama local

```bash
git checkout develop
git pull origin develop
```

### 2. Crear rama para tu tarea

```bash
# Feature nueva
git checkout -b feature/descripcion-breve

# Bugfix
git checkout -b fix/descripcion-del-error
```

### 3. Trabajar y hacer commit

```bash
# Ver qué cambió
git status
git diff

# Agregar archivos
git add -A

# Commit con mensaje descriptivo
git commit -m "tipo: mensaje corto"

# Tipos de commit:
# feat:  nueva funcionalidad
# fix:   corrección de bug
# refactor: cambio sin agregar funcionalidad
# docs:  documentación
# style: formato, espacios, punto y coma
# chore: tareas rutinarias
```

### 4. Publicar rama

```bash
git push origin feature/descripcion-breve
```

### 5. Fusionar con develop

```bash
git checkout develop
git merge feature/descripcion-breve
git push origin develop
```

### 6. Pasar a main (solo cuando develop esté validado)

```bash
git checkout main
git merge develop
git push origin main
```

---

## Iniciar Servidor Local

```powershell
.venv\Scripts\activate
uvicorn app.main:app --reload --port 8000
```

Documentación: http://localhost:8000/docs

---

## Probar Endpoints

```powershell
# Login admin
$login = Invoke-RestMethod -Uri "http://localhost:8000/api/auth/login" -Method Post -ContentType "application/json" -Body (@{email="admin@agua.com"; password="<tu-password>"} | ConvertTo-Json)

# Dashboard admin
Invoke-RestMethod -Uri "http://localhost:8000/api/dashboard/admin" -Method Get -Headers @{Authorization="Bearer $($login.access_token)"}

# Dashboard lecturista
$login2 = Invoke-RestMethod -Uri "http://localhost:8000/api/auth/login" -Method Post -ContentType "application/json" -Body (@{email="lector1@lectura.com"; password="<tu-password>"} | ConvertTo-Json)
Invoke-RestMethod -Uri "http://localhost:8000/api/dashboard/lector" -Method Get -Headers @{Authorization="Bearer $($login2.access_token)"}
```

---

## Comandos Útiles de Git

```bash
# Ver historial
git log --oneline --graph --all

# Ver ramas
git branch -a

# Descartar cambios locales (cuidado)
git checkout -- <archivo>

# Guardar cambios temporales
git stash
git stash pop

# Borrar rama local
git branch -d feature/nombre

# Borrar rama remota
git push origin --delete feature/nombre
```

---

## Estructura del Proyecto

```
app/
├── api/routers/      → Endpoints FastAPI
├── core/             → Config, DB, logging, excepciones
├── models/           → SQLAlchemy models
├── schemas/          → Pydantic v2 schemas
├── services/         → Lógica de negocio
└── main.py           → Punto de entrada
```

---

## Resolución de Problemas Comunes

| Error | Causa | Solución |
|---|---|---|
| `ResponseValidationError` | Schema no coincide con DB | Revisar tipos en schema vs modelo |
| `404 Not Found` en endpoint | Servidor no reiniciado | Ctrl+C y volver a ejecutar `uvicorn` |
| `ValidationError` en login | Campo incorrecto | Usar `email` no `username` |
| Puerto ocupado | Otro proceso en :8000 | `netstat -ano \| findstr :8000` y matar proceso |
