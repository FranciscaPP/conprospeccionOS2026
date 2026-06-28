# Modelo de accesos vigente

Fecha de referencia: 2026-06-27

## Principio

No existe un sistema de multiples roles internos.

El panel maestro interno lo usan Francisca y Yanina. Ambas tienen exactamente las mismas capacidades operativas.

## Panel interno

Ruta:

```text
https://conprospeccion-os2026.streamlit.app/Seguimiento_Reuniones
```

Implementacion:

```text
dashboard/master_auth.py
dashboard/pages/1_Seguimiento_Reuniones.py
```

Capacidades internas:

- ver todas las reuniones;
- editar Etapa Agenda;
- editar Evaluacion CP;
- completar ICP y BANT;
- escribir informacion para reunion;
- agregar justificacion y evidencia;
- cambiar SDR asignada;
- responder solicitudes de revision;
- consultar historial;
- definir Estado Final manualmente.

No crear:

- roles internos;
- permisos diferenciados entre Francisca y Yanina;
- perfiles de administrador, supervisor o SDR;
- logica RBAC interna.

## Portales cliente

Los portales cliente son paneles separados por cliente. No son vistas por rol interno.

Rutas activas:

```text
dashboard/pages/12_GBS_Validacion_Reuniones.py
dashboard/pages/7_Clickie_Validacion_Reuniones.py
dashboard/pages/18_BambuTech_Validacion_Reuniones.py
```

Implementacion de acceso:

```text
dashboard/portal_auth.py
```

Regla:

- GBS solo ve reuniones `cliente_slug = 'gbs'`.
- Clickie solo ve reuniones `cliente_slug = 'clickie'`.
- BambuTech solo ve reuniones `cliente_slug = 'bambutech'`.

El cliente puede confirmar o solicitar revision desde su portal. No puede decidir Estado Final ni modificar Evaluacion CP, BANT, ICP, evidencia interna o notas internas.

## Seguridad pendiente

La separacion por cliente ya existe en la aplicacion. Como mejora de seguridad, Supabase debe reforzarla con RLS.

Politicas futuras:

- Francisca/Yanina: leer y escribir todo.
- Cada cliente: leer solo su `cliente_slug`.
- Cada cliente: escribir solo campos permitidos de Evaluacion Cliente, cuando corresponda.
- Servicio de sincronizacion: escribir datos tecnicos sincronizados.
- Historial cliente: mostrar solo eventos marcados como visibles.

Estas politicas no cambian la logica funcional actual; solo evitan que un error de aplicacion exponga datos cruzados.
