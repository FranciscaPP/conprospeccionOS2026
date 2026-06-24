# Workspace activo

## Ruta oficial

```text
C:\Users\Admin\OneDrive\Documents\Con Prospección\conprospeccionOS2026
```

Entrada de Streamlit:

```text
C:\Users\Admin\OneDrive\Documents\Con Prospección\conprospeccionOS2026\dashboard\app.py
```

## Comando de ejecución

Ejecutar desde la raíz:

```powershell
python -m streamlit run dashboard/app.py --server.port 8502
```

O ejecutar:

```text
iniciar_dashboard.bat
```

URL local:

```text
http://localhost:8502
```

## Archivos principales

- `dashboard/app.py`: entrada principal.
- `dashboard/pages/*.py`: páginas Streamlit.
- `dashboard/master_auth.py`: acceso interno.
- `dashboard/portal_auth.py`: acceso y navegación de clientes.
- `dashboard/assets/`: recursos visuales activos.
- `shared/config.py`: configuración compartida.
- `shared/validacion.py`: reglas de validación.
- `shared/validacion_ui.py`: presentación de estados.
- `shared/seguimiento.py`: operaciones de seguimiento.
- `shared/metas.py`, `shared/kpis.py`: metas e indicadores.
- `tests/*.py`: pruebas del núcleo Python.

`sync/` y `supabase/` son activos, pero solo deben modificarse cuando la tarea trate explícitamente de sincronización, base de datos o integraciones.

## No tocar por defecto

- `archive/`: historia; no analizar salvo instrucción explícita.
- `.next/`, `node_modules/`, `.vercel/`, `.netlify/`: artefactos ajenos al producto activo.
- `graphify-out/`: generado automáticamente; consultar mediante `graphify`.
- Integraciones de `sync/` y `supabase/` si la tarea es únicamente de UI o lógica Streamlit.
- Datos locales, credenciales y archivos `.env`.

No borrar, rediseñar o refactorizar fuera del alcance solicitado.

