# Diseño: respuestas de Balia en la nube

Fecha: 2026-10-05

## Objetivo

Detectar y enviar al bot de Telegram las respuestas nuevas de las campañas de
Balia aunque el computador local esté apagado, bloqueado o sin sesión activa.

## Alcance

- Ejecutar el sincronizador de respuestas de Balia en GitHub Actions.
- Ejecutarlo cada hora entre las 08:00 y las 22:00 de `America/Santiago`.
- Leer las campañas asociadas a `cliente_slug = 'balia'` en
  `snov_campaign_map`.
- Consultar las respuestas en Snov, reconciliarlas con el contacto en GHL,
  registrar las tarjetas en Supabase y enviar a `@balia_campaing_bot` solo las
  respuestas que todavía no tengan tarjeta registrada.
- Mantener intactas las 36 respuestas ya registradas y no reenviarlas.

## Fuera de alcance

- Mantener activos con el PC apagado los botones interactivos de Telegram para
  crear tareas, cambiar estatus, responder correos o agendar reuniones.
- Reescribir el sincronizador como Supabase Edge Function.
- Contratar o configurar un servidor permanente.
- Cambiar la sincronización de reuniones, contactos o pipelines existente.

## Arquitectura

Se ampliará `.github/workflows/sync-commercial-data.yml` con un job independiente
para respuestas de Balia. El job no dependerá del gate de 4,5 horas usado por la
sincronización general: el workflow se dispara cada hora y el job decidirá si la
hora actual en Chile está dentro de la ventana inclusiva 08:00–22:00.

El job ejecutará:

```text
python sync/scripts/sync_snov_replies_to_ghl.py --client balia
```

Las credenciales se leerán exclusivamente desde GitHub Actions Secrets. No se
copiarán tokens al workflow ni al repositorio.

## Secretos requeridos

- `SUPABASE_URL`
- `SUPABASE_SECRET_KEY`
- `GHL_AGENCY_TOKEN`
- `GHL_TOKEN_BALIA`
- `SNOV_CLIENT_ID`
- `SNOV_CLIENT_SECRET`
- `TELEGRAM_BOT_BALIA_TOKEN`
- `TELEGRAM_BOT_BALIA_CHAT_IDS`

El job validará la presencia de todos los secretos antes de ejecutar. Si falta
uno, fallará de forma visible en vez de terminar en verde sin sincronizar.

## Flujo de datos

1. GitHub Actions despierta cada hora.
2. Convierte la hora actual a `America/Santiago`.
3. Si está fuera de 08:00–22:00, omite el job de respuestas.
4. Si está dentro de la ventana, instala las dependencias de `sync/requirements.txt`.
5. Valida los ocho secretos requeridos.
6. Ejecuta el sincronizador limitado a Balia.
7. El sincronizador consulta las seis campañas mapeadas, compara contra GHL y
   revisa `telegram_ghl_cards` para deduplicar.
8. Solo las respuestas sin tarjeta previa se envían a Telegram y se registran
   en Supabase.
9. La corrida deja evidencia en `sync_runs`.

## Errores y observabilidad

- Una credencial faltante produce un error visible de GitHub Actions.
- Un error HTTP de Snov, GHL, Supabase o Telegram hace fallar el job; no se
  convertirá silenciosamente en advertencia.
- `sync_runs` conservará el estado, estadísticas y errores del sincronizador.
- La deduplicación por cliente y correo evita reenviar respuestas históricas en
  ejecuciones posteriores.

## Verificación

1. Validar sintaxis del workflow.
2. Ejecutar las pruebas del sincronizador y las tarjetas de Telegram.
3. Publicar el workflow y dispararlo manualmente una vez.
4. Confirmar que el run termina correctamente con el PC local apagado o sin
   participar en la ejecución.
5. Reconciliar el total de Snov con `telegram_ghl_cards` para Balia.
6. Ejecutar una segunda vez y confirmar que el conteo no aumenta sin respuestas
   nuevas.

## Criterios de aceptación

- El job se ejecuta cada hora dentro de 08:00–22:00, hora de Chile.
- No depende del Programador de tareas de Windows.
- Las 36 respuestas ya registradas no se duplican.
- Una respuesta nueva de cualquiera de las campañas mapeadas de Balia genera
  una tarjeta y un registro en Supabase.
- Los secretos no aparecen en archivos, logs ni mensajes del repositorio.
