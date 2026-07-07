# Instrucciones para Claude Code

## Producto activo

El producto oficial es la aplicacion Streamlit:

- Entrada: `dashboard/app.py`
- Panel maestro interno: `dashboard/pages/1_Seguimiento_Reuniones.py`
- URL local: `http://localhost:8502/Seguimiento_Reuniones`
- URL publica oficial: `https://conprospeccion-os2026.streamlit.app/Seguimiento_Reuniones`

No trabajar en React, Next.js, Vercel, Netlify ni HTML mockups salvo instruccion explicita.

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

Fuente de verdad de datos: la base Supabase viva (el repo no refleja todo
el esquema).

## Documentos que debes leer antes de cambios amplios

- `PROJECT_MASTER_CONTEXT.md`
- `ACTIVE_WORKSPACE.md`
- `docs/SEGUIMIENTO_REUNIONES_RUNBOOK.md`
- `CONPROSPECCION_OS_RULEBOOK.md`
- `AGENTS.md`

## Alcance activo

Trabajar normalmente solo en:

- `dashboard/`
- `shared/`
- `sync/`
- `supabase/`
- `mvp_setup/`
- `tests/`
- `docs/`

Estado 2026-07-03: los portales cliente fueron eliminados del repo. Se
reconstruiran desde cero como proyeccion del panel interno. La unica
pagina cliente que sobrevive es `19_BambuTech_Intelligence_Insight.py`,
conservada como ejemplo/referencia.

## Ramas y deploy

La rama de trabajo oficial es `main`.

Publicar:

```powershell
git push origin main
```

Estado verificado de Streamlit Cloud al 2026-06-27:

```text
App URL: https://conprospeccion-os2026.streamlit.app
Repository: franciscapp/conprospeccionOS2026
Branch: main
Main file path: dashboard/app.py
```

No usar el repo historico `FranciscaPP/conprospeccion-os` ni agregar remoto `streamlit`.

No desarrollar en `master`.

## Regla de paginas Streamlit

No dejar POCs, backups ni experimentos dentro de `dashboard/pages`. Streamlit puede convertir esos archivos en paginas visibles.
