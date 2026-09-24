# Diseño: respuesta de Snov → contacto en GHL + bot interactivo por cliente

Fecha: 2026-09-24
Clientes en alcance: `balia`, `gbs`, `bambutech`

## 0. Fases

- **Fase 1 (este diseño, lista para implementar):** detectar respuestas de Snov,
  crear/actualizar el contacto en GHL automáticamente, avisar por Telegram (un
  bot por cliente) y permitir desde ahí mover el estatus del prospecto y crear
  tareas en GHL. Todo vía API de Snov + API de GHL + Telegram — **sin Gmail**.
- **Fase 2 (pendiente, fuera de este plan):** "Responder" (redactar/mandar el
  correo real al prospecto, con borrador sugerido por IA opcional) y "Agendar"
  reunión desde Telegram. Requiere acceso de envío a las casillas de correo
  reales — confirmado que **la API de Snov no permite enviar correos**, solo
  leerlos. Ver sección 9.

## 1. Contexto

Hoy, cuando un prospecto responde a una campaña de Snov.io, no hay nada automático
que lo lleve a GoHighLevel (GHL). Si el contacto no existe en GHL, la SDR no lo ve
ni tiene sus datos enriquecidos (empresa, cargo, tamaño de empresa, sitio web, etc.)
hasta que alguien lo carga a mano. Tampoco hay forma rápida de mover el estatus del
prospecto o dejarle una tarea sin entrar a GHL.

Existe una implementación previa y completa de un problema relacionado — **Alicia**
(rama sin mergear `origin/claude/snov-telegram-responses-nm5rlu`) — pero detecta
respuestas leyendo Gmail directamente (OAuth por casilla), solo está piloteada
para GBS, ata la creación del contacto a que la SDR apruebe una respuesta por
Telegram, y está ~4 semanas desactualizada respecto a `main`.

**Decisión:** no se toca ni se extiende Alicia en la Fase 1. Se construye un
sistema nuevo y más simple que no necesita Gmail para lo esencial (crear el
contacto, mover estatus, crear tareas). Gmail solo hace falta para Fase 2
(responder/agendar), que queda pendiente.

## 2. Credenciales y configuración (resueltas en esta sesión)

### 2.1 GHL por cliente
`clientes` (Supabase) tiene fila para los 3 clientes:
- `gbs` → `ghl_location_id = u9b8KkJXhM8lqJfzxa7G` (token `GHL_TOKEN_GBS_LOGISTICS`, rotado y verificado en vivo).
- `bambutech` → `ghl_location_id = FJ1YCwi4UVvwcBb8qlOb` (token `GHL_TOKEN_BAMBUTECH`, ya existía, verificado).
- `balia` → `ghl_location_id = eJnh0qIKSxz0C2CHbT2O` (token `GHL_TOKEN_BALIA`, nuevo; fila creada en esta sesión, verificado).

**Balia no tiene subcuenta GHL propia**: sus contactos viven en la misma location
que la cuenta privada de Conprospección (`GHL_LOCATION_CONPROSPECCION`, mismo
`locationId`, token distinto). Confirmado con la usuaria. Por eso todo contacto
creado/actualizado por este sistema lleva, para los 3 clientes (no solo Balia,
por trazabilidad uniforme):
- tag = `cliente_slug` (ej. `balia`, `gbs`, `bambutech`)
- campo estándar `source` = `snov-{cliente_slug}` (ej. `snov-balia`)

### 2.2 Telegram — un bot por cliente
Para no mezclar contactos entre clientes en un mismo chat, cada cliente tiene
su propio bot de Telegram (creado con @BotFather). Cada bot le llega a **Francisca
y Nora** (ambas le dan `/start`).

| Cliente | Bot | Token | Chat IDs |
| --- | --- | --- | --- |
| BambuTech | @bambutech_bot | `TELEGRAM_BOT_BAMBUTECH_TOKEN` ✅ | `TELEGRAM_BOT_BAMBUTECH_CHAT_IDS`: Francisca ✅ (`7311602262`), Nora pendiente |
| GBS | — | `TELEGRAM_BOT_GBS_TOKEN` pendiente | pendiente |
| Balia | — | `TELEGRAM_BOT_BALIA_TOKEN` pendiente | pendiente |

Acento visual por cliente en las tarjetas (emoji/color de encabezado): BambuTech
= verde 🟢. GBS y Balia: a definir (por defecto, un color distinto cada uno para
diferenciarlos a simple vista).

### 2.3 GBS — casillas de correo (para Fase 2, no usado en Fase 1)
Se recibió `Snov_Bulk_Email_Accounts_GBS_CORREGIDO.csv` con las 3 casillas de
GBS (`sam@`, `sammiller@`, `sam.miller@gbs-logistics.cl`) y sus contraseñas.
Se probó login IMAP directo y **falla en las 3**: Google exige contraseña de
aplicación (App Password) o OAuth, la contraseña de cuenta normal no alcanza.
Guardado en `.env.local` (`SMTP_GBS01/02/03_EMAIL/PASSWORD`) para cuando se
retome Fase 2. No se usa en Fase 1.

## 3. Qué NO cambia

- Alicia (Gmail + Telegram + aprobación) sigue intacta en su rama, sin mergear,
  solo GBS, tal como está.
- `sync_snov.py`, `sync_snov_prospects.py`, `sync_ghl.py` y el resto de los
  `sync_*.py` no se modifican en su comportamiento actual.
- `report_sdr_bot.py` (bot de reportes existente) no se toca — los bots nuevos
  son procesos separados con tokens separados, para no chocar con su
  `getUpdates` (Telegram no permite dos procesos escuchando el mismo bot).

## 4. Componentes nuevos

### 4.1 `sync/scripts/sync_snov_replies_to_ghl.py`
Script nuevo (patrón `sync_*.py`: argparse, `setup_logging`, `main()`, log a
`sync_runs`). Corre por Task Scheduler cada hora, 8am-8pm. Hace el create/update
automático del contacto (ver sección 6) y, cuando corresponde, dispara el aviso
por Telegram al bot del cliente correspondiente.

### 4.2 `sync/scripts/telegram_ghl_bot.py` (uno por cliente, o un solo proceso
que atiende los 3 bots en paralelo — se decide en el plan de implementación)
Bot interactivo nuevo (long-polling, independiente de `report_sdr_bot.py`).
Maneja:
- **Mover estatus**: la SDR responde (reply) a la tarjeta del contacto → el bot
  muestra botones con las opciones del custom field `STATUS PROSPECTO`
  (ordenadas en orden de embudo, no el orden crudo de GHL: No Contesta →
  Información Adicional → Coordinando Reunión → Reunión Agendada → Reagendar
  Reunión → cierres: No Interesado / No Califica / Deriva Refiere Directo /
  Deriva Refiere Seguimiento / Teléfono-Whatsapp no existen). Si ya está en
  ese estatus, responde avisando que no hay cambios.
- **Crear tarea**: la SDR responde a la tarjeta con texto tipo
  `tarea: llamar mañana 10am para coordinar reunión` → crea una tarea en GHL
  asociada al contacto (`POST /contacts/{contactId}/tasks`, a confirmar forma
  exacta del payload contra la API real al implementar).
- **Chequeo de choque de identidad** (ver sección 7) antes de cualquier acción
  sobre un contacto ya existente.

### 4.3 Ampliación de `GHLClient` (`sync/scripts/ghl_client.py`)
Hoy el cliente es 100% lectura. Se agregan:
- `find_contact_by_email(location_id, email) -> dict | None`
  (`GET /contacts/?locationId=&query=<email>&limit=5`, filtra por email exacto).
- `custom_field_id_map(location_id) -> dict[str, str]` (cachea
  `list_custom_fields()` ya existente, arma `{nombre_normalizado: id}` — cada
  subcuenta GHL usa IDs de custom field distintos, incidente ya conocido).
- `create_contact(location_id, payload) -> dict` (`POST /contacts/`).
- `update_contact(contact_id, payload) -> dict` (`PUT /contacts/{id}`).
- `update_custom_field(contact_id, field_id, value)` (mover estatus).
- `create_task(contact_id, payload)` (crear tarea).

### 4.4 Enriquecimiento (corregido tras verificar con datos reales de Snov)
Se descarta la migración a `snov_prospects` planteada originalmente: verificado
contra la API real, `prospects_in_list()` (la fuente de `snov_prospects`) casi
nunca trae empresa/cargo/sitio web/tamaño — la mayoría de esos campos vienen
vacíos. La fuente confiable es `SnovClient.prospect_by_id(prospectId)`, y
`replies()` ya entrega el `prospectId` de cada respuesta. Por eso el
enriquecimiento para este flujo llama siempre a `prospect_by_id()` directo
(no depende de `snov_prospects`). Forma real verificada de la respuesta:

```json
{"success": true, "data": {
  "id": "...", "name": "...", "firstName": "...", "lastName": "...",
  "country": "...", "locality": "...", "industry": "...",
  "phones": [],
  "social": [{"link": "https://linkedin.com/in/...", "type": "linkedinProfile"}],
  "currentJob": [{"companyName": "...", "position": "...", "site": "...",
                  "size": "11-50", "industry": "...", "country": "...",
                  "city": "...", "socialLink": "https://linkedin.com/company/..."}]
}}
```
Mapeo: `currentJob[0].companyName`→empresa, `.position`→cargo, `.site`→website,
`.size`→tamaño empresa, `.socialLink`→linkedin_empresa, `social[].link`
(type linkedinProfile/linkedIn)→linkedin_personal, `phones[0]`→teléfono (si hay).

## 5. Flujo

```
sync_snov_replies_to_ghl.py  (Task Scheduler, cada hora, 8am-8pm)
  para cada cliente en clientes (balia, gbs, bambutech) con ghl_location_id:
    para cada campaña de snov_campaign_map de ese cliente:
      replies = SnovClient.replies(campaign_id)          # ya existe
      para cada prospecto que respondió:
        datos = snov_prospects (ya sincronizado, por snov_prospect_id/email)
                o snov.prospect_by_email() si no está sincronizado todavía
        contacto_ghl = GHLClient.find_contact_by_email(location_id, email)

        si NO existe:
            create_contact()  con todos los campos disponibles
            -> Telegram: tarjeta "contacto nuevo" al bot del cliente
        si existe Y el nombre coincide (o GHL no tiene nombre cargado):
            update_contact()  solo con los campos vacíos (no pisa datos ya cargados)
            -> Telegram: tarjeta "contacto actualizado"
        si existe pero el NOMBRE no coincide (choque de identidad, sección 7):
            no toca nada -> Telegram: alerta de choque para revisión manual
        si ya está completo y sin choques:
            no hace nada (idempotente sin tabla de estado extra)

  sync_runs.insert(source="snov_replies_ghl", stats={...})
```

Cada tarjeta de Telegram queda "viva": responderla (reply) abre el flujo de
mover estatus / crear tarea descrito en 4.2.

Idempotencia: no hay tabla de "ya procesado". Cada corrida vuelve a mirar el
estado real del contacto en GHL y decide create/update/skip en base a eso —
correr el script dos veces seguidas es seguro y no genera duplicados ni pisa
datos.

## 6. Mapeo de campos

Fuente única: `docs/GHL_CAMPOS_ESTANDAR.md` (se le agrega una sección para este job).

**Estándar GHL** (van directo en el body del contacto, no como customField):
`firstName`, `lastName`, `name`, `email`, `phone`, `companyName`, `website`,
`country`, `source`, `tags`.

**Custom fields** (resueltos por id vía `custom_field_id_map`, valores desde
`snov_prospects`): `cargo`, `industria`, `tamano_empresa`, `linkedin_personal`
(`linkedInUrl` de Snov), `linkedin_empresa` (si Snov lo trae).

Si un dato no está disponible en Snov, se omite ese campo (no se manda vacío
pisando algo que la SDR ya haya cargado a mano en GHL).

## 7. Choque de identidad (email ya existe, pero el nombre no coincide)

Caso real detectado en la conversación: el email de la campaña Snov ya existe
como contacto en GHL, pero pertenece a otra persona (ej. GHL tiene "Juan Pérez"
con su teléfono, pero quien respondió en Snov es "José García" — típico de
casillas compartidas o datos cruzados).

Regla: antes de actualizar un contacto **existente**, comparar nombre de Snov
vs nombre en GHL (normalizado, sin tildes/mayúsculas). Si coinciden o GHL no
tiene nombre cargado → seguir con el update normal. Si claramente no coinciden
→ **no tocar el contacto ni el estatus**, mandar alerta a Telegram para que la
SDR decida a mano. Nunca se fusiona ni se pisa historial de una persona con
datos de otra automáticamente.

## 8. Programación (Task Scheduler)

- `sync_snov_replies_to_ghl.py`: tarea nueva, cada hora entre 8:00 y 20:00
  (mismo mecanismo que los reportes existentes).
- `telegram_ghl_bot.py` (los 3 bots interactivos): proceso de larga duración
  (long-polling), no una tarea programada — se deja corriendo, mismo patrón
  operativo que `run_sdr_bot.bat` / `report_sdr_bot.py`.

## 9. Fase 2 (pendiente, no incluida en el plan de implementación actual)

"Responder" (mandar correo real al prospecto, con borrador IA opcional) y
"Agendar" reunión desde Telegram:
- Confirmado: la API de Snov **no** permite enviar correos, solo leerlos (ni
  siquiera con webhooks). Hace falta acceso de envío real a la casilla.
- Dos caminos posibles cuando se retome: (a) generar App Password de Google
  por casilla (simple, sin OAuth) — probar si Workspace lo permite; (b)
  retomar el módulo Gmail OAuth de Alicia (ya construido y probado para GBS).
- BambuTech: agendar SIEMPRE en hora México, con el calendario de
  `michelle.hernandez@bambutech-services.com` (aunque la campaña haya llegado
  por otra de sus 3 casillas); pero la **respuesta de correo** debe salir de
  la casilla específica a la que el prospecto le escribió, no siempre la de
  Michelle. Esto hay que tenerlo en cuenta en el diseño de Fase 2.
- No se empieza a implementar hasta que se apruebe un diseño aparte para esto.

## 10. Testing

Tests unitarios sin llamadas reales a Snov/GHL/Telegram, mockeando `SnovClient`
y `GHLClient`:
- Mapeo de campos Snov → payload GHL (incluye tag/source por cliente).
- Lógica de decisión create / update-solo-lo-que-falta / skip.
- Chequeo de choque de identidad (nombre no coincide → no toca, alerta).
- Resolución de `custom_field_id_map` con distintos sets de IDs por location.
- Orden y armado de los botones de estatus (funnel, no el orden crudo de GHL).

## 11. Riesgos / supuestos abiertos

- **Confirmado (no solo asumido): `snov_campaign_map` no tiene NINGUNA campaña
  mapeada a `balia`** (0 filas). Hay campañas activas llamadas "CP CHILE/MEXICO/PERÚ
  - ..." que podrían ser las de Balia (corren bajo la cuenta de Conprospección),
  pero no se puede confirmar por nombre solo. Bloquea probar Fase 1 en vivo para
  Balia hasta que la usuaria confirme qué `snov_campaign_id` son de Balia y se
  agreguen a `snov_campaign_map`. El código no depende de esto para funcionar
  (simplemente no encuentra campañas de balia y no hace nada), pero sin este
  dato Balia no va a generar ningún contacto automático.
- `SnovClient.replies()` no pagina explícitamente en el código actual más allá
  del parámetro `offset` — confirmar al implementar si con campañas grandes
  hace falta iterar por offset hasta vaciar resultados.
- Falta token/chat_id de los bots de GBS y Balia, y que Nora le dé `/start` a
  los 3 — no bloquea escribir el código, sí bloquea probarlo en vivo para esos
  2 clientes.
- El nombre exacto del custom field `STATUS PROSPECTO` (y su lista de opciones)
  se confirmó en la location de GBS; hay que verificar que BambuTech y la
  location compartida de Balia/Conprospección tengan el mismo campo con las
  mismas opciones (los IDs van a ser distintos igual, ya contemplado).
