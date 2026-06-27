# Contexto maestro del proyecto

Fecha de referencia: 2026-06-27

Este documento define la fuente oficial de verdad tecnica del repositorio Conprospeccion OS2026.

## Producto oficial

La aplicacion oficial actual es Streamlit.

- Entrada principal: `dashboard/app.py`
- Panel maestro interno: `dashboard/pages/1_Seguimiento_Reuniones.py`
- URL publica Streamlit: `https://conprospeccion-os.streamlit.app/Seguimiento_Reuniones`
- URL local esperada: `http://localhost:8502/Seguimiento_Reuniones`

Las carpetas de Next.js, React, Vercel, Netlify y prototipos visuales no son implementaciones activas del producto. Pueden conservar decisiones de negocio o referencias visuales, pero no deben usarse como base tecnica salvo instruccion explicita.

## Alcance activo

El trabajo ordinario debe limitarse a:

- `dashboard/`
- `shared/`
- `sync/`
- `supabase/`
- `tests/`
- `docs/`

No analizar ni modificar `archive/` salvo que se pida rescatar material historico.

## Datos canonicos

GoHighLevel sigue siendo la fuente primaria de datos de reuniones, contactos y agenda.

Supabase es la base operacional usada por la aplicacion:

- `reuniones`: datos canonicos sincronizados desde fuentes externas y campos base de reunion/contacto.
- `seguimiento_reuniones`: decisiones operativas internas, correcciones, evaluaciones, visibilidad y estado administrativo.
- `meeting_status_history`: historial/auditoria de cambios relevantes.

El panel maestro puede completar, corregir y decidir cuando GHL no trae informacion suficiente. Esos cambios deben quedar persistidos y trazables. La sincronizacion futura hacia GHL debe partir de estos mismos campos, no de copias visuales.

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

- App publica: `https://conprospeccion-os.streamlit.app`
- Repository configurado: `conprospeccion-os`
- Branch configurada: `master`
- Main file path: `dashboard/app.py`

Por lo tanto, el deploy publico todavia depende del repo historico `FranciscaPP/conprospeccion-os`.

Regla practica mientras no se migre Streamlit Cloud:

1. Desarrollar y commitear en `main`.
2. Publicar a `origin main`.
3. Espejar a `streamlit master` solo para no romper la app publica existente.

No desarrollar directamente en `master`.

Objetivo de orden:

1. Cambiar o recrear la app de Streamlit Cloud para que despliegue desde `FranciscaPP/conprospeccionOS2026`, branch `main`, archivo `dashboard/app.py`.
2. Probar que la app publica carga correctamente.
3. Eliminar el remoto local `streamlit`.
4. Archivar o eliminar el repo historico `FranciscaPP/conprospeccion-os`.

## Documentacion relacionada

- `ACTIVE_WORKSPACE.md`: estado operativo actual del workspace.
- `docs/SEGUIMIENTO_REUNIONES_RUNBOOK.md`: reglas funcionales, UI/UX, persistencia y deploy del panel de reuniones.
- `CONPROSPECCION_OS_RULEBOOK.md`: reglas generales de autoridad de Conprospeccion y portal cliente.
- `AGENTS.md`: instrucciones para agentes de codigo y Graphify.
