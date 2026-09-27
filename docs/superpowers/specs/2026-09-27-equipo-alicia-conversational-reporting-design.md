# Diseño: consultas conversacionales y reporte de trabajo de `@equipo_alicia_bot`

Fecha: 2026-09-27

## Objetivo

Convertir `@equipo_alicia_bot` en la única interfaz operativa para consultar y
recibir el seguimiento de Nora. El bot y los reportes programados deben usar el
mismo motor de datos y las mismas definiciones, de modo que una pregunta manual
y el reporte de la hora entreguen cifras idénticas.

El indicador principal es cuánto tiempo de la jornada tiene actividad
comprobable y cuánto queda sin actividad registrada. Toda cifra se presenta por
BAMBU TECH, GBS, BALIA y TOTAL.

Esta especificación reemplaza las decisiones de formato, frecuencia y cálculo
del diseño del 24 de septiembre cuando exista contradicción. Se mantienen de ese
diseño la identidad exclusiva del bot, los tres clientes, Nora, el horario y la
paleta oficial.

## Límites y seguridad

- Único token permitido: `TELEGRAM_SDR_TOKEN`, verificado con `getMe` como
  `equipo_alicia_bot`.
- Único destinatario autorizado: `TELEGRAM_SDR_CHAT_ID`. El bot interactivo
  no responderá datos operativos a otros chats.
- No se modifican ni reutilizan los bots por cliente ni el bot de Reuniones
  Cliente.
- La SDR operativa es Nora para las tres subcuentas.
- Zona horaria: `America/Santiago`.
- Esta fase no incorpora un modelo generativo ni envía datos a servicios de IA.
  Las preguntas se resuelven con intenciones deterministas y datos auditables.

## Programación

- Se elimina permanentemente `SDR_Telegram_Meeting_Monitor`; no habrá sondeo ni
  mensajes cada cinco minutos.
- El reporte automático se ejecuta una vez por hora, de lunes a viernes, con
  cortes 12:00–20:00 Chile. Cada corte describe la hora que acaba de terminar y
  el acumulado del día.
- A las 20:00 se agrega el cierre diario.
- Las reuniones nuevas se consultan dentro del proceso horario y se muestran
  una sola vez respecto del snapshot anterior.
- El bot interactivo permanece escuchando, pero solo consulta cuando la usuaria
  escribe; no genera notificaciones periódicas.
- El resumen semanal queda fuera de esta fase. Primero se estabilizan el
  reporte horario, el cierre y las consultas bajo demanda.

## Horario oficial

| Hora Chile | Cliente / actividad |
|---|---|
| 11:00–12:00 | BALIA |
| 12:00–13:00 | GBS |
| 13:00–16:00 | BAMBU TECH |
| 16:00–17:00 | Almuerzo excluido |
| 17:00–18:00 | GBS |
| 18:00–20:00 | BAMBU TECH |

La jornada medible tiene ocho horas. El almuerzo y el tiempo fuera de los
bloques no se clasifican como trabajo ni como falta de actividad.

## Fuente compartida de verdad

`sdr_reporting` será la capa compartida para:

1. recolectar llamadas, tareas, email, contactos, funnel y reuniones;
2. normalizar eventos por cliente y contacto;
3. calcular uso del tiempo, cantidades y adherencia;
4. guardar snapshots horarios idempotentes en Supabase;
5. producir documentos de respuesta independientes del canal;
6. renderizar el reporte programado, las respuestas interactivas y los PNG.

`report_sdr_telegram.py` y `report_sdr_bot.py` no tendrán cálculos propios.
Ambos consumirán los mismos servicios. El bot interactivo usará el snapshot
más reciente cuando la pregunta admita datos cacheados y refrescará la fuente
cuando se solicite "ahora", "en vivo" o un intervalo posterior al snapshot.

## Definiciones oficiales

### Tareas

- **Meta operativa:** solo tareas cuyo vencimiento es hoy.
- **Cumplidas de hoy:** tareas de la meta de hoy marcadas como completadas.
- **Atrasadas:** tareas con vencimiento anterior a hoy que siguen abiertas.
- Las atrasadas se muestran por cliente y total, pero nunca se suman al
  denominador de la meta operativa.
- El informe por tipo usa bloques verticales, no tablas `<pre>` estrechas.
- Se eliminan los nombres "arrastre vencido" y "contactos prioritarios".

### Llamadas

- Solo se consideran llamadas salientes.
- **Contestada:** duración de conversación superior a 20 segundos.
- **No contestada/corta:** duración menor o igual a 20 segundos.
- **Reintento:** llamada a un contacto ya llamado el mismo día.
- Se muestran por separado cantidades y minutos:
  - llamadas;
  - contactos únicos;
  - contestadas y minutos hablando;
  - no contestadas/cortas y minutos de teléfono;
  - reintentos y sus minutos;
  - minutos totales al teléfono.
- GHL no ofrece un campo de repique exacto. El tiempo total al teléfono se
  conserva con el cálculo defensivo actual basado en `dateAdded/dateUpdated` y
  se identifica como estimado cuando corresponda. No se inventa precisión.

### Contactos trabajados

Un contacto se considera trabajado cuando tiene al menos uno de estos eventos
manuales observables: llamada, correo manual, respuesta SMTP exitosa, tarea
completada, actualización manual verificable de contacto o movimiento de funnel
con autor manual verificable. Se deduplica por
`(cliente, contact_id, fecha)`.

El total general es la suma de contactos únicos por subcuenta; no se suman
eventos. Las actividades automáticas no convierten un contacto en trabajado.

### Email

El reporte distingue por cliente:

- correos manuales enviados;
- respuestas recibidas de campaña;
- respuestas atendidas exitosamente por Nora;
- respuestas pendientes;
- tiempo medio de respuesta, cuando exista trazabilidad suficiente.

Fuentes y reglas:

- Las respuestas de campaña se leen desde Snov y/o los mensajes recibidos en
  las casillas, deduplicadas por `Message-ID` o una clave estable equivalente.
- Cuando Nora responde mediante el bot, se inserta un evento en
  `sdr_activity_events` solamente después de que SMTP confirme el envío.
- Las respuestas enviadas directamente desde la casilla se detectan leyendo
  la carpeta IMAP de enviados y se enlazan por `In-Reply-To`, `References` o,
  como respaldo, destinatario y asunto normalizado.
- Automatizaciones, workflows y secuencias no cuentan como correo manual.
- BAMBU TECH y GBS tienen casillas configuradas en el código actual. BALIA se
  muestra como `N/D` hasta disponer de una casilla verificable; nunca como cero
  por ausencia de fuente.

### Funnel

El cierre muestra movimientos registrados durante el día por cliente:
Información Adicional, Coordinando Reunión y Reunión Agendada, además del total.

GHL no prueba hoy qué persona hizo todos los movimientos. El texto dirá
"movimientos registrados en la subcuenta", sin atribuirlos inequívocamente a
Nora. El funnel no se incluye en los reportes horarios para reducir ruido.

### Reuniones

Se muestran las reuniones nuevas desde el snapshot anterior y el acumulado del
día, siempre a partir de citas reales de calendario GHL. No existe alerta
separada de cinco minutos.

## Uso del tiempo

Cada minuto transcurrido dentro del horario medible pertenece a exactamente
una categoría:

1. **Teléfono:** intervalo completo observado de una llamada, atribuido a su
   cliente. Tiene prioridad sobre cualquier otro evento coincidente.
2. **Otras gestiones:** minutos sin llamada cubiertos por ventanas de cinco
   minutos a partir de un correo manual, respuesta SMTP exitosa, tarea
   completada o actualización manual verificable de contacto. Un movimiento de
   funnel solo genera tiempo cuando la fuente demuestra que fue manual y
   atribuible; en caso contrario se informa como cantidad en el cierre, pero no
   se usa para acreditar minutos trabajados.
3. **Sin actividad registrada:** minuto sin cobertura de las dos categorías
   anteriores.

Los intervalos se unen antes de sumar; una llamada, tarea y correo simultáneos
no triplican el tiempo. Si ventanas de otros eventos de clientes distintos se
superponen, el minuto se atribuye al evento manual más reciente; un empate se
resuelve con una prioridad fija y documentada para que los totales sean
reproducibles. Los minutos por cliente más `Sin actividad registrada` suman el
total transcurrido medible.

El texto usa "sin actividad registrada", no afirma que Nora no trabajó fuera
de las fuentes observables.

## Adherencia

Por cada bloque se muestra:

- cliente esperado;
- llamadas y minutos de teléfono al cliente correcto;
- llamadas y minutos a cada otro cliente;
- porcentaje de minutos telefónicos dedicados al cliente correcto.

Si no hubo minutos de teléfono, se muestra `Sin actividad telefónica` en vez de
un porcentaje engañoso.

## Formato del reporte horario

Telegram evita las tablas anchas que actualmente desplazan columnas. Usa
secciones verticales y totales explícitos, en este orden:

1. corte horario y acumulado del día;
2. uso del tiempo por hora y total acumulado;
3. llamadas: cantidades por cliente y total;
4. llamadas: minutos por cliente y total;
5. contactos trabajados, correos y tareas por cliente y total;
6. meta de tareas de hoy y atrasadas por cliente y total;
7. adherencia de los bloques transcurridos;
8. correos de campaña recibidos, atendidos y pendientes;
9. reuniones nuevas y acumuladas.

Se eliminan del reporte:

- tablas `<pre>` anchas;
- "arrastre vencido";
- contactos prioritarios;
- cumplimiento de ventana crítica;
- comparación contra ayer;
- funnel horario;
- alertas de tareas repetidas al final.

## Formato del cierre diario

El cierre incluye:

- minutos y porcentaje en Teléfono, Otras gestiones y Sin actividad
  registrada;
- detalle hora por hora;
- cantidades y minutos de llamadas por cliente y total;
- contactos trabajados por cliente y total;
- tareas de hoy y atrasadas por cliente y total;
- email manual y respuestas de campaña;
- movimientos de funnel registrados durante el día;
- reuniones agendadas.

## Gráficos

El reporte horario adjunta un PNG acumulado del día con una barra apilada de
60 minutos por cada hora transcurrida:

- teléfono BAMBU TECH `#22C55E`;
- teléfono GBS `#8B5CF6`;
- teléfono BALIA `#EC4899`;
- otras gestiones en gris;
- sin actividad registrada en rojo.

Cada barra suma 60 minutos, salvo la hora actual incompleta cuando se consulta
manualmente. El cierre reutiliza el gráfico completo y agrega un gráfico de
barras por cliente con llamadas, contactos trabajados y tareas cumplidas.

## Consultas interactivas

El bot incorpora botones: `Tiempo trabajado`, `Llamadas`, `Tareas`, `Correos`,
`Funnel`, `Reuniones` y `Cierre`.

También entiende preguntas naturales dentro del dominio, por ejemplo:

- "¿Cuánto trabajó Nora hoy?"
- "¿Cuántos minutos llamó de 11 a 12?"
- "Dame llamadas y contactos por cliente."
- "¿Cuántas llamadas superaron 20 segundos?"
- "¿Cuántos correos de campaña respondieron y cuántos atendió Nora?"
- "¿Cuántas tareas de hoy completó y cuántas atrasadas hay?"
- "¿A qué cliente llamó durante el bloque de GBS?"
- "¿Cuántos contactos pasaron a Información Adicional?"
- "Mándame el gráfico de hoy."

El enrutador extrae fecha (`hoy`, `ayer`, fecha explícita), intervalo horario,
cliente y métrica. Si faltan datos esenciales hace una pregunta corta. Si la
consulta queda fuera del dominio, muestra el menú disponible; no improvisa.

## Persistencia y deduplicación

Se reutilizan `sdr_activity_events`, `sdr_daily_baselines`,
`sdr_hourly_snapshots` y `sdr_alert_state`.

- Los eventos usan ids de fuente y upsert idempotente.
- Los snapshots guardan la versión del esquema de cálculo.
- Los documentos horarios se recalculan desde eventos canónicos, no sumando
  snapshots entre sí.
- Un correo presente en Snov, IMAP y GHL se cuenta una vez.
- Un reintento de envío SMTP no crea dos respuestas exitosas.

## Manejo de errores

- Un cliente sin fuente se muestra `N/D`; nunca se reemplaza por cero.
- Un fallo parcial no borra los otros clientes.
- Las respuestas interactivas indican la hora del snapshot o de la consulta en
  vivo.
- El bot no expone excepciones ni secretos en Telegram.
- Los tiempos estimados se etiquetan; los exactos y estimados no se mezclan sin
  explicación.
- Todo contenido dinámico se escapa antes de usar HTML de Telegram.

## Pruebas y activación

- Pruebas unitarias para intervalos, unión sin duplicación, frontera de 20
  segundos, tareas de hoy versus atrasadas, deduplicación de email, intenciones
  y autorización de chat.
- Pruebas de render para las tres cuentas y TOTAL sin tablas desplazadas.
- Prueba de integración en seco con datos reales del día.
- Antes de activar, se muestra en esta conversación el reporte real y el PNG.
- Solo después de aprobación se activa el formato en Telegram.

## Criterios de aceptación

- El bot y el reporte programado entregan las mismas cifras.
- Siempre aparecen BAMBU TECH, GBS, BALIA y TOTAL, o `N/D` con explicación.
- Cada hora completa suma 60 minutos y cada jornada completa medible suma 480.
- Llamadas muestran cantidades y minutos separados.
- Contestada significa estrictamente más de 20 segundos.
- Meta operativa contiene solo tareas que vencen hoy; atrasadas van aparte.
- Email diferencia manual, respuesta de campaña, atendida y pendiente.
- Funnel aparece solo en el cierre y no atribuye autor sin evidencia.
- Los gráficos usan los colores oficiales y reflejan los mismos totales del
  texto.
- No existe automatización de cinco minutos ni alertas inmediatas de
  inactividad.
- Solo el chat configurado puede consultar datos.
