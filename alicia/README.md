# Alicia · respuestas de campañas Snov.io desde Telegram

Servicio backend (no toca el dashboard Streamlit) que detecta respuestas reales
a campañas de Snov.io en las cuentas de correo, avisa por Telegram en **una sola
notificación agrupada por ejecución**, y permite responder en el mismo hilo tras
tu aprobación. Prioriza **cero consumo de créditos de IA** en la operación normal.

## Principio de diseño: la detección NO usa IA

Toda la detección, lectura de metadatos, filtrado de mensajes nuevos e
identificación de respuestas / rebotes / fuera de oficina / spam / duplicados es
**100% determinística** (código + Gmail API). Ningún modelo participa en esto.

La IA (Anthropic) solo se usa **bajo petición explícita** desde Telegram y pasa
siempre por el único gateway `alicia/ai.py`. El pipeline de detección ni siquiera
importa ese módulo.

## Control de costos de IA (obligatorio)

| Pregunta | Respuesta |
|---|---|
| **¿Cuándo se ejecuta?** | Solo si tú lo pides: `resumen`, `clasifica`, o redactar (`respóndele…`). Nunca automáticamente, nunca una vez por correo, nunca en bucle. |
| **¿Qué se envía al modelo?** | Asunto + último mensaje del prospecto + cliente/campaña. Para borrador, además tu instrucción. Nunca bandejas completas, secretos ni tokens. |
| **¿Qué modelo?** | `ALICIA_AI_MODEL` (por defecto `claude-haiku-4-5-20251001`, el más barato), con `max_tokens` acotado por tarea. |
| **¿Cómo se desactiva del todo?** | `ALICIA_AI_ENABLED=false` (valor por defecto). Cada función lanza `AIDisabledError` sin tocar la red. Sin `ANTHROPIC_API_KEY` tampoco corre. |

Si dictas el texto exacto (`Envía exactamente: …` o entre comillas), el sistema lo
envía **sin llamar a ningún modelo** (`alicia/drafting.py::literal_reply`).

## Interruptores de seguridad

- `ALICIA_ENABLED=false` — el servicio no corre (para el piloto antes de tener secretos).
- `ALICIA_DRY_RUN=true` — no envía correos reales, no marca leído, no escribe en GHL.
- `ALICIA_AI_ENABLED=false` — apaga toda la IA.

## Frecuencia

No es tiempo real. El poller se auto-limita a `ALICIA_RUN_HOURS` (por defecto
`8,20`, dos veces al día) en `ALICIA_TIMEZONE`. El cron del workflow puede
dispararse cada hora sin costo: solo corre de verdad en esas horas. `--force`
ignora la ventana para pruebas.

## Escalabilidad y piloto

Las cuentas se declaran como configuración, sin código por cuenta:

- **Piloto (una cuenta):** `ALICIA_ACCOUNTS_JSON` con una entrada `enabled:true`.
- **Producción (25+ cuentas):** tabla `public.alicia_accounts`. Habilitar otra
  cuenta = una fila `enabled=true` + su refresh token en Secrets bajo el nombre
  de `token_env`. El pipeline itera uniformemente sobre las habilitadas.

Los refresh tokens **nunca** van al repo ni a la tabla: solo a Secrets. La tabla
guarda el *nombre* del secreto (`token_env`), no su valor.

## Estructura

```
alicia/
  settings.py       Config e interruptores (dry-run, IA, horario, cuentas)
  accounts.py       Registro de cuentas (Supabase o JSON) + identificador interno
  gmail_client.py   Gmail REST: listar/leer metadatos, marcar leído, responder en hilo
  reply_filters.py  Clasificación determinística (rebote/OOO/auto/spam) — SIN IA
  snov_match.py     Correlación remitente ↔ campaña Snov — SIN IA
  notifications.py  Notificación agrupada por ejecución — SIN IA
  drafting.py       Instrucciones: no responder / literal (sin IA) / borrador (IA bajo petición)
  ai.py             Gateway ÚNICO de IA, apagado por defecto
  store.py          Supabase REST + idempotencia/estado
  telegram_io.py    Envío a Telegram (salida)
  pipeline.py       Orquestación determinística de una corrida
  __main__.py       Entrypoint con auto-límite de horario
```

## Ejecutar

```bash
pip install -r alicia/requirements.txt
# Piloto en dry-run, forzando la ventana horaria:
ALICIA_ENABLED=true ALICIA_DRY_RUN=true python -m alicia --force
```

## Estado de implementación

- [x] **Etapa 0** — andamiaje, config, migración `025`, filtros y pipeline determinístico, tests (dry-run, sin IA, sin envíos).
- [ ] Etapa 1-2 — cableado real de Gmail (piloto una cuenta) + alerta a Telegram.
- [ ] Etapa 3 — webhook de Telegram (instrucciones/aprobación).
- [ ] Etapa 4 — envío real en hilo (con dry-run por defecto).
- [ ] Etapa 5 — acciones GHL post-envío (contacto, nota, etapa).
- [ ] Etapa 6 — automatización (workflow + webhook) y runbook operativo.

## Tests

```bash
python -m pytest tests/test_alicia_filters.py tests/test_alicia_pipeline.py -q
```
