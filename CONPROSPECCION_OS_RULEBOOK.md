# Conprospección OS Rulebook

Fecha de vigencia: 2026-06-18  
Producto oficial: Streamlit  
Estado: fuente oficial de verdad

Nota de actualizacion 2026-06-27:

- El panel maestro interno de seguimiento de reuniones se rige por `docs/SEGUIMIENTO_REUNIONES_RUNBOOK.md`.
- Este Rulebook mantiene las reglas generales de autoridad de Conprospeccion, portal cliente y criterios contractuales.
- Si una regla antigua de UX del portal contradice el runbook del panel maestro, prevalece el runbook para el panel interno.
- La rama de trabajo oficial es `main`; `master` solo puede usarse como espejo tecnico de deploy Streamlit cuando sea necesario.

## 1. Autoridad de este documento

Este Rulebook define las reglas funcionales y de UX vigentes de Conprospección OS.

En caso de contradicción, prevalece sobre:

- implementaciones actuales o históricas;
- prototipos y resúmenes visuales;
- documentación anterior;
- tests que expresen reglas descartadas;
- comentarios dentro del código;
- contenido de `RESCUE_PLAN.md`.

`PROJECT_MASTER_CONTEXT.md` continúa definiendo el alcance técnico del proyecto. Este documento define el comportamiento funcional del producto.

El producto activo vive en:

- `dashboard/`
- `shared/`
- `tests/`
- `sync/`
- `supabase/`

`archive/` no forma parte del producto activo y no debe analizarse salvo instrucción explícita.

## 2. Origen y alcance de reglas heredadas

El producto oficial actual de Conprospección OS es la aplicación Streamlit.

Todo desarrollo activo debe realizarse bajo:

- `dashboard/`
- `shared/`
- `tests/`
- `sync/`
- `supabase/`

Vercel, Next.js y React quedan archivados y no constituyen una implementación activa.

Las reglas de negocio, flujos y decisiones de UX útiles que fueron definidas durante la etapa de Vercel pueden rescatarse como especificación funcional. Ese rescate no implica reactivar la aplicación, copiar sus componentes ni conservar su arquitectura.

Reglas obligatorias para material heredado:

1. No se debe copiar código de Vercel ni asumir su arquitectura como base del producto.
2. Una regla heredada desde Vercel solo es válida cuando no contradice este Rulebook.
3. Las decisiones definidas o implementadas recientemente en Streamlit también deben respetar este Rulebook.
4. Si la implementación actual de Streamlit contradice este Rulebook, la contradicción se considera deuda funcional que debe corregirse.
5. Si el contenido archivado de Vercel contradice este Rulebook, debe ignorarse.
6. `archive/` solo debe revisarse cuando el usuario solicite explícitamente rescatar una regla o referencia puntual.
7. El material archivado no debe utilizarse para búsquedas generales, comparaciones automáticas o decisiones de implementación.

Este Rulebook es el filtro final para aceptar, adaptar o descartar cualquier regla heredada, independientemente de su origen.

## 3. Principio rector

Conprospección es la autoridad contractual y operativa sobre el resultado final de una reunión.

El portal cliente permite confirmar una evaluación positiva de Conprospección o solicitar que sea revisada. No entrega al cliente control directo sobre estados negativos u operativos.

La IA, el BANT, la evidencia y las respuestas del cliente aportan información. Ninguno sustituye la resolución final de Conprospección.

## 4. Regla oficial del portal cliente

El cliente solo puede realizar dos acciones:

1. **Confirmar reunión**
2. **Solicitar revisión**

### 4.1 Confirmar reunión

Confirmar significa que el cliente está de acuerdo con la evaluación positiva presentada por Conprospección.

La confirmación:

- se registra en el historial;
- cierra la evaluación como válida cuando la evaluación de Conprospección es válida;
- permite que la reunión sume a la meta únicamente cuando el resultado final sea `válida`;
- no permite modificar BANT, evidencia ni estados operativos.

### 4.2 Solicitar revisión

Solicitar revisión significa que el cliente no está de acuerdo o necesita que Conprospección vuelva a evaluar la reunión.

La solicitud:

- exige seleccionar un motivo;
- exige escribir un comentario;
- queda registrada en el historial;
- mueve la reunión a `Cliente solicita revisión`;
- puede activar el indicador de disputa;
- no convierte automáticamente la reunión en no válida;
- no descuenta automáticamente la reunión de la meta;
- debe ser resuelta desde la vista interna por Conprospección.

### 4.3 Acciones prohibidas al cliente

El cliente no puede:

- rechazar una reunión;
- marcar una reunión como no válida;
- reagendar una reunión;
- cancelar una reunión;
- indicar que alguien no asistió;
- cambiar estados operativos;
- modificar la evaluación de Conprospección;
- modificar BANT o evidencia;
- decidir un resultado final negativo;
- aplicar un override sobre el resultado final.

Si el cliente informa una situación equivalente a rechazo, no asistencia, cancelación o reagendamiento, debe hacerlo mediante **Solicitar revisión**, usando motivo y comentario. Conprospección resuelve posteriormente el estado correcto.

## 5. Regla oficial de Conprospección

Conprospección es la autoridad final.

Solo la vista interna puede:

- evaluar la reunión;
- resolver una solicitud de revisión;
- marcar una reunión como no válida;
- marcar una reunión como reagendada;
- marcar una reunión como cancelada;
- registrar no asistencia del prospecto o del cliente;
- excluir una reunión;
- corregir estados operativos;
- aplicar una resolución final u override;
- determinar si una reunión cuenta para la meta.

Toda resolución interna que cambie el resultado debe quedar registrada en el historial con:

- campo modificado;
- valor anterior;
- valor nuevo;
- usuario o actor;
- rol;
- fecha y hora;
- fuente de la modificación.

## 6. Estados oficiales del flujo

La interfaz debe utilizar únicamente estos siete estados funcionales:

| Estado | Significado |
|---|---|
| `Reunión futura` | La fecha aún no ocurre. No admite acción de validación del cliente. |
| `Reunión cancelada` | Existe una cancelación operativa resuelta por Conprospección. |
| `Pendiente evaluación CP` | Conprospección todavía no completa su evaluación. |
| `Pendiente evaluación cliente` | Conprospección evaluó la reunión y espera Confirmar o Solicitar revisión. |
| `Cliente solicita revisión` | El cliente pidió reevaluación con motivo y comentario. |
| `Evaluación cerrada válida` | Conprospección resolvió que la reunión es válida. |
| `Evaluación cerrada no válida` | Conprospección resolvió que la reunión no es válida. |

No deben aparecer como estados oficiales del portal:

- cliente rechazó;
- cliente marcó no válida;
- cliente reagendó;
- cliente canceló;
- cliente no asistió;
- prospecto no asistió, si aún no fue resuelto internamente.

Esos conceptos pueden existir como datos operativos internos, pero su resolución corresponde a Conprospección.

## 7. Resultado final y disputa

### 7.1 Resultado válido

Una reunión cuenta como válida cuando Conprospección la resuelve como válida.

La confirmación del cliente puede cerrar una evaluación positiva, pero no sustituye la evaluación previa de Conprospección.

### 7.2 Solicitud de revisión

Una solicitud de revisión:

- mantiene pendiente la resolución final;
- queda visible para el equipo interno;
- puede clasificarse como disputa;
- requiere resolución manual de Conprospección;
- no equivale a `no válida`.

### 7.3 Resultado negativo

Solo Conprospección puede cerrar una reunión como:

- no válida;
- cancelada;
- reagendada;
- no asistió;
- excluida;
- cualquier otro resultado operativo negativo.

## 8. KPI oficiales

El portal de validación GBS debe mostrar exactamente:

1. **Total reuniones**
2. **Válidas**
3. **No válidas**
4. **Avance meta**

### 8.1 Definiciones

**Total reuniones**

Reuniones del mismo conjunto visible según periodo y filtros.

**Válidas**

Reuniones con resultado final cerrado como válido.

**No válidas**

Reuniones con resultado final cerrado como no válido por Conprospección.

**Avance meta**

Avance contractual basado exclusivamente en reuniones finales válidas.

`Pendiente evaluación cliente` y `Cliente solicita revisión` se muestran como
estado, filtro, etiqueta o aviso operativo, pero no como KPI principal.

### 8.2 Regla de conteo

- Solo las reuniones con resultado final `válida` suman a la meta.
- Una confirmación no debe contar si Conprospección todavía no emitió evaluación válida.
- Una solicitud de revisión no suma como una nueva válida.
- Una solicitud de revisión o disputa no descuenta automáticamente una reunión ya contabilizada.
- Cualquier ajuste de meta por resolución negativa debe ocurrir cuando Conprospección cierre la revisión.
- Los KPI deben recalcularse después de cada resolución persistida.

## 9. UX oficial

La jerarquía de la página es:

1. KPIs
2. Filtros
3. Tabla
4. Drawer de detalle

No se debe alterar esta jerarquía sin actualizar primero este Rulebook.

### 9.1 Header

Debe incluir:

- identidad del portal;
- periodo o contexto actual cuando corresponda;
- avance de meta visible;
- acceso a navegación y sesión.

### 9.2 KPIs

Los KPI oficiales deben aparecer antes de los filtros y funcionar como resumen del mismo conjunto de reuniones visible en la página.

### 9.3 Filtros

Los filtros deben operar sobre los estados oficiales y no introducir estados alternativos.

### 9.4 Tabla mínima

La tabla debe priorizar:

- fecha;
- hora;
- empresa;
- contacto;
- estado oficial.

La tabla abre el detalle; no debe convertirse en un formulario de edición.

### 9.5 Drawer

El drawer debe contener, en este orden:

1. Contacto y empresa
2. Resumen de la reunión
3. Evaluación de Conprospección
4. Evidencia
5. Acción cliente
6. Historial

### 9.6 Acción cliente

La sección de acción cliente contiene exclusivamente:

- **Confirmar**
- **Solicitar revisión**

Al solicitar revisión:

- el motivo es obligatorio;
- el comentario es obligatorio;
- no se ofrece una opción de rechazo;
- no se ofrece una opción de reagendamiento;
- no se ofrece una opción de no válida.

Después de guardar:

- debe persistirse la respuesta;
- debe registrarse el historial;
- deben invalidarse los datos cacheados necesarios;
- al recargar debe mantenerse la respuesta;
- los KPI y el estado deben reflejar el dato persistido.

## 10. Evidencia e IA

La evidencia puede incluir:

- grabación;
- transcripción;
- resumen;
- observaciones;
- señales BANT;
- otros antecedentes verificables.

La IA puede:

- resumir;
- detectar señales;
- sugerir;
- destacar inconsistencias;
- asistir la revisión.

La IA no puede:

- cerrar una reunión como válida o no válida;
- resolver una disputa;
- reemplazar a Conprospección;
- modificar la meta por sí sola;
- presentar su inferencia como decisión definitiva.

### 10.1 Información para reunión

`Información para reunión` es un antecedente distinto de la justificación y del
resumen generado por IA. Su fuente GHL es
`{{contact.informacin_de_preparacin_para_la_reunin}}`.

- puede sincronizarse desde `customFields` o `raw_data`;
- si falta, el equipo interno puede completarla manualmente;
- la edición manual interna debe reflejarse en el portal cliente;
- si está vacía, el portal no muestra el bloque;
- no se reemplaza definitivamente por `ai_summary`;
- no se inventa ni se duplica desde la justificación.

### 10.2 BANT e ICP

El BANT SDR proviene de `{{contact.validacin_sdr_bant}}` y puede completarse
manualmente en Seguimiento. El cliente nunca lo edita.

BANT, ICP, evidencia, próximos pasos, plan, cierre y fechas informan la
evaluación, pero no cierran automáticamente una reunión como válida o no válida.
Solo Conprospección resuelve la validez.

Para GBS, una reunión cumple ICP salvo que esté cancelada, sin perjuicio de que
Conprospección pueda registrar el antecedente explícitamente.

### 10.3 Campos vacíos

El portal muestra únicamente datos reales. No presenta etiquetas, filas,
botones o bloques vacíos ni placeholders como `N/A`, `Sin dato`,
`No disponible`, `null` o `—`.

### 10.4 Resumen y justificación

`Información para reunión`, resumen IA y justificación son conceptos separados.
La justificación puede apoyarse en evaluación CP, ICP, BANT, evidencia e
información SDR/GHL, sin inventar antecedentes ni duplicar el resumen.

### 10.5 Reuniones futuras

Una reunión futura:

- usa el estado `Reunión futura`;
- no admite Confirmar ni Solicitar revisión;
- no cuenta como pendiente de evaluación cliente;
- no afecta la meta;
- muestra únicamente los datos reales disponibles;
- informa claramente que todavía no admite acciones.

## 11. Historial oficial

El historial es obligatorio para:

- confirmación del cliente;
- solicitud de revisión;
- evaluación de Conprospección;
- resolución final;
- cambios operativos internos;
- overrides;
- correcciones posteriores.
- edición manual interna de BANT;
- edición manual de Información para reunión;
- `Reunión realizada` como hito, nunca como estado funcional vigente.

El mismo estado funcional oficial debe usarse en portal cliente, Seguimiento
interno, filtros, tabla, detalle e historial. No existen estados funcionales
adicionales como `Reunión realizada` o `Revisada por CP`.

Un guardado no debe presentarse como completo si falla el registro crítico de la respuesta o de la resolución.

El historial debe permitir reconstruir qué ocurrió, quién decidió y en qué orden.

## 12. Decisiones descartadas

Quedan oficialmente descartadas:

- cliente eligiendo válida o no válida;
- cliente rechazando reuniones;
- cliente reagendando reuniones;
- cliente registrando cancelaciones o no asistencia;
- cliente decidiendo un resultado final negativo;
- regla “el cliente manda”;
- tema visual diferente para cada cliente;
- IA como decisora;
- BANT como decisión automática definitiva;
- prototipos con botones `Validar`, `No validar`, `Pedir revisión` y `Reagendar`;
- formularios cliente que editen estado comercial o información operativa interna.

Los resúmenes visuales anteriores que muestran esas opciones se conservan solo como referencia histórica de UX, no como especificación vigente.

## 13. Tema visual

El producto utiliza un sistema visual común de Conprospección.

Los logos y contenidos pueden variar por cliente, pero no debe existir un tema estructural independiente por cliente.

Los colores semánticos pueden diferenciar:

- válido;
- pendiente;
- revisión o disputa;
- no válido;
- cancelado.

El color acompaña al texto y nunca reemplaza la etiqueta del estado.

## 14. Criterios mínimos para pruebas reales

El portal está listo para una prueba real cuando:

- el cliente inicia sesión;
- puede abrir una reunión;
- solo ve Confirmar y Solicitar revisión;
- una reunión futura no admite validación;
- Confirmar persiste y aparece después de recargar;
- Solicitar revisión exige motivo y comentario;
- la revisión persiste y aparece después de recargar;
- cada acción aparece en el historial;
- los KPI se recalculan desde datos persistidos;
- solo las válidas finales suman a la meta;
- la revisión queda pendiente de resolución interna;
- la vista interna puede cerrar la revisión;
- no existe una vía cliente para rechazar, reagendar o marcar no válida.

## 15. Desalineaciones conocidas

Al momento de publicar este Rulebook, pueden existir implementaciones recientes que todavía:

- muestran rechazo al cliente;
- muestran reagendamiento al cliente;
- permiten guardar `no_valida` o `reagendada` desde el portal;
- contienen tests basados en esas acciones;
- muestran KPI o estados no alineados.

Esas implementaciones no cambian la regla oficial. Deben corregirse en una tarea posterior, con este Rulebook como criterio de aceptación.

No se debe modificar código como efecto automático de actualizar este documento.
