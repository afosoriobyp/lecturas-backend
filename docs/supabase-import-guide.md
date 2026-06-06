# Guía de Importación a Supabase

## Archivos Generados

| Archivo | Tamaño | Descripción |
|---------|--------|-------------|
| `supabase_full.sql` | ~180 KB | Esquema completo + datos (usuarios, historial, auditoría, motivos) |
| `supabase_schema.sql` | ~18 KB | Solo esquema (sin datos) |
| `supabase_data.sql` | ~166 KB | Solo datos |

## Tablas exportadas con datos

| Tabla | Registros |
|-------|-----------|
| `users` | 5 (admin, supervisor, lecturista, nelson, auditor) |
| `historial_lecturas` | 460 (historial legacy importado) |
| `audit_logs` | 267 (registros de actividad) |
| `no_read_reasons` | 49 (catálogo de motivos de no lectura) |

## Instrucciones

### Opción 1: SQL Editor (datos pequeños)
1. Ir a Supabase Dashboard → **SQL Editor**
2. Abrir `supabase_full.sql` y copiar todo el contenido
3. Pegar en el editor y ejecutar
4. Verificar en **Table Editor** que las tablas aparezcan con datos

### Opción 2: pg_dump + psql remoto (recomendado)
```bash
# Obtener cadena de conexión de Supabase (Project Settings → Database → Connection string)
# Usar URI mode (postgresql://)

pg_dump -h localhost -U lectura_user -d lectura_medidor \
  --no-owner --no-acl | psql "<supabase-connection-string>"
```

### Opción 3: Split manual
1. Primero ejecutar `supabase_schema.sql` para crear tablas
2. Luego ejecutar `supabase_data.sql` para insertar datos

## Post-importación

```sql
-- Verificar tablas creadas
SELECT table_name, row_estimate 
FROM information_schema.tables t 
LEFT JOIN pg_stat_user_tables s ON t.table_name = s.relname
WHERE table_schema = 'public';

-- Crear seed users si no se importaron (passwords hasheados)
-- admin / admin123, supervisor / super123, lecturista / lectura123, auditor / auditor123
```

## Notas
- Los archivos se generaron con `pg_dump` desde PostgreSQL 18.3 local
- Supabase usa PostgreSQL 15+, compatible
- No se incluyen políticas RLS — configurarlas según necesidades
- El archivo usa `public.` como schema (default en Supabase)
