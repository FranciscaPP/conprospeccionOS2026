# Equipo Alicia: automatización cloud sin dependencia del PC

Fecha: 2026-10-05

Estado: diseño aprobado por Francisca.

## Objetivo

Mantener `@equipo_alicia_bot` operativo cuando el computador local esté
apagado, bloqueado o sin conexión. La solución debe:

- enviar los reportes automáticos de Nora entre 10:00 y 22:00 Chile, de lunes
  a viernes;
- responder las consultas escritas al bot durante las 24 horas, todos los días;
- conservar las métricas, imágenes y reglas del reporte ya aprobadas;
- usar exclusivamente `TELEGRAM_SDR_TOKEN` y `TELEGRAM_SDR_CHAT_ID`;
- evitar reportes y respuestas duplicadas;
- no depender de un servidor contratado.

## Alcance

Este cambio mueve a la nube dos procesos que actualmente dependen de Windows:

1. generación y envío del reporte tabular horario;
2. recepción y respuesta de consultas dirigidas al bot.

No modifica:

- los bots de clientes;
- el bot separado de reuniones;
- las fórmulas de tareas, llamadas, correos, WhatsApp y tiempo;
- el formato de dos imágenes PNG;
- las fuentes GHL ya utilizadas por el reporte.

## Arquitectura elegida

La solución combina GitHub Actions y Supabase:

```text
GitHub Actions programado
        |
        v
report_sdr_telegram.py --operational --cloud-scheduled --send
        |
        +--> GHL / Supabase
        |
        +--> @equipo_alicia_bot --> chat privado de Francisca

Telegram update
        |
        v
Supabase Edge Function (webhook)
        |
        +--> valida chat y update_id
        +--> guarda consulta en Supabase
        +--> activa workflow_dispatch en GitHub
                              |
                              v
                    consulta GHL y responde Telegram
```

GitHub ejecuta el código Python existente. Supabase aporta un endpoint público
para Telegram y una cola persistente mínima para las consultas.

## Reporte horario cloud

### Programación

Un workflow independiente se dispara cada 15 minutos. La frecuencia corta no
genera cuatro reportes por hora: un gate calcula la hora local con
`America/Santiago` y solo permite un envío cuando:

- es lunes, martes, miércoles, jueves o viernes;
- la hora Chile está entre 10:00 y 22:00, ambas incluidas;
- todavía no existe un envío exitoso para esa fecha y hora Chile.

Habrá como máximo 13 cortes diarios: 10:00, 11:00, 12:00, 13:00, 14:00,
15:00, 16:00, 17:00, 18:00, 19:00, 20:00, 21:00 y 22:00.

El gate tolera atrasos del cron de GitHub. Si el tick exacto de las 15:00 no
ocurre, el siguiente tick dentro de esa hora puede generar el corte faltante.
No se promete puntualidad al minuto exacto porque GitHub puede retrasar
ejecuciones programadas.

### Idempotencia

Supabase mantiene una tabla `sdr_report_deliveries` con una restricción única
sobre `delivery_key`. La clave usa:

```text
hourly:YYYY-MM-DD:HH:America/Santiago
```

Estados:

- `processing`: una ejecución reclamó el corte;
- `sent`: Telegram confirmó las dos imágenes;
- `failed`: la ejecución terminó con error verificable.

La fila también conserva `part1_sent_at` y `part2_sent_at`. Así un reintento
después de una falla parcial no vuelve a enviar una imagen ya confirmada.

Una ejecución reclama la clave antes de consultar todas las fuentes. Otra
ejecución con la misma clave termina sin enviar. Un registro `failed` puede ser
reclamado nuevamente por un tick posterior mediante un intento explícito y
acotado; nunca se reenvía un registro `sent`. Un estado `processing` con más de
30 minutos se considera abandonado y puede recuperarse una sola vez.

### Contenido

El workflow reutiliza el documento producido por `build_live_report()` y
`render_tabular_report()`. Envía exactamente:

1. `Reporte Nora · 1 de 2`;
2. `Reporte Nora · 2 de 2`.

Se conservan las definiciones oficiales:

- `Total = atrasadas base + tareas de hoy`;
- `Avance = completadas del Total`;
- `Pendiente = Total - Avance`;
- llamadas principales dentro de jornada oficial;
- llamadas antes de las 11:00, almuerzo y después de las 20:00 separadas;
- cinco minutos por conversación de correo o WhatsApp respondida;
- `N/D` cuando una fuente no sea verificable.

El horario de envío 10:00–22:00 no cambia la jornada de medición
11:00–20:00. El corte de las 10:00 puede mostrar preparación o actividad fuera
de horario; los cortes de 21:00 y 22:00 muestran el cierre y cualquier trabajo
posterior separado.

## Consultas al bot 24/7

### Entrada por webhook

Telegram se configura con `setWebhook` hacia una nueva Supabase Edge Function.
Telegram enviará un encabezado secreto configurado al registrar el webhook. La
función acepta únicamente:

- método `POST`;
- encabezado secreto válido;
- mensajes de texto;
- `chat.id` exactamente igual a `TELEGRAM_SDR_CHAT_ID`;
- `update_id` no procesado anteriormente.

Todo otro chat se ignora sin activar GitHub ni revelar información.

### Cola de consultas

La función inserta la consulta en `sdr_bot_queries` con `update_id` único y los
campos mínimos:

- `update_id`;
- `chat_id`;
- `text`;
- `status` (`queued`, `processing`, `answered`, `failed`);
- marcas de tiempo;
- error técnico resumido, si corresponde.

El texto no se pasa como argumento visible al workflow. La Edge Function activa
`workflow_dispatch` enviando solamente el `update_id`. El workflow consulta la
fila mediante la service role de Supabase, utiliza el mismo parser de
intenciones y las mismas métricas del reporte, responde por Telegram y marca la
fila como `answered`.

Un segundo intento con el mismo `update_id` no genera otra respuesta. Una fila
`failed` puede reintentarse una vez desde GitHub; después queda visible como
fallida para revisión.

### Latencia

La respuesta no es instantánea. El objetivo operativo es responder normalmente
en uno a tres minutos, sujeto a la cola de GitHub Actions y a las APIs de GHL.
El webhook devuelve HTTP 200 rápidamente para que Telegram no reenvíe el mismo
update por timeout.

## Workflows de GitHub

Se crea un workflow dedicado, separado de `sync-commercial-data.yml`, para que
un fallo del reporte no afecte la sincronización comercial y viceversa.

El workflow admite dos entradas:

- ejecución programada: evalúa y envía el corte horario pendiente;
- `workflow_dispatch` con `update_id`: responde una consulta de Telegram.

Se utiliza `concurrency` para impedir dos ejecuciones simultáneas del mismo modo
y se añade un timeout finito. Los logs nunca imprimen tokens, contraseñas,
encabezados de autorización ni el texto completo de una consulta.

## Secretos

### GitHub Actions

El repositorio necesita estos secretos:

- `SUPABASE_URL`;
- `SUPABASE_SECRET_KEY`;
- `GHL_TOKEN_BAMBUTECH`;
- `GHL_LOCATION_BAMBUTECH`;
- `GHL_TOKEN_GBS_LOGISTICS`;
- `GHL_LOCATION_GBS`;
- `GHL_TOKEN_BALIA`;
- `GHL_LOCATION_BALIA`;
- `TELEGRAM_SDR_TOKEN`;
- `TELEGRAM_SDR_CHAT_ID`.

El workflow valida su presencia y falla de forma visible si falta cualquiera.
No se copian valores a archivos versionados ni a mensajes de chat.

### Supabase Edge Function

La función necesita:

- `TELEGRAM_SDR_CHAT_ID`;
- `TELEGRAM_WEBHOOK_SECRET`;
- `GITHUB_REPOSITORY`;
- `GITHUB_WORKFLOW_TOKEN`, token de alcance mínimo que permita activar el
  workflow del repositorio.

La credencial de GitHub vive solo como secreto de Supabase. No se almacena en
tablas ni en el repositorio.

## Fallos y observabilidad

- Si una fuente de un cliente no está disponible, el reporte conserva `N/D` y
  registra la alerta existente.
- Si no se pueden construir las dos imágenes, el corte queda `failed` y no se
  envía un reporte parcial.
- Si Telegram confirma solo la primera imagen, el corte queda `failed`; el
  reintento reutiliza la misma clave y debe evitar duplicar la primera imagen
  mediante el estado de partes enviadas.
- Si GitHub no responde a una consulta, la fila permanece `queued` o `failed` y
  puede identificarse en Supabase.
- Los workflows conservan resultado, duración y logs técnicos en GitHub.
- Una consulta fallida recibe una respuesta breve y segura en Telegram cuando
  el canal de salida siga disponible.

## Migración desde Windows

La transición evita tanto cortes como duplicados:

1. crear tablas y Edge Function;
2. configurar secretos de GitHub y Supabase;
3. ejecutar pruebas automatizadas;
4. ejecutar manualmente el workflow cloud sin enviar;
5. verificar `getMe` como `@equipo_alicia_bot` y el único chat autorizado;
6. enviar un reporte cloud real y verificar las dos imágenes;
7. registrar el webhook y hacer una pregunta real;
8. verificar la respuesta y la idempotencia;
9. desactivar `SDR_Telegram_Hourly` y `SDR_Telegram_Bot` en Windows;
10. comprobar que el siguiente reporte cloud llega sin depender del PC.

Las tareas locales no se eliminan. Quedan desactivadas y disponibles como
respaldo manual, pero nunca activas al mismo tiempo que la nube.

## Pruebas de aceptación

- Un corte válido envía exactamente dos imágenes al chat autorizado.
- Dos ejecuciones para la misma hora producen un solo envío.
- Un cron retrasado todavía puede cubrir la hora pendiente.
- No se envían reportes fuera de lunes a viernes, 10:00–22:59 Chile.
- Los cambios de UTC por horario de verano no alteran la ventana Chile.
- Un chat no autorizado no crea una consulta ni activa GitHub.
- Dos entregas del mismo `update_id` producen una sola respuesta.
- El workflow de consulta no imprime el texto completo ni secretos.
- La consulta usa las mismas métricas que el reporte horario.
- La caída de una fuente no produce cifras inventadas.
- Las tareas de Windows se desactivan solo después de verificar reporte y
  consulta cloud reales.

## Limitaciones aceptadas

- GitHub Actions puede retrasar ejecuciones programadas; la revisión cada 15
  minutos reduce el impacto, pero no garantiza envío al minuto exacto.
- Las consultas pueden tardar uno a tres minutos.
- La disponibilidad depende de GitHub, Supabase, Telegram y GHL.
- La solución no incorpora un servidor permanente ni una nueva plataforma de
  pago.
