# Conprospeccion OS2026

Aplicacion operativa oficial de Conprospeccion, desarrollada en Streamlit.

## Producto activo

- Entrada principal: `dashboard/app.py`
- Panel maestro interno: `dashboard/pages/1_Seguimiento_Reuniones.py`
- URL publica oficial: `https://conprospeccion-os2026.streamlit.app/Seguimiento_Reuniones`
- URL local: `http://localhost:8502/Seguimiento_Reuniones`

Streamlit es la implementacion actual. Next.js, React, Vercel, Netlify, HTML mockups y prototipos antiguos no son producto activo.

`vercel.json` existe solo para impedir deployments automaticos del proyecto Vercel historico (incluye PRs). El producto activo es Streamlit Cloud. Si siguen llegando correos de `vercel[bot]`, desconecta el repo en el dashboard de Vercel.

## Inicio rapido

Desde la raiz del repositorio:

```powershell
python -m pip install -r requirements.txt
python -m streamlit run dashboard/app.py --server.port 8502
```

Tambien se puede ejecutar:

```text
iniciar_dashboard.bat
```

## Estructura activa

```text
dashboard/    Aplicacion Streamlit, paginas, autenticacion y assets
shared/       Logica Python compartida
sync/         Procesos de sincronizacion y reporting
supabase/     Migraciones y funciones de infraestructura
tests/        Pruebas del producto activo
docs/         Documentacion funcional y operativa
```

No analizar ni modificar `archive/` salvo peticion explicita.

## Documentacion obligatoria

Leer antes de trabajar:

- `PROJECT_MASTER_CONTEXT.md`
- `ACTIVE_WORKSPACE.md`
- `docs/SEGUIMIENTO_REUNIONES_RUNBOOK.md`
- `CONPROSPECCION_OS_RULEBOOK.md`
- `AGENTS.md`

## Despliegue Streamlit

Rama de trabajo oficial:

```text
main
```

Repositorio oficial:

- `https://github.com/FranciscaPP/conprospeccionOS2026`

Publicar codigo fuente:

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

El repo historico `FranciscaPP/conprospeccion-os` y la app antigua `https://conprospeccion-os.streamlit.app` no deben usarse para nuevos cambios.

No desarrollar en `master`.

## Regla de arquitectura

GoHighLevel es la fuente primaria de datos. Supabase es la base operacional de la aplicacion.

El panel interno de reuniones trabaja sobre registros canonicos compartidos con los portales cliente. No deben existir copias independientes por portal ni rutas POC activas dentro de `dashboard/pages`.
