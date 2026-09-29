# Equipo Alicia: consultas específicas, alertas de reuniones y envíos únicos

Fecha: 2026-09-29

## Objetivo

Ampliar exclusivamente `@equipo_alicia_bot` para que Francisca pueda hacer
consultas operativas específicas en vivo, recibir alertas de reuniones nuevas
de BAMBU TECH, GBS y BALIA, y no recibir reportes horarios duplicados.

## Restricciones

- Único bot: token `TELEGRAM_SDR_TOKEN`, validado como
  `@equipo_alicia_bot` mediante `getMe`.
- Único destinatario: `TELEGRAM_SDR_CHAT_ID`, actualmente el chat privado de
  Francisca.
- No modificar ni reutilizar bots de clientes ni el bot de reuniones separado.
- El monitor anterior de cinco minutos continúa eliminado.
- Cuando una fuente no permita verificar un dato se responde `N/D`; no se
  inventan asuntos, contactos, enlaces, actividad ni autoría.

## 1. Consultas específicas en vivo

El controlador responderá primero con un acuse breve, por ejemplo
`Consultando correos de BAMBU TECH…`. Después ejecutará únicamente la consulta
necesaria para la intención y el cliente solicitados.

Una pregunta de correos de BAMBU TECH no puede construir el reporte general ni
consultar tareas, llamadas, calendarios, GBS o BALIA. Esto evita que un fallo o
un límite de una fuente no relacionada bloquee la respuesta. El incidente
observado el 29 de septiembre se produjo porque la consulta de correo llegó al
calendario de otro cliente y GHL respondió HTTP 429.

Para `¿cuáles correos están pendientes de responder?`, la respuesta incluirá,
por cada conversación verificable:

- contacto;
- dirección de correo;
- asunto;
- fecha y hora;
- resumen breve del último correo entrante;
- enlace a GHL solo cuando pueda construirse y verificarse.

Un correo está pendiente cuando existe un mensaje entrante y no existe un
mensaje manual posterior en la misma conversación. `workflow` no cuenta como
respuesta manual. El bot admite filtros por BAMBU TECH, GBS o BALIA y no mezcla
clientes.

Si la consulta en vivo falla, el bot informa la fuente y el tipo de error en un
mensaje legible. Una caché breve del último resultado correcto puede mostrarse
como respaldo, identificando claramente su hora; nunca se presenta como dato en
vivo.

## 2. Alertas de reuniones nuevas cada tres horas

Una tarea de Windows independiente, `SDR_Meeting_Alert_3h`, se ejecutará cada
tres horas, las 24 horas del día. Cada ejecución revisará silenciosamente los
calendarios GHL de BAMBU TECH, GBS y BALIA.

La primera ejecución registra las reuniones existentes sin notificarlas. En
ejecuciones posteriores, una cita activa cuyo identificador no esté registrado
se considera nueva. Se excluyen estados cancelados, `canceled`, `cancelled` y
`noshow`.

Cada alerta se envía una sola vez e incluye:

- cliente;
- contacto;
- fecha y hora en Chile;
- fecha y hora en Perú;
- teléfono y correo, si GHL los entrega;
- SDR Nora.

Si no existen reuniones nuevas, la tarea no envía ningún mensaje. La
deduplicación se persiste en `sdr_activity_events` por
`source + source_id + cliente_slug`. Una reunión se marca como notificada solo
después de que Telegram confirme el envío; si falla antes, se reintenta en la
siguiente ejecución.

## 3. Reportes horarios sin duplicados

Se mantiene una sola tarea horaria: `SDR_Telegram_Hourly`. El duplicado de las
15:00 del 29 de septiembre fue la suma de esa ejecución y un envío manual de
prueba realizado a la misma hora; no había dos tareas horarias.

Cada corte horario tendrá una clave persistente `YYYY-MM-DDTHH`. Antes de
enviar, el proceso comprobará si el corte ya fue confirmado para el chat
autorizado. Después de enviar todas las partes registra los identificadores de
mensaje de Telegram. Una repetición manual o programada del mismo corte
responderá `reporte ya enviado` en el log y no volverá a Telegram.

Los modos de vista previa y pruebas nunca registran un envío ni bloquean el
reporte programado.

## Componentes

- `sdr_reporting/query.py`: consultas específicas por dominio y cliente.
- `sdr_reporting/sources.py`: detalle de correos y clasificación pendiente.
- `report_sdr_bot.py`: acuse inmediato, autorización y respuesta final.
- `sdr_reporting/meeting_alerts.py`: detección, semilla y notificación de citas.
- `sdr_reporting/storage.py`: deduplicación de reuniones y recibos horarios.
- `sdr_reporting/cli.py`: comandos explícitos de alerta, semilla y envío.
- `run_sdr_meeting_alerts.bat`: entrada de la tarea cada tres horas.

## Errores y observabilidad

- Cada ejecución registra inicio, cliente consultado, cantidad encontrada,
  cantidad enviada y error resumido, sin secretos ni cuerpos completos.
- Un error de un cliente no impide revisar los otros dos para alertas.
- HTTP 429 aplica espera y reintento acotado; nunca produce un bucle rápido.
- El bot conversacional siempre entrega acuse y éxito o error final.

## Pruebas y aceptación

- Una pregunta de correo de BAMBU TECH no invoca calendarios ni otros clientes.
- El bot devuelve detalle de pendientes y excluye respuestas `workflow`.
- Un fallo HTTP 429 genera respuesta de error y no deja la conversación muda.
- La semilla de reuniones no alerta citas existentes.
- Una cita nueva produce exactamente una alerta y no reaparece en la siguiente
  ejecución.
- Las alertas incluyen hora Chile y Perú.
- Dos intentos del mismo corte horario producen un solo grupo de mensajes.
- `getMe` confirma `@equipo_alicia_bot` y todos los envíos usan únicamente el
  chat privado configurado.

