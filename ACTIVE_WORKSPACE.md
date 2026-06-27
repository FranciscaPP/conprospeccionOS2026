# Workspace activo

Fecha de referencia: 2026-06-27

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
- `tests/`
- `docs/`
- `README.md`
- `PROJECT_MASTER_CONTEXT.md`
- `ACTIVE_WORKSPACE.md`
- `CONPROSPECCION_OS_RULEBOOK.md`

## Que no se debe tocar sin instruccion explicita

- `archive/`
- `.next/`
- `.vercel/`
- `.netlify/`
- `node_modules/`
- prototipos HTML bajo `mockups/`
- carpetas historicas de React/Next (`app/`, `components/`, `lib/`) cuando el cambio sea del producto Streamlit

Estas carpetas pueden existir por historia del proyecto, pero no son el producto activo.

## Rutas oficiales

Panel interno oficial:

```text
dashboard/pages/1_Seguimiento_Reuniones.py
```

Portales cliente activos:

```text
dashboard/pages/12_GBS_Validacion_Reuniones.py
dashboard/pages/7_Clickie_Validacion_Reuniones.py
dashboard/pages/18_BambuTech_Validacion_Reuniones.py
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
Repository: conprospeccion-os
Branch: master
Main file path: dashboard/app.py
```

Mientras la app publica siga apuntando al repo historico, tambien se debe espejar el deploy:

```powershell
git push streamlit main:master
```

Objetivo pendiente: reconfigurar Streamlit Cloud para que apunte a `FranciscaPP/conprospeccionOS2026`, branch `main`, archivo `dashboard/app.py`. Despues de eso, eliminar el remoto `streamlit` y dejar de usar el repo historico `FranciscaPP/conprospeccion-os`.

## Regla de orden

Si aparece una ruta POC, backup o experimento dentro de `dashboard/pages`, debe eliminarse o moverse fuera del arbol activo antes de deploy. Streamlit convierte los archivos de `dashboard/pages` en paginas visibles.
