# Modelo de accesos vigente

Fecha de referencia: 2026-06-27

## Principio

El panel maestro interno lo usan dos usuarios con distinto alcance:

- **Francisca** — acceso completo a todos los modulos internos.
- **Nora** — acceso restringido: solo el panel Seguimiento Reuniones. Dentro de
  ese panel tiene las mismas capacidades operativas que Francisca.

La lista de paginas permitidas por usuario restringido vive en
`_RESTRICTED_PAGES` (`dashboard/master_auth.py`). Para Nora se ocultan del menu
las demas paginas y el acceso directo por URL redirige a Seguimiento Reuniones.

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

- perfiles de administrador, supervisor o SDR;
- logica RBAC generica ni jerarquia de roles.

La unica diferenciacion soportada es la lista blanca de paginas por usuario
(`_RESTRICTED_PAGES`), usada hoy para acotar a Nora a Seguimiento Reuniones.

## Portales cliente

Estado 2026-07-03: los portales cliente fueron eliminados del repo por
decision de Francisca. Se reconstruiran desde cero como proyeccion del
panel interno. La unica pagina cliente conservada como referencia es
`dashboard/pages/19_BambuTech_Intelligence_Insight.py` (acceso via
`dashboard/portal_auth.py`).

Reglas que deben regir los portales futuros (sin cambio):

- Los portales son paneles separados por cliente. No son vistas por rol interno.
- Cada cliente solo ve reuniones de su propio `cliente_slug`.
- El cliente puede confirmar o solicitar revision (con motivo obligatorio). No puede decidir Estado Final ni modificar Evaluacion CP, BANT, ICP, evidencia interna o notas internas.

## Seguridad pendiente

La separacion por cliente ya existe en la aplicacion. Como mejora de seguridad, Supabase debe reforzarla con RLS.

Politicas futuras:

- Francisca/Nora: leer y escribir todo (Nora solo desde Seguimiento Reuniones).
- Cada cliente: leer solo su `cliente_slug`.
- Cada cliente: escribir solo campos permitidos de Evaluacion Cliente, cuando corresponda.
- Servicio de sincronizacion: escribir datos tecnicos sincronizados.
- Historial cliente: mostrar solo eventos marcados como visibles.

Estas politicas no cambian la logica funcional actual; solo evitan que un error de aplicacion exponga datos cruzados.
