# Estándar oficial de portal cliente — Conprospección OS

Fecha de vigencia: 2026-06-18  
Implementación oficial: Streamlit

Este documento conserva las reglas de UX e interfaz validadas durante el piloto GBS y
las convierte en estándar reutilizable para los próximos portales de clientes.

## 1. Estructura general

- Encabezado compacto con título, contexto, meta principal y marcas.
- KPIs accionables antes de los filtros.
- Orden: KPIs → filtros → tabla → drawer lateral.
- Tabla con encabezado fijo y sin doble scroll.
- Detalle en drawer al lado derecho, con ancho aproximado de 560 px.
- Colores de estados idénticos entre tabla, filtros y drawer.

## 2. Búsqueda y filtros

- La búsqueda principal cubre empresa, contacto y cargo.
- Al borrar completamente el texto, el listado se restablece automáticamente.
- Los filtros separan `Etapa de agenda` de `Estatus de validación`.
- Los KPI funcionan como filtros y se desactivan al volver a pulsarlos.

## 3. Legibilidad

- Las etiquetas de etapa y validación deben leerse sin esfuerzo.
- Los títulos de secciones del drawer usan morado de marca y jerarquía visual clara.
- El avance de meta permanece visible como progreso principal, sin sustituir los KPI.
- Los enlaces se presentan como acciones breves: abrir sitio, grabación o transcripción.

## 4. Validación de reuniones

- Se aplican íntegramente las reglas de `CONPROSPECCION_OS_RULEBOOK.md`.
- El cliente solo puede confirmar una evaluación positiva o solicitar revisión.
- El detalle muestra agenda, validación, información, evaluación, evidencia, acciones e historial.
- El historial utiliza eventos directos y evita encabezados genéricos duplicados.
- Las cotizaciones se presentan sin fecha de reunión y se consideran válidas por interés
  inmediato y traspaso al equipo comercial, cuando esa regla esté configurada para el cliente.

## 5. Referencia ICP

- La tarjeta ICP muestra `Cumple` o `No cumple`.
- Incluye una referencia compacta a países, industrias, tamaño de empresa y cargos objetivo.
- La fuente es el onboarding vigente del cliente.
- Debe indicar que la definición fue confirmada y validada con el cliente en onboarding.
- La reunión muestra solamente una síntesis y enlaza a `Resumen ICP acordado` en Onboarding.
- El resumen ICP se construye con todos los antecedentes útiles del onboarding, incluyendo
  definición explícita, exclusiones, propuesta de valor, dolores, gatillos y palabras clave.
- El cliente no edita el ICP desde el portal de validación.

## 6. Módulos y planes

- Los módulos contratables permanecen visibles en la navegación.
- Si un módulo aún no tiene datos, muestra un estado informativo de próxima activación.
- Si un módulo requiere plan premium, explica el requisito dentro de la página.
- El acceso interno de Conprospección conserva la vista completa de todos los módulos.
- Cambiar el plan del cliente habilita el contenido sin rediseñar el portal.

## 7. Evidencia

- Cuando existe evidencia se muestran únicamente acciones útiles:
  `Abrir grabación`, `Abrir transcripción` y `Confirmación Conprospección`.
- El resumen de IA apoya la reconfirmación de la reunión; no decide la validez final.
- BANT, evidencia y estados operativos permanecen bajo control interno.

## 8. Reutilización

Para un nuevo cliente se conserva esta estructura y se parametrizan:

- identidad visual;
- meta;
- ICP;
- etapas operativas específicas;
- plan y módulos habilitados;
- reglas particulares de cotización;
- fuentes de datos y sincronización.

No se debe reconstruir el portal desde cero ni recuperar interfaces React/Vercel archivadas.

## 9. Reglas operativas consolidadas

- Los datos asociados a reuniones son reales y se sincronizan desde las fuentes comerciales.
- Las proyecciones o datos modelados se limitan a Intelligence Insight y deben identificarse como tales.
- La reunión se asigna al SDR propietario actual del contacto; la agenda no redefine esa propiedad.
- Se conserva una sola reunión operativa por prospecto; citas reemplazadas y oportunidades duplicadas se excluyen.
- `Reunión agendada` no es una etapa visible. Según fecha y estado se utiliza `Reunión futura`,
  `Reunión realizada`, `Reagendar`, `Cancelada` o `Cotización`.
- Los filtros muestran su título arriba y el valor neutro `Todo` dentro del control.
- La validación histórica utiliza la fecha de evaluación o evidencia, nunca la fecha de carga técnica.
- Una excepción contractual debe incluir cláusula, evidencia y justificación visible.
- Los nombres técnicos de proveedores de CRM no se muestran al cliente; se utiliza `sistema comercial`.
- Onboarding mantiene documentos, enlaces, web, LinkedIn, ICP, agenda, oferta y respaldos del proyecto.
- Playbook SDR se presenta embebido dentro del portal, no como salida a una página aislada.
- Los módulos no incluidos en el plan permanecen visibles y muestran `No disponible en este plan`.
- La sincronización de BambuTech y GBS se ejecuta a las 08:00, 13:00 y 20:00 de `America/Santiago`.
