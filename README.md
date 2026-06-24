# Conprospección OS2026

Aplicación operativa oficial de Con Prospección, desarrollada en **Streamlit**.

## Inicio rápido

Desde la raíz del repositorio:

```powershell
python -m pip install -r dashboard/requirements.txt
python -m streamlit run dashboard/app.py --server.port 8502
```

También se puede ejecutar:

```text
iniciar_dashboard.bat
```

La aplicación queda disponible en:

```text
http://localhost:8502
```

## Estructura activa

```text
dashboard/    Aplicación Streamlit, páginas, autenticación y assets
shared/       Lógica Python compartida
sync/         Procesos de sincronización y reporting
supabase/     Migraciones y funciones de infraestructura
tests/        Pruebas del producto activo
```

El punto de entrada oficial es `dashboard/app.py`.

## Contexto para desarrollo

Leer antes de trabajar:

- `PROJECT_MASTER_CONTEXT.md`
- `ACTIVE_WORKSPACE.md`
- `AGENTS.md`

`archive/` es referencia histórica y no debe analizarse salvo petición explícita.

## Configuración

Usar `.env.example` como referencia y mantener las credenciales reales fuera de Git.

La aplicación consume datos desde Supabase. Los procesos que alimentan esos datos viven en `sync/` y `supabase/`.

## Regla de arquitectura

Streamlit es la única implementación actual. Next.js, React y Vercel no forman parte del producto activo.

