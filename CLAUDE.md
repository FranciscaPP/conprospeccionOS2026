# Instrucciones para Claude Code

## Producto activo

El producto oficial es la aplicacion Streamlit:

- Entrada: `dashboard/app.py`
- Panel maestro interno: `dashboard/pages/1_Seguimiento_Reuniones.py`
- URL local: `http://localhost:8502/Seguimiento_Reuniones`
- URL publica oficial: `https://conprospeccion-os2026.streamlit.app/Seguimiento_Reuniones`

No trabajar en React, Next.js, Vercel, Netlify ni HTML mockups salvo instruccion explicita.

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

No trabajar en React, Next.js, Vercel ni Netlify salvo instruccion explicita.

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
