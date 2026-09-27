# Equipo Alicia Conversational Reporting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hacer que `@equipo_alicia_bot` responda consultas operativas libres con el mismo motor del reporte horario, mida tiempo comprobable por cliente y entregue un cierre diario con gráficos, sin automatizaciones de cinco minutos.

**Architecture:** Un documento operativo canónico se construye desde eventos normalizados de GHL, Snov, IMAP/SMTP y Supabase. El reporte programado y el bot interactivo consumen ese mismo documento; un asignador de intervalos reparte cada segundo laboral entre teléfono, otras gestiones y sin actividad registrada sin duplicaciones. El enrutador conversacional es determinista, admite varias intenciones por pregunta y solo responde al chat privado configurado.

**Tech Stack:** Python 3.14, pytest, httpx, Pillow, IMAP/SMTP, GoHighLevel API, Snov API, Supabase/PostgREST, Telegram Bot API HTML.

---

## Estructura de archivos

- Crear `sync/scripts/sdr_reporting/time_usage.py`: intervalos canónicos, unión, prioridad y distribución por hora/cliente.
- Crear `sync/scripts/sdr_reporting/email_tracking.py`: deduplicación de respuestas Snov/GHL/IMAP y estado atendida/pendiente.
- Crear `sync/scripts/sdr_reporting/query.py`: documento operativo compartido y consultas por fecha/intervalo/cliente.
- Crear `sync/scripts/sdr_reporting/intents.py`: interpretación determinista de preguntas.
- Crear `sync/scripts/sdr_reporting/charts.py`: PNG horarios y de cierre.
- Modificar `sync/scripts/sdr_reporting/models.py`: tipos canónicos.
- Modificar `sync/scripts/sdr_reporting/metrics.py`: contestada `>20s`, reintentos y tareas de hoy separadas de atrasadas.
- Modificar `sync/scripts/sdr_reporting/sources.py`: eventos con inicio/fin, contacto y fuente manual.
- Modificar `sync/scripts/sdr_reporting/service.py`: construir el documento compartido, no una versión exclusiva del renderer.
- Modificar `sync/scripts/sdr_reporting/render.py`: secciones verticales legibles.
- Modificar `sync/scripts/sdr_reporting/storage.py`: upsert/lectura de eventos SMTP y snapshots versionados.
- Modificar `sync/scripts/sdr_reporting/telegram.py`: documento, foto, botones y verificación del único chat.
- Modificar `sync/scripts/report_sdr_bot.py`: reemplazar cálculos legacy por `query.py` + `intents.py`.
- Modificar `sync/scripts/report_sdr_telegram.py` y `sync/scripts/sdr_reporting/cli.py`: horario y cierre sobre el documento compartido.
- Modificar `sync/scripts/client_mailboxes.py`: devolver `Message-ID` de envío y leer enviados directos.
- Modificar `sync/scripts/telegram_ghl_bot.py`: auditar respuesta SMTP solo después de éxito.
- Eliminar `sync/scripts/run_sdr_meeting_monitor.bat`.
- Modificar `PROJECT_MASTER_CONTEXT.md`: frecuencia, consultas y ausencia del monitor.
- Crear pruebas enfocadas bajo `tests/test_sdr_*` y ampliar `tests/test_client_mailboxes.py` y `tests/test_telegram_ghl_bot.py`.

La tabla existente `public.sdr_activity_events` ya soporta los eventos nuevos
mediante `source`, `source_id`, `cliente_slug`, `contact_id`, `event_type`,
`occurred_at`, `duration_seconds` y `metadata`; no se crea una migración sin
necesidad. Antes de activar se verificará que RLS siga habilitado, que
`anon/authenticated` no tengan privilegios y que el secreto permanezca solo en
los procesos locales. Esta decisión sigue la documentación actual de Supabase:
las tablas expuestas requieren RLS y grants explícitos, mientras la clave
secreta debe permanecer en servidor.

### Task 1: Modelos canónicos y asignación del tiempo

**Files:**
- Modify: `sync/scripts/sdr_reporting/models.py`
- Create: `sync/scripts/sdr_reporting/time_usage.py`
- Create: `tests/test_sdr_reporting_time_usage.py`

- [ ] **Step 1: Escribir pruebas fallidas para prioridad, unión y almuerzo**

```python
def test_phone_wins_and_every_hour_sums_sixty_minutes():
    events = [
        ActivityInterval("call-1", "bambutech", "phone", at(13, 0), at(13, 20), "c1"),
        ActivityInterval("mail-1", "gbs", "other", at(13, 10), at(13, 15), "c2"),
        ActivityInterval("task-1", "bambutech", "other", at(13, 30), at(13, 35), "c3"),
    ]
    usage = allocate_usage(at(13, 0), at(14, 0), events)
    assert usage.phone_seconds_by_client == {"bambutech": 1200}
    assert usage.other_seconds_by_client == {"bambutech": 300}
    assert usage.unregistered_seconds == 2100
    assert usage.total_seconds == 3600

def test_lunch_is_not_measured():
    usage = allocate_workday(date(2026, 9, 25), at(15, 0), [])
    assert all(bucket.start.hour != 16 for bucket in usage.hours)
```

- [ ] **Step 2: Ejecutar las pruebas y comprobar el fallo**

Run: `python -m pytest tests/test_sdr_reporting_time_usage.py -q`

Expected: FAIL con `ModuleNotFoundError: sdr_reporting.time_usage`.

- [ ] **Step 3: Añadir los modelos exactos**

```python
@dataclass(frozen=True)
class ActivityInterval:
    source_id: str
    client: str
    kind: Literal["phone", "other"]
    start: datetime
    end: datetime
    contact_id: str | None = None
    event_type: str = ""

@dataclass(frozen=True)
class TimeUsage:
    start: datetime
    end: datetime
    phone_seconds_by_client: dict[str, int]
    other_seconds_by_client: dict[str, int]
    unregistered_seconds: int

    @property
    def total_seconds(self) -> int:
        return int((self.end - self.start).total_seconds())
```

- [ ] **Step 4: Implementar el asignador con prioridad por segundo**

```python
def allocate_usage(start: datetime, end: datetime, events: Iterable[ActivityInterval]) -> TimeUsage:
    phone = Counter()
    other = Counter()
    unregistered = 0
    ordered = sorted(events, key=lambda event: (event.start, event.source_id))
    cursor = start
    while cursor < end:
        active = [event for event in ordered if event.start <= cursor < event.end]
        calls = [event for event in active if event.kind == "phone"]
        if calls:
            chosen = max(calls, key=lambda event: (event.start, event.source_id))
            phone[chosen.client] += 1
        elif active:
            chosen = max(active, key=lambda event: (event.start, event.source_id))
            other[chosen.client] += 1
        else:
            unregistered += 1
        cursor += timedelta(seconds=1)
    return TimeUsage(start, end, dict(phone), dict(other), unregistered)
```

`allocate_workday` recorre exclusivamente `work_blocks_for(day)`, divide en
horas y recorta el último bucket a `now`. No incluye 16:00–17:00.

- [ ] **Step 5: Ejecutar pruebas de la unidad**

Run: `python -m pytest tests/test_sdr_reporting_time_usage.py -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add sync/scripts/sdr_reporting/models.py sync/scripts/sdr_reporting/time_usage.py tests/test_sdr_reporting_time_usage.py
git commit -m "Calcular uso del tiempo sin duplicaciones"
```

### Task 2: Métricas oficiales de llamadas, tareas y contactos

**Files:**
- Modify: `sync/scripts/sdr_reporting/models.py`
- Modify: `sync/scripts/sdr_reporting/metrics.py`
- Modify: `sync/scripts/sdr_reporting/service.py`
- Modify: `tests/test_sdr_reporting_activity.py`
- Modify: `tests/test_sdr_reporting_tasks.py`

- [ ] **Step 1: Cambiar las pruebas para la frontera estricta de 20 segundos**

```python
def test_answered_means_strictly_more_than_twenty_seconds():
    metrics = call_metrics([
        {"contact_id": "a", "duration_seconds": 20, "phone_seconds": 30},
        {"contact_id": "b", "duration_seconds": 21, "phone_seconds": 35},
        {"contact_id": "b", "duration_seconds": 5, "phone_seconds": 15},
    ])
    assert metrics.calls == 3
    assert metrics.answered == 1
    assert metrics.unanswered == 2
    assert metrics.repeated_contacts == 1
    assert metrics.answered_seconds == 21
    assert metrics.unanswered_phone_seconds == 45
    assert metrics.retry_calls == 1
```

```python
def test_today_goal_excludes_overdue_tasks():
    progress = task_progress(baseline_with(today={"t1", "t2"}, overdue={"old"}), {"t1"})
    assert progress.today_done == 1
    assert progress.today_total == 2
    assert progress.overdue_pending == 1
```

- [ ] **Step 2: Ejecutar y verificar los fallos de contrato**

Run: `python -m pytest tests/test_sdr_reporting_activity.py tests/test_sdr_reporting_tasks.py -q`

Expected: FAIL por campos ausentes y semántica legacy.

- [ ] **Step 3: Reemplazar `CallMetrics` y `TaskProgress`**

```python
@dataclass(frozen=True)
class CallMetrics:
    calls: int
    unique_contacts: int
    answered: int
    unanswered: int
    retry_calls: int
    answered_seconds: int
    unanswered_phone_seconds: int
    retry_phone_seconds: int
    phone_seconds: int

@dataclass(frozen=True)
class TaskProgress:
    today_done: int
    today_total: int
    overdue_pending: int
```

`call_metrics` clasifica con `duration_seconds > 20`, calcula reintentos a
partir de la segunda llamada de cada contacto y conserva los segundos de
teléfono de cada grupo. `task_progress` usa `due_today_ids` para meta/numerador
y `overdue_ids` solo para el contador separado.

- [ ] **Step 4: Añadir contactos trabajados como unión por cliente**

```python
def worked_contacts(events: Iterable[dict]) -> set[tuple[str, str]]:
    return {
        (event["client"], event["contact_id"])
        for event in events
        if event.get("manual") is True and event.get("contact_id")
    }
```

- [ ] **Step 5: Adaptar `service.py` sin mantener alias ambiguos**

El payload por cliente usa `tasks_today_done`, `tasks_today_total`,
`tasks_overdue`, `calls`, `contacts`, `answered`, `unanswered`, `retry_calls`,
`answered_seconds`, `unanswered_phone_seconds`, `retry_phone_seconds`,
`phone_seconds` y `worked_contacts`.

- [ ] **Step 6: Ejecutar las pruebas afectadas**

Run: `python -m pytest tests/test_sdr_reporting_activity.py tests/test_sdr_reporting_tasks.py tests/test_sdr_reporting_render.py -q`

Expected: PASS después de adaptar los fixtures de render.

- [ ] **Step 7: Commit**

```bash
git add sync/scripts/sdr_reporting/models.py sync/scripts/sdr_reporting/metrics.py sync/scripts/sdr_reporting/service.py tests/test_sdr_reporting_activity.py tests/test_sdr_reporting_tasks.py tests/test_sdr_reporting_render.py
git commit -m "Separar llamadas tareas y contactos trabajados"
```

### Task 3: Eventos canónicos y ventanas de cinco minutos

**Files:**
- Modify: `sync/scripts/sdr_reporting/sources.py`
- Modify: `sync/scripts/sdr_reporting/service.py`
- Create: `tests/test_sdr_reporting_events.py`

- [ ] **Step 1: Escribir prueba fallida de normalización**

```python
def test_manual_email_creates_five_minute_window_but_workflow_does_not():
    manual = activity_intervals([message(source="app", at=at(12, 10))], "gbs")
    automatic = activity_intervals([message(source="workflow", at=at(12, 20))], "gbs")
    assert manual[0].start == at(12, 10)
    assert manual[0].end == at(12, 15)
    assert automatic == []

def test_call_uses_observed_phone_interval():
    intervals = activity_intervals([call(at=at(13, 0), phone_seconds=42)], "bambutech")
    assert intervals[0].end == at(13, 0, 42)
```

- [ ] **Step 2: Ejecutar y confirmar el fallo**

Run: `python -m pytest tests/test_sdr_reporting_events.py -q`

Expected: FAIL con `ImportError: activity_intervals`.

- [ ] **Step 3: Implementar fuentes admitidas y trazabilidad manual**

```python
OTHER_WINDOW = timedelta(minutes=5)

def activity_intervals(messages: Iterable[dict], client: str) -> list[ActivityInterval]:
    result = []
    for message in messages:
        when = message.get("occurred_at")
        if message.get("message_type") == "TYPE_CALL" and when:
            seconds = max(0, int(message.get("phone_seconds") or 0))
            result.append(ActivityInterval(str(message["id"]), client, "phone", when,
                                           when + timedelta(seconds=seconds),
                                           message.get("contact_id"), "call"))
        elif (message.get("message_type") == "TYPE_EMAIL"
              and message.get("direction") == "outbound"
              and message.get("source") in MANUAL_EMAIL_SOURCES and when):
            result.append(ActivityInterval(str(message["id"]), client, "other", when,
                                           when + OTHER_WINDOW,
                                           message.get("contact_id"), "manual_email"))
    return result
```

Tareas completadas y eventos SMTP exitosos se convierten mediante funciones
equivalentes. `dateUpdated` de contacto o funnel solo genera ventana cuando el
payload demuestra una acción manual; si no, se conserva para cantidades del
cierre sin acreditar tiempo.

- [ ] **Step 4: Construir el uso horario dentro de `build_live_report`**

El servicio agrega `usage.hours`, `usage.total` y `usage.by_client`. Cada hora
contiene segundos de teléfono por cliente, otras gestiones por cliente y sin
registro. El corte incompleto termina en `now`.

- [ ] **Step 5: Ejecutar pruebas de eventos, actividad y servicio**

Run: `python -m pytest tests/test_sdr_reporting_events.py tests/test_sdr_reporting_activity.py tests/test_sdr_reporting_sources.py -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add sync/scripts/sdr_reporting/sources.py sync/scripts/sdr_reporting/service.py tests/test_sdr_reporting_events.py
git commit -m "Normalizar eventos de actividad del SDR"
```

### Task 4: Respuestas de campaña y auditoría SMTP exitosa

**Files:**
- Create: `sync/scripts/sdr_reporting/email_tracking.py`
- Modify: `sync/scripts/client_mailboxes.py`
- Modify: `sync/scripts/telegram_ghl_bot.py`
- Modify: `sync/scripts/sdr_reporting/storage.py`
- Create: `tests/test_sdr_reporting_email_tracking.py`
- Modify: `tests/test_client_mailboxes.py`
- Modify: `tests/test_telegram_ghl_bot.py`

- [ ] **Step 1: Escribir pruebas para Message-ID, pendientes y deduplicación**

```python
def test_send_reply_returns_message_id_after_success(monkeypatch):
    result = send_reply("sam@gbs.test", "lead@test", "Hola", "Respuesta", "<inbound>")
    assert result.message_id.startswith("<")
    assert result.to_email == "lead@test"

def test_same_reply_from_snov_and_imap_counts_once():
    status = summarize_threads([
        inbound("snov", "<reply-1>", "gbs", "lead@test", at(12, 0)),
        inbound("imap", "<reply-1>", "gbs", "lead@test", at(12, 0)),
        outbound("smtp", "<answer-1>", "gbs", "lead@test", at(12, 20), references="<reply-1>"),
    ])
    assert status.received == 1
    assert status.responded == 1
    assert status.pending == []
```

- [ ] **Step 2: Ejecutar y verificar fallos**

Run: `python -m pytest tests/test_client_mailboxes.py tests/test_sdr_reporting_email_tracking.py tests/test_telegram_ghl_bot.py -q`

Expected: FAIL porque `send_reply` devuelve `None` y no existe el agregador.

- [ ] **Step 3: Hacer que `send_reply` devuelva evidencia del envío**

```python
@dataclass(frozen=True)
class SentReply:
    message_id: str
    account_email: str
    to_email: str
    subject: str
    references: str | None

def send_reply(...) -> SentReply:
    # construir msg como hoy, autenticar y ejecutar server.send_message(msg)
    return SentReply(msg["Message-ID"], account_email, to_email, msg["Subject"], references)
```

- [ ] **Step 4: Registrar el evento solo después del éxito SMTP**

```python
sent = send_reply(...)
store.record_activity_event(
    source="smtp_reply",
    source_id=sent.message_id,
    client=slug,
    contact_id=pending["contact_id"],
    event_type="email_reply_sent",
    occurred_at=datetime.now(CHILE),
    metadata={"to": sent.to_email, "subject": sent.subject, "references": sent.references},
)
```

Si SMTP lanza una excepción, no se inserta evento ni se confirma éxito al
chat.

- [ ] **Step 5: Leer respuestas enviadas directamente desde IMAP**

Agregar `list_sent_replies(cliente_slug, start, end)` que descubre la carpeta
con atributo `\\Sent`, usa `SINCE` y filtra `Date` dentro del intervalo. Devuelve
`Message-ID`, `In-Reply-To`, `References`, `To`, asunto, fecha y casilla. La
función continúa con otras casillas si una credencial falla. BALIA devuelve una
disponibilidad explícita `False`, no una lista que se interprete como cero.

- [ ] **Step 6: Unir Snov, GHL, IMAP y eventos SMTP**

`summarize_threads` normaliza `Message-ID`, deduplica inbound, enlaza outbound
posterior por referencias y usa destinatario+asunto solo como respaldo. Devuelve
por cliente `manual_sent`, `campaign_received`, `responded`, `pending[]` y
`average_response_seconds`. Cada pendiente contiene nombre/email, asunto,
fecha y antigüedad para responder "qué correos faltan".

- [ ] **Step 7: Verificar RLS y grants sin crear migración innecesaria**

Run mediante Supabase MCP/SQL:

```sql
select relrowsecurity
from pg_class
where oid = 'public.sdr_activity_events'::regclass;

select grantee, privilege_type
from information_schema.role_table_grants
where table_schema = 'public'
  and table_name = 'sdr_activity_events'
  and grantee in ('anon', 'authenticated', 'service_role');
```

Expected: RLS `true`; ningún grant para `anon/authenticated`; acceso de
`service_role`/secreto solo en proceso local. No se expone el secreto a Telegram.

- [ ] **Step 8: Ejecutar pruebas de correo**

Run: `python -m pytest tests/test_client_mailboxes.py tests/test_sdr_reporting_email_tracking.py tests/test_telegram_ghl_bot.py -q`

Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add sync/scripts/client_mailboxes.py sync/scripts/telegram_ghl_bot.py sync/scripts/sdr_reporting/email_tracking.py sync/scripts/sdr_reporting/storage.py tests/test_client_mailboxes.py tests/test_sdr_reporting_email_tracking.py tests/test_telegram_ghl_bot.py
git commit -m "Auditar respuestas SMTP y correos pendientes"
```

### Task 5: Documento operativo compartido y consultas

**Files:**
- Create: `sync/scripts/sdr_reporting/query.py`
- Modify: `sync/scripts/sdr_reporting/service.py`
- Modify: `sync/scripts/sdr_reporting/storage.py`
- Create: `tests/test_sdr_reporting_query.py`

- [ ] **Step 1: Escribir pruebas de totales y cortes**

```python
def test_document_has_every_client_and_total():
    document = build_operational_document(fixture_sources(), day=DAY, now=at(14, 0))
    assert tuple(document["clients"]) == ("bambutech", "gbs", "balia")
    assert document["total"]["calls"] == sum(c["calls"] for c in document["clients"].values())
    assert document["usage"]["total_seconds"] == 3 * 3600

def test_pending_email_query_returns_identity_and_age():
    result = answer_document(document, QueryRequest(("email_pending",), DAY, None, None, None, False))
    assert result["email_pending"][0]["email"] == "lead@test"
    assert result["email_pending"][0]["age_seconds"] == 3600
```

- [ ] **Step 2: Ejecutar y confirmar fallo**

Run: `python -m pytest tests/test_sdr_reporting_query.py -q`

Expected: FAIL con `ModuleNotFoundError: sdr_reporting.query`.

- [ ] **Step 3: Implementar el documento versionado**

```python
SCHEMA_VERSION = 2

def build_operational_document(day: date, now: datetime | None = None) -> dict:
    report = build_live_report(day, now)
    return {
        "schema_version": SCHEMA_VERSION,
        "day": day,
        "cut": report["cut"],
        "sdr": "Nora",
        "clients": report["clients"],
        "total": sum_client_metrics(report["clients"]),
        "usage": report["usage"],
        "adherence": report["block_adherence"],
        "email_pending": report["email_pending"],
        "funnel": report["funnel"],
        "meetings": report["meetings"],
        "availability": report["availability"],
    }
```

`answer_document` filtra por cliente e intervalo y devuelve secciones tipadas;
no renderiza Telegram. `SnapshotStore.save_report` guarda versión 2 y
`load_latest(day, at_or_before)` recupera el corte apropiado.

- [ ] **Step 4: Implementar refresco en vivo o snapshot**

`query_operational(request)` usa snapshot cuando cubre el intervalo y tiene
menos de diez minutos; usa `build_operational_document` cuando `request.live`
es verdadero o el corte solicitado es posterior.

- [ ] **Step 5: Ejecutar pruebas**

Run: `python -m pytest tests/test_sdr_reporting_query.py tests/test_sdr_reporting_storage.py -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add sync/scripts/sdr_reporting/query.py sync/scripts/sdr_reporting/service.py sync/scripts/sdr_reporting/storage.py tests/test_sdr_reporting_query.py tests/test_sdr_reporting_storage.py
git commit -m "Compartir documento operativo entre bot y reportes"
```

### Task 6: Reporte vertical y gráficos de barras

**Files:**
- Modify: `sync/scripts/sdr_reporting/render.py`
- Create: `sync/scripts/sdr_reporting/charts.py`
- Modify: `sync/scripts/sdr_reporting/extended.py`
- Modify: `tests/test_sdr_reporting_render.py`
- Create: `tests/test_sdr_reporting_charts.py`

- [ ] **Step 1: Escribir pruebas de contenido eliminado y suma visual**

```python
def test_hourly_render_is_vertical_and_removes_confusing_sections():
    joined = "\n".join(render_hourly(document_fixture()))
    assert "BAMBU TECH" in joined and "GBS" in joined and "BALIA" in joined and "TOTAL" in joined
    assert "Tareas de hoy" in joined and "Tareas atrasadas" in joined
    assert "Arrastre vencido" not in joined
    assert "Contactos prioritarios" not in joined
    assert "VENTANA CRÍTICA" not in joined
    assert "VS AYER" not in joined
    assert "<pre>" not in joined

def test_every_complete_chart_hour_sums_sixty_minutes():
    series = chart_series(document_fixture())
    assert all(sum(hour.values()) == 60 for hour in series if hour["complete"])
```

- [ ] **Step 2: Ejecutar y verificar fallos**

Run: `python -m pytest tests/test_sdr_reporting_render.py tests/test_sdr_reporting_charts.py -q`

Expected: FAIL por contenido legacy y módulo ausente.

- [ ] **Step 3: Renderizar secciones verticales**

Crear helpers `render_usage`, `render_call_counts`, `render_call_minutes`,
`render_client_work`, `render_tasks`, `render_adherence`, `render_email` y
`render_meetings`. Cada helper lista BAMBU TECH, GBS, BALIA y TOTAL en líneas
independientes, escapa contenido y retorna `N/D` cuando `availability` es falso.
Telegram se divide solo entre secciones y cada mensaje queda bajo 4096
caracteres.

- [ ] **Step 4: Crear gráfico horario apilado**

```python
SEGMENT_COLORS = {
    "bambutech": "#22C55E", "gbs": "#8B5CF6", "balia": "#EC4899",
    "other": "#94A3B8", "unregistered": "#DC2626",
}

def chart_series(document: dict) -> list[dict]:
    return [seconds_to_exact_minutes(bucket) for bucket in document["usage"]["hours"]]
```

`render_usage_chart` dibuja una barra horizontal de 60 minutos por hora, leyenda
y totales. `render_close_chart` agrega barras por cliente para llamadas,
contactos trabajados y tareas cumplidas. Los valores provienen del documento,
no se recalculan en Pillow.

- [ ] **Step 5: Ejecutar pruebas y abrir PNG de fixture**

Run: `python -m pytest tests/test_sdr_reporting_render.py tests/test_sdr_reporting_charts.py -q`

Expected: PASS y PNG válido de 1200px de ancho.

- [ ] **Step 6: Commit**

```bash
git add sync/scripts/sdr_reporting/render.py sync/scripts/sdr_reporting/charts.py sync/scripts/sdr_reporting/extended.py tests/test_sdr_reporting_render.py tests/test_sdr_reporting_charts.py
git commit -m "Ordenar reporte horario y gráficos de actividad"
```

### Task 7: Preguntas naturales, botones y chat privado

**Files:**
- Create: `sync/scripts/sdr_reporting/intents.py`
- Modify: `sync/scripts/report_sdr_bot.py`
- Modify: `sync/scripts/sdr_reporting/telegram.py`
- Create: `tests/test_sdr_reporting_intents.py`
- Create: `tests/test_report_sdr_bot.py`
- Modify: `tests/test_sdr_reporting_telegram.py`

- [ ] **Step 1: Escribir pruebas de preguntas compuestas**

```python
@pytest.mark.parametrize("text,intents", [
    ("¿Cuántos minutos no ha trabajado hasta ahora?", ("time_usage",)),
    ("¿Cuántos correos llegaron, respondió y cuáles faltan?",
     ("email_summary", "email_pending")),
    ("Llamadas y minutos por cliente de 11 a 12", ("call_counts", "call_minutes")),
    ("¿Cuántas tareas de hoy y atrasadas hay?", ("tasks",)),
    ("Dame el funnel de GBS hoy", ("funnel",)),
    ("Mándame el gráfico", ("chart",)),
])
def test_parse_queries(text, intents):
    request = parse_query(text, now=at(15, 0))
    assert request.intents == intents

def test_interval_and_client_are_extracted():
    request = parse_query("GBS de 12 a 13", now=at(15, 0))
    assert request.client == "gbs"
    assert request.start.hour == 12 and request.end.hour == 13
```

- [ ] **Step 2: Escribir prueba de autorización**

```python
def test_bot_ignores_unauthorized_chat(monkeypatch):
    controller = BotController(allowed_chat_id="123", query=fake_query)
    assert controller.handle({"chat": {"id": 999}, "text": "resumen"}) is None
    assert fake_query.calls == []
```

- [ ] **Step 3: Ejecutar y confirmar fallos**

Run: `python -m pytest tests/test_sdr_reporting_intents.py tests/test_report_sdr_bot.py -q`

Expected: FAIL por módulos/controlador ausentes.

- [ ] **Step 4: Implementar `QueryRequest` y parser multi-intención**

```python
@dataclass(frozen=True)
class QueryRequest:
    intents: tuple[str, ...]
    day: date
    start: datetime | None
    end: datetime | None
    client: str | None
    live: bool
```

Normalizar tildes, detectar todos los grupos de palabras (no usar `elif`),
extraer cliente, `hoy/ayer`, rango `HH[:MM] a HH[:MM]` y `ahora/en vivo`.
Preguntas no reconocidas devuelven el menú; no producen respuestas inventadas.

- [ ] **Step 5: Reemplazar el bot legacy por controlador compartido**

`report_sdr_bot.py` conserva long-polling, pero elimina `day_stats`,
`txt_comparativo`, clientes hardcodeados y cálculos duplicados. En startup:

1. verifica `getMe == equipo_alicia_bot`;
2. exige `TELEGRAM_SDR_CHAT_ID`;
3. ignora mensajes de cualquier otro chat;
4. llama `parse_query` y `query_operational`;
5. renderiza las secciones pedidas;
6. envía PNG si la intención es `chart`.

- [ ] **Step 6: Añadir teclado de respuestas**

```python
MENU_KEYBOARD = {
    "keyboard": [
        [{"text": "Tiempo trabajado"}, {"text": "Llamadas"}],
        [{"text": "Tareas"}, {"text": "Correos"}],
        [{"text": "Funnel"}, {"text": "Reuniones"}],
        [{"text": "Gráfico de hoy"}, {"text": "Cierre"}],
    ],
    "resize_keyboard": True,
}
```

- [ ] **Step 7: Ejecutar pruebas de bot, Telegram e intenciones**

Run: `python -m pytest tests/test_sdr_reporting_intents.py tests/test_report_sdr_bot.py tests/test_sdr_reporting_telegram.py -q`

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add sync/scripts/sdr_reporting/intents.py sync/scripts/report_sdr_bot.py sync/scripts/sdr_reporting/telegram.py tests/test_sdr_reporting_intents.py tests/test_report_sdr_bot.py tests/test_sdr_reporting_telegram.py
git commit -m "Responder consultas operativas en equipo Alicia"
```

### Task 8: Programación horaria, reuniones y cierre

**Files:**
- Modify: `sync/scripts/sdr_reporting/cli.py`
- Modify: `sync/scripts/report_sdr_telegram.py`
- Modify: `sync/scripts/run_sdr_telegram.bat`
- Delete: `sync/scripts/run_sdr_meeting_monitor.bat`
- Modify: `PROJECT_MASTER_CONTEXT.md`
- Create: `tests/test_sdr_reporting_schedule.py`

- [ ] **Step 1: Escribir pruebas de frecuencia y reuniones nuevas**

```python
def test_schedule_has_only_hourly_cuts_and_close():
    assert scheduled_cuts(date(2026, 9, 25)) == [time(h) for h in range(12, 21)]

def test_new_meetings_compare_previous_snapshot():
    assert new_meeting_ids({"a", "b"}, {"b", "c"}) == {"c"}
```

- [ ] **Step 2: Ejecutar y confirmar fallo**

Run: `python -m pytest tests/test_sdr_reporting_schedule.py -q`

Expected: FAIL por helpers ausentes.

- [ ] **Step 3: Integrar reuniones en el corte horario**

El servicio compara ids de citas del documento actual con el snapshot anterior;
incluye solo ids nuevos en `meetings.new` y el total en `meetings.today`. No
ejecuta un proceso independiente.

- [ ] **Step 4: Eliminar artefacto del monitor y actualizar documentación**

Eliminar `run_sdr_meeting_monitor.bat`. En `PROJECT_MASTER_CONTEXT.md`, reemplazar
la mención al monitor por reporte horario + consultas bajo demanda. Confirmar
con `Get-ScheduledTask` que `SDR_Telegram_Meeting_Monitor` no existe.

- [ ] **Step 5: Verificar y normalizar la tarea horaria de Windows**

La tarea `SDR_Telegram_Hourly` debe tener nueve triggers: 12:00–20:00, ejecutar
solo `run_sdr_telegram.bat`, ignorar instancias superpuestas y usar
`StartWhenAvailable`. No modificar `Reuniones_Dia_Telegram`, bots por cliente ni
sus scripts.

- [ ] **Step 6: Ejecutar pruebas**

Run: `python -m pytest tests/test_sdr_reporting_schedule.py tests/test_sdr_reporting_extended.py -q`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add PROJECT_MASTER_CONTEXT.md sync/scripts/sdr_reporting/cli.py sync/scripts/report_sdr_telegram.py sync/scripts/run_sdr_telegram.bat tests/test_sdr_reporting_schedule.py
git rm sync/scripts/run_sdr_meeting_monitor.bat
git commit -m "Consolidar equipo Alicia en frecuencia horaria"
```

### Task 9: Verificación real, muestra y activación

**Files:**
- Modify only if diagnostics require it: files from Tasks 1–8

- [ ] **Step 1: Ejecutar la suite enfocada completa**

Run: `python -m pytest tests/test_sdr_reporting_*.py tests/test_report_sdr_bot.py tests/test_client_mailboxes.py tests/test_telegram_ghl_bot.py -q`

Expected: todas las pruebas PASS.

- [ ] **Step 2: Ejecutar verificación estática y diff**

Run: `python -m compileall -q sync/scripts/sdr_reporting sync/scripts/report_sdr_bot.py sync/scripts/report_sdr_telegram.py sync/scripts/client_mailboxes.py sync/scripts/telegram_ghl_bot.py`

Run: `git diff --check`

Expected: exit code 0; solo advertencias CRLF permitidas.

- [ ] **Step 3: Generar reporte real sin Telegram**

Run (PowerShell): `$reportDay = Get-Date -Format 'yyyy-MM-dd'; python sync/scripts/report_sdr_telegram.py --operational --date $reportDay`

Expected: BAMBU TECH, GBS, BALIA y TOTAL; cada hora cerrada suma 60 minutos;
llamadas tienen cantidades/minutos; tareas de hoy no incluyen atrasadas; funnel
solo aparece en cierre; se genera PNG.

- [ ] **Step 4: Probar consultas reales sin enviar**

Ejecutar el controlador con:

```text
¿Cuántos minutos no ha trabajado hasta ahora?
¿Cuántos correos llegaron, cuántos respondió y cuáles faltan?
Llamadas y minutos por cliente de 11 a 12
¿Cuántas tareas de hoy y atrasadas hay?
¿A qué cliente llamó durante el bloque de GBS?
Mándame el gráfico de hoy
```

Expected: respuestas consistentes con el mismo documento operativo y `N/D`
cuando una fuente no existe.

- [ ] **Step 5: Mostrar en esta conversación la prueba real y el PNG**

No enviar el formato nuevo a Telegram hasta recibir aprobación explícita sobre
esa muestra real, cumpliendo la especificación aprobada.

- [ ] **Step 6: Verificar identidad y destinatario antes del primer envío**

Run: `python sync/scripts/report_sdr_telegram.py --operational --verify-bot`

Expected: `@equipo_alicia_bot verificado · destinatarios: 1`.

- [ ] **Step 7: Activar y probar el bot interactivo**

Reiniciar exclusivamente `SDR_Telegram_Bot`, enviar `Tiempo trabajado` desde el
chat autorizado y verificar respuesta + teclado. Enviar desde un chat no
autorizado en una prueba simulada; no debe consultar ni responder datos.

- [ ] **Step 8: Ejecutar suite general para detectar regresiones**

Run: `python -m pytest -q`

Expected: PASS, salvo fallos preexistentes documentados antes de comenzar. No
corregir archivos ajenos al alcance para ocultar fallos preexistentes.

- [ ] **Step 9: Commit final y publicación**

```bash
git add PROJECT_MASTER_CONTEXT.md sync/scripts tests
git commit -m "Activar consultas y reportes de equipo Alicia"
git push origin main
```

Verificar que `origin/main` apunta al commit final y que los cambios locales
ajenos permanecen intactos.
