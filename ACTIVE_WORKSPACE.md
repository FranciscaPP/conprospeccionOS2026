# Workspace activo

Fecha de referencia: 2026-07-03

## Estado actual

El workspace activo corresponde al producto Streamlit de Conprospeccion OS2026.

Ruta local:

```text
C:\Users\Admin\OneDrive\Documents\Con Prospeccion\conprospeccionOS2026
```

Branch activa esperada:

```text
main
```

## Que se debe tocar

Para trabajo normal del producto:

- `dashboard/`
- `shared/`
- `sync/`
- `supabase/`
- `mvp_setup/`
- `tests/`
- `docs/`
- `README.md`
- `PROJECT_MASTER_CONTEXT.md`
- `ACTIVE_WORKSPACE.md`
- `CONPROSPECCION_OS_RULEBOOK.md`

## Que no se debe tocar sin instruccion explicita

- `.vercel/`, `.netlify/`, `node_modules/` u otras carpetas locales de herramientas
- datos locales de clientes (`CLIENTES/`, bases Excel/CSV): nunca se suben al repo

Limpieza 2026-07-03: se eliminaron del repo `archive/`, `mockups/`,
`scripts/`, los mockups de `dashboard/` y todas las paginas de portal
cliente y Tiresias. El unico frente de desarrollo es el panel interno.

## Rutas oficiales

Panel interno oficial:

```text
dashboard/pages/1_Seguimiento_Reuniones.py
```

Portales cliente: eliminados del repo el 2026-07-03. Se reconstruiran
desde cero como proyeccion del panel interno. Referencia conservada:

```text
dashboard/pages/19_BambuTech_Intelligence_Insight.py
```

Modulo de onboarding de clientes (app Streamlit independiente):

```text
mvp_setup/app.py
```

## Ejecucion local

```powershell
python -m streamlit run dashboard/app.py --server.port 8502
```

Abrir:

```text
http://localhost:8502/Seguimiento_Reuniones
```

## Deploy vigente

Publicar siempre el codigo fuente en `main`:

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

El workspace local solo debe tener el remoto oficial:

```text
origin -> https://github.com/FranciscaPP/conprospeccionOS2026.git
```

No agregar nuevamente el remoto `streamlit` ni empujar al repo historico `FranciscaPP/conprospeccion-os`.

## Regla de orden

Si aparece una ruta POC, backup o experimento dentro de `dashboard/pages`, debe eliminarse o moverse fuera del arbol activo antes de deploy. Streamlit convierte los archivos de `dashboard/pages` en paginas visibles.
