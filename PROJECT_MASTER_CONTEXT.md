# Contexto maestro del proyecto

Fecha de referencia: 2026-06-27

Este documento define la fuente oficial de verdad tecnica del repositorio Conprospeccion OS2026.

**Fuente unica.** Este es el documento que cualquier IA o persona nueva debe
leer primero. `CLAUDE.md` (lo lee Claude) y `AGENTS.md` (lo leen Codex,
Cursor y otras IA) solo apuntan aqui; no duplican contenido. Si algo cambia
(mapa, alcance, reglas, deploy), se actualiza **aqui** y en ningun otro lado,
para que nunca haya dos versiones distintas.

## Producto oficial

La aplicacion oficial actual es Streamlit.

- Entrada principal: `dashboard/app.py`
- Panel maestro interno: `dashboard/pages/1_Seguimiento_Reuniones.py`
- URL publica Streamlit oficial: `https://conprospeccion-os2026.streamlit.app/Seguimiento_Reuniones`
- URL local esperada: `http://localhost:8502/Seguimiento_Reuniones`

Streamlit es la unica implementacion. No usar React, Next.js, Vercel ni Netlify como base tecnica salvo instruccion explicita.

## Alcance activo

El trabajo ordinario debe limitarse a:

- `dashboard/`
- `shared/`
- `sync/`
- `supabase/`
- `mvp_setup/`
- `tests/`
- `docs/`

Limpieza 2026-07-03: `archive/`, `mockups/`, `scripts/` y todas las
paginas de portal cliente y Tiresias fueron eliminadas del repo. Los
portales cliente se reconstruiran desde cero a partir del panel interno.

## Mapa del proyecto

Estructura para orientarse rapido (cualquier IA o persona nueva la lee y
entiende el repo sin explorar archivo por archivo):

- `dashboard/` — App Streamlit (el producto). `app.py` es la entrada.
  - `dashboard/pages/` — Paginas del panel. La principal es
    `1_Seguimiento_Reuniones.py` (panel maestro interno). Tambien:
    `2_Clientes.py`, `9_SDRs.py`, `16_Client_Setup_OS.py`,
    `19_BambuTech_Intelligence_Insight.py` (referencia),
    `20_GBS_Intelligence_Insight.py`.
  - `master_auth.py`, `portal_auth.py` — Login / autenticacion.
  - `meeting_component.py`, `meeting_shared.py` — UI y logica de la tabla
    de reuniones.
- `shared/` — Codigo reutilizable. Clave: `validacion.py` (los 7 estados
  oficiales de una reunion), `seguimiento.py`, `meeting_scope.py`,
  `config.py`, `cp_design.py` (design system carbon + dorado), `metas.py`,
  `planes.py`.
- `sync/` — Sincronizacion de datos hacia Supabase (`scripts/`,
  `migrations/`, `queries/`) + CI.
- `supabase/` — Base de datos: `migrations/` y `functions/` (edge functions).
- `mvp_setup/` — Modulo de setup / onboarding de clientes (app propia).
- `tests/` — Pruebas (pytest).
- `docs/` — Documentacion funcional (ver el RUNBOOK del panel de reuniones).

## Datos canonicos

GoHighLevel sigue siendo la fuente primaria de datos de reuniones, contactos y agenda.

Supabase es la base operacional usada por la aplicacion:

- `reuniones`: datos canonicos sincronizados desde fuentes externas y campos base de reunion/contacto.
- `seguimiento_reuniones`: decisiones operativas internas, correcciones, evaluaciones, visibilidad y estado administrativo.
- `meeting_status_history`: historial/auditoria de cambios relevantes.

El panel maestro puede completar, corregir y decidir cuando GHL no trae informacion suficiente. Esos cambios deben quedar persistidos y trazables. La sincronizacion futura hacia GHL debe partir de estos mismos campos, no de copias visuales.

### Origen de las reuniones (regla anti-duplicados)

Una reunion se sincroniza **desde el calendario de GHL** (cita). El calendario
es la fuente de verdad. Las oportunidades del pipeline **no** crean reuniones
cuando el contacto ya tiene una cita de calendario; solo se derivan reuniones
desde una oportunidad cuando esa reunion **no existe** como cita de calendario
(respaldo, para no perder reuniones que solo viven en el pipeline).

Motivo: antes se creaban dos filas por reunion (una desde la cita y otra desde
la oportunidad) y aparecian **duplicadas** en el panel. La regla vive en
`sync/scripts/derive_meetings_from_opportunities.py` (omite derivar si el
contacto ya tiene una `ghl_appointment_id` que no empieza con `opportunity:`).

Para ocultar un duplicado ya existente (o cualquier reunion) se usa el flag
`reuniones.excluida = true`; la vista `vw_reuniones_semana` y las paginas de
Intelligence Insight filtran por `excluida = false`. Es reversible.

## Acceso vigente

No existe un sistema de roles internos.

Francisca y Yanina usan la misma interfaz interna y tienen las mismas capacidades:

- ver todas las reuniones;
- editar Etapa Agenda;
- editar Evaluacion CP;
- completar ICP y BANT;
- escribir informacion para reunion;
- agregar justificacion y evidencia;
- cambiar SDR asignada;
- responder solicitudes de revision;
- consultar historial;
- cerrar Estado Final.

Los portales de clientes son paneles separados por cliente. No son vistas por rol interno.

## Despliegue y ramas

La rama de trabajo oficial es `main`.

Repositorio oficial unico:

- `FranciscaPP/conprospeccionOS2026`
- Rama: `main`

Estado verificado en Streamlit Cloud al 2026-06-27:

- App publica oficial: `https://conprospeccion-os2026.streamlit.app`
- Repository configurado: `franciscapp/conprospeccionOS2026`
- Branch configurada: `main`
- Main file path: `dashboard/app.py`

La app publica oficial ya despliega desde el repo oficial `FranciscaPP/conprospeccionOS2026`.

Regla practica:

1. Desarrollar y commitear en `main`.
2. Publicar a `origin main`.

No desarrollar directamente en `master`.

Estado 2026-07-03: la app antigua `conprospeccion-os.streamlit.app` fue
eliminada. Los repos historicos y los proyectos de Vercel quedaron
marcados para eliminacion manual por Francisca.

Vercel fue eliminado del producto por completo. No agregar `vercel.json`,
`package.json`, Next.js ni configuracion React por ningun motivo.

## Regla de paginas Streamlit

No dejar POCs, backups ni experimentos dentro de `dashboard/pages`. Streamlit
puede convertir esos archivos en paginas visibles.

## Documentacion relacionada

Indice de todos los documentos del repo. Antes de cambios amplios, leer los
marcados con (*).

- `ACTIVE_WORKSPACE.md` (*): estado operativo actual del workspace.
- `docs/SEGUIMIENTO_REUNIONES_RUNBOOK.md` (*): reglas funcionales, UI/UX, persistencia y deploy del panel de reuniones.
- `CONPROSPECCION_OS_RULEBOOK.md` (*): reglas generales de autoridad de Conprospeccion y portal cliente.
- `AGENTS.md`: puerta de entrada para Codex, Cursor y otras IA (apunta a este documento).
- `CLAUDE.md`: puerta de entrada para Claude (apunta a este documento).
- `AUDIT_REPORT.md`: informe historico de la auditoria 2026-07-03 (memoria, no reglas vigentes).
- `RLS_AUDIT.md`: informe de seguridad sobre RLS de Supabase (diagnostico y plan; no son reglas vigentes).

> Los informes (`AUDIT_REPORT.md`, `RLS_AUDIT.md`) son fotos de un momento
> para consulta. No definen reglas: las reglas vivas estan en este maestro y
> en los documentos marcados con (*).
