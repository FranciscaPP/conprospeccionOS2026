# Supabase — Migraciones

Proyecto: `gdlncvbvhbfjonbnmxfl`

Estas migraciones **no se aplican automáticamente** — son documentación del estado actual de la base de datos. Si necesitás recrear la BD desde cero, correlas en orden numérico desde el panel SQL de Supabase o via MCP.

## Orden de aplicación

| Archivo | Tablas | Descripción |
|---------|--------|-------------|
| `001_core_tables.sql` | sdrs, clientes, sdr_cliente, sdr_pago_reglas | Estructura base del equipo y clientes |
| `002_actividad_tables.sql` | reuniones, llamadas, oportunidades | Actividad comercial sincronizada desde GHL |
| `003_finanzas_y_sync.sql` | pagos_sdr, sync_runs, import_runs | Finanzas SDR y registros de sync |
| `004_seguimiento_clientes.sql` | tiresias_seguimiento, clickie_seguimiento | Seguimiento comercial por cliente |
| `005_gbs_onboarding.sql` | gbs_onboarding | Formulario de onboarding GBS (upsert por cliente) |

## Convención para nuevos clientes

Cuando se agrega un nuevo cliente con tabla de seguimiento:
1. Agregar la tabla en `004_seguimiento_clientes.sql` (descomentar el bloque de ejemplo)
2. Si tiene formulario de onboarding, crear `006_{cliente}_onboarding.sql` siguiendo el patrón de GBS

## Tablas que NO están documentadas aquí

- `backup_*` — backups puntuales, no reproducibles
- `snov_*` — creadas por el módulo de Snov.io, se documentan separado si aplica
- Vistas (`vw_*`) — generadas por Supabase, no son tablas base
- `contactos`, `ghl_calendars`, `ghl_pipeline_stages`, `ghl_users` — tablas de referencia GHL

## Notas

- La tabla `gbs_seguimiento` está pendiente — crearla cuando haya reuniones reales de GBS
- Las tablas de actividad (`reuniones`, `llamadas`, `oportunidades`) se sincronizan via `sync/scripts/run_sync.py`
