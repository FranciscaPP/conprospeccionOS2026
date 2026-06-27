# Conprospeccion OS2026

Aplicacion operativa oficial de Conprospeccion, desarrollada en Streamlit.

## Producto activo

- Entrada principal: `dashboard/app.py`
- Panel maestro interno: `dashboard/pages/1_Seguimiento_Reuniones.py`
- URL publica: `https://conprospeccion-os.streamlit.app/Seguimiento_Reuniones`
- URL local: `http://localhost:8502/Seguimiento_Reuniones`

Streamlit es la implementacion actual. Next.js, React, Vercel, Netlify, HTML mockups y prototipos antiguos no son producto activo.

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

Remotos:

- `origin`: `https://github.com/FranciscaPP/conprospeccionOS2026.git`
- `streamlit`: `https://github.com/FranciscaPP/conprospeccion-os.git`

Publicar:

```powershell
git push origin main
git push streamlit main
git push streamlit main:master
```

`master` no es rama de desarrollo. El push `main:master` solo mantiene compatibilidad con el deploy historico de Streamlit si la app esta apuntando a `master`.

## Regla de arquitectura

GoHighLevel es la fuente primaria de datos. Supabase es la base operacional de la aplicacion.

El panel interno de reuniones trabaja sobre registros canonicos compartidos con los portales cliente. No deben existir copias independientes por portal ni rutas POC activas dentro de `dashboard/pages`.
