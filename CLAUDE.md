# Instrucciones para Claude Code

## Producto activo

El producto oficial es la aplicacion Streamlit:

- Entrada: `dashboard/app.py`
- Panel maestro interno: `dashboard/pages/1_Seguimiento_Reuniones.py`
- URL local: `http://localhost:8502/Seguimiento_Reuniones`
- URL publica: `https://conprospeccion-os.streamlit.app/Seguimiento_Reuniones`

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
- `tests/`
- `docs/`

No analizar ni modificar `archive/`, `.next/`, `.vercel/`, `.netlify/`, `node_modules/` ni prototipos fuera del alcance activo salvo que se pida explicitamente.

## Ramas y deploy

La rama de trabajo oficial es `main`.

Publicar:

```powershell
git push origin main
git push streamlit main:master
```

Estado verificado de Streamlit Cloud al 2026-06-27:

```text
Repository: conprospeccion-os
Branch: master
Main file path: dashboard/app.py
```

Ese repo historico se usa solo como deploy temporal. El objetivo pendiente es reconfigurar Streamlit Cloud para apuntar al repo oficial `FranciscaPP/conprospeccionOS2026`, branch `main`, archivo `dashboard/app.py`.

No desarrollar en `master`.

## Graphify

Este proyecto tiene grafo de conocimiento en `graphify-out/`.

Reglas:

- Para preguntas de codigo, primero usar `graphify query "<pregunta>"` cuando exista `graphify-out/graph.json`.
- Usar `graphify path "<A>" "<B>"` para relaciones y `graphify explain "<concepto>"` para conceptos puntuales.
- No leer masivamente `graphify-out/`; usar el CLI.
- Despues de modificar codigo o documentacion estructural, ejecutar `graphify update . --force`.

## Regla de paginas Streamlit

No dejar POCs, backups ni experimentos dentro de `dashboard/pages`. Streamlit puede convertir esos archivos en paginas visibles.
