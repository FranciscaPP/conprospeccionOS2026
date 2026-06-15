# Modelo de accesos OS2026

Clientes activos desde junio 2026:

- Clickie: meta mensual 6 reuniones validas.
- GBS Logistics: meta mensual 10 reuniones validas.
- BambuTech: meta mensual 12 reuniones validas.

## Roles

- `agency_admin`: ve todos los clientes, reuniones, SDRs, configuracion y sincronizaciones.
- `sdr_leader`: ve todos los clientes activos y seguimiento operativo por SDR.
- `client_admin`: ve y valida solo las reuniones del cliente asignado.
- `client_viewer`: ve solo las reuniones del cliente asignado, sin permisos de edicion.

## Rutas actuales

- Interno: `/internal/meeting-followup`
- Portal Clickie: `/client/meeting-validation?client=clickie`
- Portal GBS: `/client/meeting-validation?client=gbs`
- Portal BambuTech: `/client/meeting-validation?client=bambutech`

## Implementacion actual

La fuente de clientes activos vive en `lib/access-control.ts`.

El dashboard interno sigue leyendo reuniones reales desde Supabase por `/api/internal/meetings`, filtrando:

- Solo clientes activos: Clickie, GBS y BambuTech.
- Filas con `TEST` en campos principales o `raw_data`.
- Filas incompletas sin empresa, contacto o fecha agendada.
- Duplicados por empresa o correo, conservando la reunion con fecha agendada mas reciente.

## Siguiente paso de seguridad

Para entregar accesos reales a clientes y SDR lider se debe conectar Supabase Auth o el proveedor definido por agencia y guardar el perfil de acceso en `app_metadata`, no en `user_metadata`.

Las politicas RLS deben restringir reuniones por `cliente_slug`:

- Agencia y SDR lider: `clickie`, `gbs`, `bambutech`.
- Cliente Clickie: `clickie`.
- Cliente GBS: `gbs`.
- Cliente BambuTech: `bambutech`.

