# Diseño: bot operativo `@equipo_alicia_bot`

Fecha: 2026-09-24

## Objetivo y límites

Ampliar el bot operativo existente identificado por Telegram como
`@equipo_alicia_bot` para medir la ejecución diaria de la única SDR, Nora, en
BAMBU TECH, GBS y BALIA.

Este trabajo no modifica ni reutiliza como canal de salida:

- el bot separado de Reuniones Cliente (`TELEGRAM_REUNIONES_TOKEN`);
- los bots interactivos por cliente (`TELEGRAM_BOT_*_TOKEN`);
- sus mensajes, callbacks o tarjetas.

Toda salida del nuevo seguimiento usa exclusivamente `TELEGRAM_SDR_TOKEN`, cuya
identidad fue verificada con Telegram como `equipo_alicia_bot`.

## Decisiones confirmadas

- SDR única: Nora.
- Todo registro presente en las tres subcuentas se atribuye operativamente a
  Nora aunque GHL muestre otro usuario. El identificador original se conserva
  solo para auditoría.
- Zona horaria canónica: `America/Santiago`.
- El horario se repite de lunes a viernes:

| Hora Chile | Actividad |
|---|---|
| 11:00–12:00 | BALIA |
| 12:00–13:00 | GBS |
| 13:00–16:00 | BAMBU TECH |
| 16:00–17:00 | Almuerzo, excluido |
| 17:00–18:00 | GBS |
| 18:00–20:00 | BAMBU TECH |

- Un hueco operativo es un período de al menos 20 minutos sin actividad
  registrada dentro de un bloque de cliente. El almuerzo y el tiempo fuera de
  bloques se excluyen.
- Los resultados posteriores de las reuniones no pertenecen a este bot.

## Arquitectura

Se conservarán los dos puntos de entrada actuales del mismo bot:

- `report_sdr_telegram.py`: envíos programados;
- `report_sdr_bot.py`: consultas interactivas.

La lógica de negocio dejará de vivir dentro del formateador. Se extraerá a
módulos compartidos y comprobables:

1. configuración de clientes, colores, zona y bloques;
2. recolectores GHL/Snov/Supabase;
3. normalización y deduplicación de eventos;
4. cálculo de métricas y comparaciones;
5. snapshots históricos;
6. render HTML de Telegram;
7. generación de PNG de cierre y semana;
8. control de alertas ya enviadas.

Los recolectores devuelven eventos canónicos. Los reportes y gráficos consumen
esos eventos o snapshots; no vuelven a calcular una segunda versión de cada
métrica.

## Fuentes reales auditadas

### Tareas

Fuente: endpoint GHL `POST /locations/{location_id}/tasks/search`, ya consumido
por `fetch_tasks` en `report_tareas.py`.

Campos confirmados: `_id`, `contactId`, `title`, `body`, `dueDate`,
`completed`, `dateAdded`, `dateUpdated`, `assignedTo` y
`assignedToUserDetails`.

La meta se congela al inicio de jornada:

`meta = tareas vencidas abiertas al inicio + tareas con vencimiento hoy`.

Una tarea completada cuenta una sola vez por `_id`. El arrastre inicial no
cambia aunque una tarea se resuelva después. Las categorías reutilizan
`tipo_de`; se ampliarán sus alias con ejemplos reales de los tres clientes.

### Llamadas

Fuente: conversaciones y mensajes GHL `TYPE_CALL`, mediante
`fetch_calls`, `call_status`, `call_duration` y `classify` de
`report_calls_live.py`.

Campos usados: id de mensaje, `contactId`, `dateAdded`, `dateUpdated`,
`direction`, `status` o `meta.call.status`, y `meta.call.duration`.

- Solo se cuentan llamadas salientes.
- Contactos trabajados se deduplican por `(cliente, contactId, fecha)`.
- Llamadas se deduplican por id de mensaje; si el id no está disponible, se
  usa una clave estable con cliente, contacto, timestamp y dirección.
- `completed` es la fuente principal de llamada contestada.
- Conversación relevante conserva el fallback existente de 20 segundos y se
  etiqueta como regla de respaldo, no como estado GHL.
- `meta.call.duration` se trata como conversación.
- GHL no expone hoy un campo de ring independiente. La diferencia
  `dateUpdated - dateAdded` es una aproximación de duración total y conserva
  los topes defensivos existentes. El reporte la rotulará como estimada; no se
  presentará como medición exacta mientras la fuente no mejore.

### Contactos, estados y movimientos

Fuentes: `contacts/search`, contacto GHL, oportunidades abiertas, pipelines y
los timestamps `dateAdded`, `dateUpdated`, `lastStageChangeAt` y
`lastStatusChangeAt` ya usados por los scripts actuales y sincronizados a
Supabase.

Los movimientos se detectan comparando snapshots consecutivos por contacto u
oportunidad. Esto permite guardar transiciones completas sin inferirlas desde
el estado final actual.

### Reuniones agendadas

Fuente: eventos del calendario GHL. Se reutiliza la lectura de calendarios y
eventos existente, pero no la clasificación posterior del bot Reuniones
Cliente.

La deduplicación usa `appointment id`; como respaldo, cliente + contacto +
inicio. Solo se mide el evento nuevo de agendamiento. Se excluyen no-show,
validez, realización y resultados posteriores.

La alerta inmediata incluirá exclusivamente datos disponibles. El origen se
toma de metadatos GHL o del evento precedente detectable; en ausencia de una
fuente confiable se mostrará `Desconocido`.

### Email

- Respuestas Snov se reutilizan desde los eventos ya sincronizados y el flujo
  `sync_snov_replies_to_ghl.py`.
- No se cuentan envíos automáticos de campaña.
- Mensajes de email en conversaciones GHL solo se clasifican como manuales
  cuando la fuente ofrece una marca o autor confiable.
- Si no puede distinguirse manual de automático, el KPI se omite o se marca
  como no disponible; nunca se estima.

### Actividad registrada

Eventos admitidos: llamadas, finalización de tareas, cambios de estado o etapa,
email manual confirmado, gestión de oportunidad y agendamiento.

Cada evento conserva cliente, contacto, tipo, timestamp, identificador fuente
y payload mínimo auditable. No se llama a esta métrica “hora trabajada”.

## Persistencia

Una migración aditiva creará:

### `sdr_activity_events`

Eventos normalizados e idempotentes. Clave única por `source`, `source_id` y
cliente. Guarda timestamp, tipo, cliente, contacto, datos de duración y
metadatos auditables.

### `sdr_daily_baselines`

Congela por día y cliente las tareas de hoy, el arrastre inicial, sus ids y
clasificación. Una fila por fecha/cliente.

### `sdr_hourly_snapshots`

Una fila por fecha, hora de corte y alcance (`total` o cliente). Guarda el
documento completo de métricas calculadas y una versión de esquema. Un upsert
repetido no duplica el corte.

### `sdr_alert_state`

Huella, severidad y último envío de cada alerta para no repetir mensajes sin
cambio significativo.

Esta persistencia permite reconstruir el reporte aunque GHL cambie el estado
actual de una tarea o contacto.

## Cálculos

### Meta, arrastre y brecha

- Denominador diario fijo: baseline inicial.
- Numerador: ids del baseline completados hasta la hora de corte.
- `pendientes hoy` y `arrastre pendiente` se mantienen separados.
- Mayor rezago porcentual exige al menos tres tareas.
- Mayor volumen pendiente usa cantidad absoluta.

### Actividad y huecos

Los eventos se ordenan dentro de cada bloque. Una actividad genera un intervalo
desde su timestamp hasta el fin real de la llamada cuando corresponda; para
eventos instantáneos no se inventa duración. Los huecos son intervalos de 20
minutos o más no cubiertos entre el inicio transcurrido del bloque y los
eventos registrados. Se informa siempre “sin actividad registrada”.

`Tiempo con actividad registrada` será la unión de intervalos con duración
real conocida. Los eventos instantáneos prueban actividad y cortan un hueco,
pero no agregan minutos ficticios.

### Adherencia

Se calcularán por cliente:

- actividad del cliente dentro de sus bloques / actividad total del cliente;
- actividad telefónica dentro del bloque / actividad telefónica total;
- tareas completadas dentro del bloque / tareas completadas del cliente;
- minutos sin actividad registrada / minutos transcurridos asignados.

El indicador principal de adherencia combina datos observables y mostrará sus
componentes. La ventana crítica telefónica usa exclusivamente actividad
telefónica dentro del horario correcto. El rezago intradía compara avance de
tareas contra proporción transcurrida de los bloques aplicables.

### Comparaciones

Cada reporte horario busca el snapshot de ayer con la misma hora de corte. Si
no existe, informa que no hay base comparable; no usa el cierre completo de
ayer.

El cierre diario usa el último snapshot de las 20:00 y agrega la brecha
obligatoria. El semanal agrega los cierres lunes–viernes y los eventos
canónicos, no suma snapshots horarios entre sí.

## Mensajes y diseño visual

Telegram usará `parse_mode=HTML`, escape de contenido dinámico y tablas
`<pre>` de máximo cinco columnas. El reporte horario tendrá como máximo tres
mensajes en el orden solicitado.

Colores de PNG:

- BAMBU TECH `#22C55E`;
- GBS `#8B5CF6`;
- BALIA `#EC4899`;
- TOTAL `#334155`;
- fondo `#F8FAFC`, tarjetas `#FFFFFF`;
- texto principal `#0F172A`, secundario `#64748B`;
- hueco/crítico `#DC2626`.

Los mensajes normales usan los emojis de cliente y estado definidos en el
requerimiento. No se intenta colorear texto de Telegram.

## Ejecución programada

- Baseline: 10:55 Chile, antes del primer bloque.
- Reporte horario: cortes de 12:00 a 20:00 Chile.
- Cierre diario: 20:00 Chile, después de incorporar los eventos del último
  bloque.
- Alerta de nueva reunión: monitor idempotente con sondeo frecuente; solo
  envía eventos no notificados.
- Cierre semanal: viernes después del cierre diario.
- Consultas interactivas: continúan en el proceso de long-polling del mismo
  bot y leen el mismo motor/snapshots.

Las tareas de Windows existentes se ajustarán solo para los puntos de entrada
de `@equipo_alicia_bot`. No se modificarán las tareas del bot Reuniones
Cliente.

## Implementación por fases

1. Base compartida, BALIA, HTML, horario oficial y pruebas.
2. Baseline de tareas, snapshots, meta/arrastre/brecha y comparación.
3. Eventos de llamadas/actividad, adherencia y huecos.
4. Reuniones nuevas y alerta inmediata.
5. Email manual verificable y movimientos del funnel.
6. Cierre diario, gráficos y semanal.
7. Activación programada, ejecución en seco y validación de identidad del
   bot antes del primer envío real.

Cada fase se desarrolla con pruebas primero. La activación real ocurre solo
después de comprobar mensajes en modo seco y verificar nuevamente que el token
corresponde a `@equipo_alicia_bot`.

## Manejo de errores

- Una subcuenta fallida no elimina las otras del reporte; se marca la sección
  como no disponible.
- Ningún cero sustituye una consulta fallida.
- Los upserts son idempotentes.
- Telegram se reintenta ante fallos transitorios sin duplicar alertas.
- Todo contenido GHL se escapa antes de insertarse en HTML.
- Se registra la versión del cálculo en cada snapshot.

## Criterios de aceptación

- Los tres clientes y TOTAL aparecen consistentemente.
- Todo se atribuye a Nora y no aparece “Norma”.
- El bot verificado es `@equipo_alicia_bot` y ningún otro token se usa.
- Las metas provienen de tareas, con arrastre inicial separado.
- Llamadas y contactos únicos no se confunden.
- No se duplica duración ni se declara exacto un dato estimado.
- Los huecos solo existen dentro de bloques y nunca incluyen almuerzo.
- “Hoy vs ayer” compara la misma hora mediante snapshots.
- Reuniones mide solo agendamiento.
- Email automático no cuenta como trabajo manual.
- Reporte horario: máximo tres mensajes, HTML válido y orden constante.
- Cierre y semanal generan PNG con la paleta oficial.
- No hay cambios en archivos ni configuraciones de otros bots.

