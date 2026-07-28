# Alicia · gestión de respuestas de campañas Snov.io desde Telegram

Servicio backend (no toca el dashboard Streamlit) que **detecta respuestas reales
de prospectos** en las casillas de correo de campañas Snov, avisa por **Telegram**
en una sola notificación agrupada, y permite **responder desde Telegram con tu
aprobación**, enviando el correo en el mismo hilo y actualizando **GoHighLevel**.

> **Regla de costos de IA (obligatoria):** la detección/filtrado es 100%
> determinística (código + Gmail API), SIN IA. La IA (Anthropic) está **apagada
> por defecto** y solo se usaría bajo petición explícita para redactar/resumir.
> Si dictas el texto, se envía sin llamar a ningún modelo. Ver `alicia/ai.py`.

---

## 1. Estado actual (2026-07-28)

**Funcionando en producción:**
- [x] Detección automática **2×/día** (12:00 y 17:00 America/Santiago) de las 3
      casillas GBS, vía Gmail API. Filtra rebotes / fuera de oficina / auto /
      spam / remitentes de sistema. Idempotente por hilo.
- [x] **Alertas a Telegram** con tarjeta por respuesta: cliente, campaña, cuenta
      receptora, prospecto, empresa, asunto, último mensaje, **fecha de respuesta**
      e identificador interno (`AL-XXXXXXXX`).
- [x] **Responder desde Telegram** con aprobación: respondes a la tarjeta → Alicia
      muestra el borrador → escribes `aprobar` → (en **modo prueba**) muestra el
      correo que se enviaría. `no responder` / `cancelar` soportados.
- [x] **GoHighLevel conectado** (token Private Integration validado: lectura y
      escritura de contactos, pipelines, calendario, campos personalizados).

- [x] **Datos del contacto de GHL en la tarjeta** (correo, tel, cargo, empresa,
      web, tamaño, LinkedIn persona/empresa, industria). Nombre del cliente
      ("GBS") en negrita arriba.
- [x] **Al aprobar**: crear/actualizar contacto en GHL + guardar el campo
      *OBJETIVO BREVE DE LA REUNIÓN* (flujo con pregunta de objetivo).
- [x] **Mover de etapa a pedido** (`mover a [etapa]`, 16 etapas mapeadas).
- [x] **Proponer horarios del calendario** ("Sam Miller - Olivo") cuando el
      mensaje del prospecto sugiere reunión.

**Pendiente:**
- [ ] Activar el **envío real** de correos y acciones GHL (hoy `ALICIA_DRY_RUN=true`).

---

## 2. Arquitectura (qué corre y dónde)

Alicia tiene dos "cuerpos": el **runtime en Supabase** (lo que corre solo) y un
**módulo Python de referencia** con la misma lógica de detección y sus tests.

### 2.1 Runtime en producción (Supabase)
- **Edge Function `alicia-poll`** (`supabase/functions/alicia-poll/index.ts`, Deno):
  el poller. Lee Gmail, clasifica (determinístico), enriquece con Snov, arma las
  tarjetas y las manda a Telegram. Idempotente a nivel de hilo (solo hilos nuevos
  o con respuesta más nueva que la última avisada → también capta la continuación
  de una conversación). Protegida por cabecera `x-alicia-secret`.
- **Edge Function `telegram-alicia`** (`supabase/functions/telegram-alicia/index.ts`,
  Deno): el **webhook** de Telegram. Maneja el flujo responder → borrador →
  aprobar → enviar en hilo. Protegida por `x-telegram-bot-api-secret-token`.
- **pg_cron** (en la base): dos jobs que llaman a `alicia-poll` vía `net.http_post`:
  - `alicia-poll-12` → `0 16 * * *` UTC (12:00 Chile)
  - `alicia-poll-17` → `0 21 * * *` UTC (17:00 Chile)
  - *(Nota DST: horas fijadas para UTC-4; si Chile cambia a UTC-3, correrán a las
    13:00/18:00 locales — ajustar los cron si se requiere exactitud.)*
- **Webhook de Telegram**: apunta a la URL de `telegram-alicia`.

### 2.2 Módulo Python de referencia (`alicia/`)
Primera implementación + **tests determinísticos** (`tests/test_alicia_*.py`).
Contiene la misma lógica de filtros/correlación/notificación. Puede correr como
poller alternativo por GitHub Actions (`.github/workflows/alicia-gmail-poll.yml`,
deshabilitado por `vars.ALICIA_ENABLED`). Hoy el poller vivo es la Edge Function;
el módulo Python es la referencia validada por tests.

```
alicia/
  settings.py       Config e interruptores (dry-run, IA, horario, cuentas)
  accounts.py       Registro de cuentas + identificador interno (AL-XXXX)
  gmail_client.py   Gmail REST: listar/leer, marcar leído, responder en hilo
  reply_filters.py  Clasificación determinística (rebote/OOO/auto/spam/sistema/Re:)
  snov_match.py     Correlación remitente ↔ campaña Snov (enriquecimiento)
  notifications.py  Notificación agrupada (con fecha de respuesta)
  drafting.py       no responder / literal (sin IA) / borrador (IA bajo petición)
  ai.py             Gateway ÚNICO de IA, apagado por defecto
  store.py          Supabase REST + idempotencia/estado
  telegram_io.py    Envío a Telegram
  pipeline.py       Orquestación determinística
  __main__.py       Entrypoint (auto-límite de horario)
  tools/get_gmail_refresh_token.py   Helper OAuth (generar refresh token)
  SETUP_GMAIL_WORKSPACE.md           Guía de alta de casillas Gmail
```

### 2.3 Tablas Supabase (migración `sync/supabase/migrations/025_*` + alters)
- `alicia_accounts` — casillas monitoreadas (email, token_env, cliente, enabled).
- `alicia_email_threads` — estado por hilo (prospecto, empresa, asunto, último
  mensaje, `internal_ref`, `estado`, `pending_draft`, `last_gmail_message_id`,
  `ghl_contact_id`…). Es la memoria de la conversación.
- `alicia_processed_messages` — idempotencia por mensaje de Gmail.
- `alicia_telegram_links` — relación `telegram_message_id` ↔ hilo ↔ cuenta.
- `alicia_actions_log` — auditoría (envíos, acciones GHL, errores).
- `alicia_runs` — registro de cada corrida del poller.
- `alicia_secrets` — **almacén de secretos** (solo service_role; RLS activo).

### 2.4 Secretos (`alicia_secrets`, NOMBRES; nunca en el repo)
`GMAIL_OAUTH_CLIENT_ID`, `GMAIL_OAUTH_CLIENT_SECRET`,
`GMAIL_REFRESH_TOKEN_GBS01/02/03`, `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID`,
`TELEGRAM_WEBHOOK_SECRET`, `ALICIA_POLL_SECRET`, `ALICIA_DRY_RUN`,
`ALICIA_LOOKBACK_HOURS`, `GHL_TOKEN_GBS`, `GHL_LOCATION_GBS`, `GHL_PIPELINE_GBS`,
`GHL_STAGE_RESPONDE`, `GHL_CALENDAR_GBS`, `GHL_FIELD_OBJETIVO`.

---

## 3. Flujo de datos

```
Gmail (3 casillas GBS)
   │  alicia-poll (2×/día, determinístico, sin IA)
   ▼
Clasificación (rebote/OOO/auto/spam/sistema/Re:) + correlación Snov
   │  solo respuestas humanas reales
   ▼
alicia_email_threads (upsert)  →  Telegram (tarjeta por hilo)
   │  respondes a la tarjeta con el texto
   ▼
telegram-alicia (webhook) → borrador → "aprobar"
   │  (modo prueba: muestra; real: envía)
   ▼
Gmail send (mismo hilo, misma casilla)  →  GoHighLevel (contacto, campo, etapa)
   │
   ▼
Confirmación en Telegram
```

---

## 4. Cuentas del piloto (GBS)
| account_id | casilla | cliente |
|---|---|---|
| gbs01 | sam.miller@gbs-logistics.cl | gbs |
| gbs02 | sammiller@gbs-logistics.cl | gbs |
| gbs03 | sam@gbs-logistics.cl | gbs |

Escala a 25+ casillas: agregar filas en `alicia_accounts` + su refresh token en
`alicia_secrets` (sin código nuevo). Auth por OAuth refresh token por casilla
(la política de la org bloquea claves de service account).

---

## 5. GoHighLevel (subcuenta GBS)
- **locationId:** `u9b8KkJXhM8lqJfzxa7G`
- **Pipeline "Sales":** `YAyXeeCL1r07NlmvghhZ`
  - Etapa "RESPONDE WHATSAPP / CORREO": `deb37e6a-d9e0-4aa4-b014-6710508f26bb`
    (las 16 etapas están en GHL; el movimiento de etapa es **a pedido**, no automático).
- **Calendario** (booking `sam-miller-fp`) = "Sam Miller - Olivo": `qi4ODVbGG8DefNBM4OvH`
- **Campo a completar:** *OBJETIVO BREVE DE LA REUNIÓN*
  (`contact.informacin_de_preparacin_para_la_reunin`, id `mwCPOKdikR3VfS7Xf9bm`)
- Acceso: token Private Integration en `alicia_secrets.GHL_TOKEN_GBS`. También hay
  un **MCP de GHL** configurado en `.mcp.json` (para asistentes en sesión; Alicia
  usa la API directa, no el MCP).
- Contexto de GBS (para IA futura): `docs/gbs/`.

---

## 6. Pendiente de construir (detalle)
1. **Datos del contacto en la tarjeta**: al detectar una respuesta, buscar el
   contacto en GHL por email y mostrar correo, teléfono, cargo, empresa, web,
   Tamaño Empresa, LinkedIn Personal/Empresa, Industria.
2. **Flujo con objetivo**: tras el borrador, pedir el *objetivo breve de la
   reunión*; al aprobar → enviar + crear/actualizar contacto + guardar ese campo.
3. **Mover de etapa a pedido**: comando `mover a [etapa]` → mueve la oportunidad.
4. **Calendario**: si el prospecto pide reunión, leer "Sam Miller - Olivo"
   (free-slots) y proponer horarios en la tarjeta.
5. **Activar envío real**: cambiar `alicia_secrets.ALICIA_DRY_RUN` a `false`.

---

## 7. Interruptores de seguridad
- `ALICIA_DRY_RUN=true` (default): no envía correos ni ejecuta acciones GHL reales.
- `ALICIA_AI_ENABLED=false` (default): apaga toda la IA.
- `ALICIA_ENABLED` (workflow GitHub Actions, alternativo): deshabilitado.

## 8. Tests
```
python -m pytest tests/test_alicia_filters.py tests/test_alicia_pipeline.py -q
```
