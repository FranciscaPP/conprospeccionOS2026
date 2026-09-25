# Equipo Alicia Operational Bot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convertir `@equipo_alicia_bot` en el sistema operativo horario, diario y semanal de Nora para BAMBU TECH, GBS y BALIA, con métricas auditables e históricas.

**Architecture:** Los scripts existentes siguen siendo los puntos de entrada, pero consumen un paquete compartido `sdr_reporting` con configuración, recolectores, cálculos, persistencia y renderizado. Supabase conserva eventos, baseline y snapshots idempotentes; Telegram solo recibe documentos ya calculados y validados.

**Tech Stack:** Python 3.14, pytest, httpx, Pillow, Supabase/PostgREST, GoHighLevel API, Telegram Bot API HTML.

---

## Estructura de archivos

- Crear `sync/scripts/sdr_reporting/config.py`: clientes, colores y horario.
- Crear `sync/scripts/sdr_reporting/models.py`: estructuras canónicas.
- Crear `sync/scripts/sdr_reporting/metrics.py`: funciones puras de cálculo.
- Crear `sync/scripts/sdr_reporting/render.py`: mensajes HTML.
- Crear `sync/scripts/sdr_reporting/charts.py`: PNG diario/semanal.
- Crear `sync/scripts/sdr_reporting/storage.py`: persistencia Supabase.
- Crear `sync/scripts/sdr_reporting/service.py`: orquestación de fuentes.
- Crear `sync/scripts/sdr_reporting/telegram.py`: envío exclusivo y verificación de identidad.
- Modificar `report_calls_live.py`: conservar ids/timestamps necesarios.
- Modificar `report_tareas.py`: exponer baseline sin cambiar categorías existentes.
- Modificar `report_sdr_telegram.py`: convertirlo en CLI del servicio.
- Modificar `report_sdr_bot.py`: consultas al mismo servicio.
- Modificar `run_sdr_telegram.bat` y `run_sdr_bot.bat`: ejecutar los puntos de entrada correctos sin `--solo`.
- Crear migración `sync/supabase/migrations/028_sdr_operational_reporting.sql`.
- Crear pruebas `tests/test_sdr_reporting_*.py`.

### Task 1: Configuración canónica y guardia del bot

**Files:**
- Create: `sync/scripts/sdr_reporting/__init__.py`
- Create: `sync/scripts/sdr_reporting/config.py`
- Create: `sync/scripts/sdr_reporting/telegram.py`
- Test: `tests/test_sdr_reporting_config.py`
- Test: `tests/test_sdr_reporting_telegram.py`

- [ ] **Step 1: Escribir pruebas fallidas de clientes, bloques y almuerzo**

```python
from datetime import date, datetime
from zoneinfo import ZoneInfo
from sdr_reporting.config import CLIENTS, work_blocks_for, client_at

def test_three_clients_and_official_colors():
    assert CLIENTS["bambutech"].color == "#22C55E"
    assert CLIENTS["gbs"].color == "#8B5CF6"
    assert CLIENTS["balia"].color == "#EC4899"

def test_official_chile_schedule_excludes_lunch():
    blocks = work_blocks_for(date(2026, 9, 24))
    assert [(b.start.hour, b.end.hour, b.client) for b in blocks] == [
        (11, 12, "balia"), (12, 13, "gbs"), (13, 16, "bambutech"),
        (17, 18, "gbs"), (18, 20, "bambutech"),
    ]
    dt = datetime(2026, 9, 24, 16, 30, tzinfo=ZoneInfo("America/Santiago"))
    assert client_at(dt) is None
```

- [ ] **Step 2: Ejecutar y confirmar RED**

Run: `pytest tests/test_sdr_reporting_config.py -q`
Expected: FAIL por `ModuleNotFoundError: sdr_reporting`.

- [ ] **Step 3: Implementar configuración mínima**

```python
@dataclass(frozen=True)
class ClientConfig:
    slug: str; name: str; short: str; emoji: str; color: str

@dataclass(frozen=True)
class WorkBlock:
    start: datetime; end: datetime; client: str

CLIENTS = {
    "bambutech": ClientConfig("bambutech", "BAMBU TECH", "BAM", "🟩", "#22C55E"),
    "gbs": ClientConfig("gbs", "GBS", "GBS", "🟪", "#8B5CF6"),
    "balia": ClientConfig("balia", "BALIA", "BAL", "🩷", "#EC4899"),
}
```

- [ ] **Step 4: Escribir prueba fallida de identidad y destinatario único**

```python
def test_sender_rejects_wrong_bot(monkeypatch):
    sender = EquipoAliciaTelegram("token", "123", transport=FakeTransport(username="otro_bot"))
    with pytest.raises(RuntimeError, match="equipo_alicia_bot"):
        sender.verify_identity()
```

- [ ] **Step 5: Implementar `EquipoAliciaTelegram`**

Debe leer exclusivamente `TELEGRAM_SDR_TOKEN` y `TELEGRAM_SDR_CHAT_ID`, llamar
`getMe`, exigir `username == "equipo_alicia_bot"`, enviar con
`parse_mode="HTML"` y no consultar variables `TELEGRAM_REUNIONES_*` ni
`TELEGRAM_BOT_*`.

- [ ] **Step 6: Ejecutar pruebas**

Run: `pytest tests/test_sdr_reporting_config.py tests/test_sdr_reporting_telegram.py -q`
Expected: PASS.

- [ ] **Step 7: Commit**

```powershell
git add sync/scripts/sdr_reporting tests/test_sdr_reporting_config.py tests/test_sdr_reporting_telegram.py
git commit -m "Agregar configuración segura de equipo Alicia bot"
```

### Task 2: Modelo de datos y cálculos de tareas

**Files:**
- Create: `sync/scripts/sdr_reporting/models.py`
- Create: `sync/scripts/sdr_reporting/metrics.py`
- Modify: `sync/scripts/report_tareas.py`
- Test: `tests/test_sdr_reporting_tasks.py`

- [ ] **Step 1: Escribir pruebas fallidas de baseline y arrastre**

```python
def test_baseline_separates_overdue_from_due_today():
    baseline = build_task_baseline(TASKS, date(2026, 9, 24), captured_at=CUT)
    assert baseline.due_today_ids == {"today-open", "today-done"}
    assert baseline.overdue_ids == {"old-open"}
    assert baseline.total == 3

def test_progress_keeps_original_denominator():
    progress = task_progress(BASELINE, completed_ids={"old-open", "today-done"})
    assert progress.completed == 2
    assert progress.pending_today == 1
    assert progress.pending_overdue == 0
```

- [ ] **Step 2: Confirmar RED**

Run: `pytest tests/test_sdr_reporting_tasks.py -q`
Expected: FAIL por funciones ausentes.

- [ ] **Step 3: Implementar dataclasses y funciones puras**

```python
@dataclass(frozen=True)
class TaskBaseline:
    day: date
    client: str
    due_today_ids: frozenset[str]
    overdue_ids: frozenset[str]
    task_types: dict[str, str]

def task_progress(baseline, completed_ids):
    scope = baseline.due_today_ids | baseline.overdue_ids
    done = scope & set(completed_ids)
    return TaskProgress(len(done), len(scope),
        len(baseline.due_today_ids - done), len(baseline.overdue_ids - done))
```

- [ ] **Step 4: Reutilizar `fetch_tasks` y `tipo_de`**

Agregar un adaptador que conserve `_id`, timestamps y clasificación; no filtrar
por `assignedTo`, pues la decisión confirmada atribuye todos los registros a
Nora.

- [ ] **Step 5: Probar rezago y volumen**

Agregar pruebas donde una categoría de una sola tarea al 0% no sea elegible
para mayor rezago y otra con mayor número absoluto sea mayor volumen.

- [ ] **Step 6: Ejecutar pruebas y commit**

Run: `pytest tests/test_sdr_reporting_tasks.py tests/test_seguimiento_helpers.py -q`
Expected: PASS.

```powershell
git add sync/scripts/sdr_reporting/models.py sync/scripts/sdr_reporting/metrics.py sync/scripts/report_tareas.py tests/test_sdr_reporting_tasks.py
git commit -m "Calcular meta diaria y arrastre de Nora"
```

### Task 3: Llamadas, actividad, adherencia y huecos

**Files:**
- Modify: `sync/scripts/report_calls_live.py`
- Modify: `sync/scripts/sdr_reporting/models.py`
- Modify: `sync/scripts/sdr_reporting/metrics.py`
- Test: `tests/test_sdr_reporting_activity.py`

- [ ] **Step 1: Escribir pruebas fallidas de deduplicación y duraciones**

```python
def test_calls_count_unique_contacts_separately():
    m = call_metrics([CALL_A, CALL_A_REPEAT_CONTACT, CALL_B])
    assert m.calls == 3
    assert m.unique_contacts == 2
    assert m.repeated_contacts == 1

def test_completed_is_answered_and_20s_is_only_conversation_fallback():
    m = call_metrics([completed_call(8), completed_call(30), no_answer_call(40)])
    assert m.answered == 2
    assert m.relevant_conversations == 1
    assert m.conversation_seconds == 38
```

- [ ] **Step 2: Confirmar RED e implementar ids de llamada**

Run: `pytest tests/test_sdr_reporting_activity.py -q`
Expected: FAIL.

`fetch_calls` debe devolver `id`, `date_added`, `date_updated`, `user_id` y los
campos actuales. No se cambia `call_duration`.

- [ ] **Step 3: Escribir pruebas fallidas de huecos**

```python
def test_gap_detection_only_inside_client_block_and_at_least_20_minutes():
    gaps = operational_gaps(BALIA_BLOCK, [event_at("11:05"), event_at("11:14"), event_at("11:40")], NOW_12)
    assert [(g.start.strftime("%H:%M"), g.end.strftime("%H:%M")) for g in gaps] == [("11:14", "11:40")]

def test_lunch_never_creates_gap():
    assert operational_gaps(None, [], datetime_at("16:45")) == []
```

- [ ] **Step 4: Implementar unión de intervalos y huecos**

Las llamadas usan intervalo real `inicio..fin_estimado`; eventos instantáneos
cortan huecos sin sumar minutos. `registered_activity_seconds` suma solo
intervalos con duración conocida.

- [ ] **Step 5: Escribir e implementar pruebas de adherencia**

Comprobar actividad dentro/fuera, teléfono dentro/fuera y porcentaje del
bloque transcurrido. Ningún porcentaje debe exceder 100.

- [ ] **Step 6: Ejecutar suite y commit**

Run: `pytest tests/test_sdr_reporting_activity.py tests/test_telegram_ghl_bot.py -q`
Expected: PASS.

```powershell
git add sync/scripts/report_calls_live.py sync/scripts/sdr_reporting tests/test_sdr_reporting_activity.py
git commit -m "Medir llamadas adherencia y huecos operativos"
```

### Task 4: Persistencia histórica y comparación

**Files:**
- Create: `sync/supabase/migrations/028_sdr_operational_reporting.sql`
- Create: `sync/scripts/sdr_reporting/storage.py`
- Test: `tests/test_sdr_reporting_storage.py`

- [ ] **Step 1: Escribir prueba fallida de upsert idempotente**

```python
def test_hourly_snapshot_upsert_uses_day_cut_scope_key():
    store.save_snapshot(SNAPSHOT)
    assert fake.upsert_args["on_conflict"] == "snapshot_date,cut_at,scope"
```

- [ ] **Step 2: Confirmar RED**

Run: `pytest tests/test_sdr_reporting_storage.py -q`
Expected: FAIL.

- [ ] **Step 3: Crear migración aditiva**

```sql
create table if not exists public.sdr_activity_events (
  id uuid primary key default gen_random_uuid(), source text not null,
  source_id text not null, cliente_slug text not null, contact_id text,
  event_type text not null, occurred_at timestamptz not null,
  duration_seconds integer, metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique(source, source_id, cliente_slug)
);
create table if not exists public.sdr_daily_baselines (
  baseline_date date not null, cliente_slug text not null,
  captured_at timestamptz not null, payload jsonb not null,
  primary key(baseline_date, cliente_slug)
);
create table if not exists public.sdr_hourly_snapshots (
  snapshot_date date not null, cut_at time not null, scope text not null,
  schema_version integer not null default 1, payload jsonb not null,
  created_at timestamptz not null default now(),
  primary key(snapshot_date, cut_at, scope)
);
create table if not exists public.sdr_alert_state (
  alert_key text primary key, fingerprint text not null,
  severity text not null, last_sent_at timestamptz not null,
  metadata jsonb not null default '{}'::jsonb
);
```

- [ ] **Step 4: Implementar almacenamiento y lectura same-hour**

`load_comparison(day, cut)` debe buscar exactamente `day - 1` y el mismo
`cut_at`; si falta devuelve `None`, nunca el cierre.

- [ ] **Step 5: Ejecutar pruebas y commit**

Run: `pytest tests/test_sdr_reporting_storage.py -q`
Expected: PASS.

```powershell
git add sync/supabase/migrations/028_sdr_operational_reporting.sql sync/scripts/sdr_reporting/storage.py tests/test_sdr_reporting_storage.py
git commit -m "Persistir snapshots operativos horarios"
```

### Task 5: Render HTML de los tres mensajes

**Files:**
- Create: `sync/scripts/sdr_reporting/render.py`
- Test: `tests/test_sdr_reporting_render.py`

- [ ] **Step 1: Escribir pruebas fallidas de estructura y escape**

```python
def test_hourly_report_is_at_most_three_html_messages_in_order():
    messages = render_hourly(REPORT)
    assert len(messages) <= 3
    joined = "\n".join(messages)
    positions = [joined.index(f"{i:02d} ·") for i in range(1, 11)]
    assert positions == sorted(positions)
    assert all(len(m) <= 4096 for m in messages)

def test_dynamic_values_are_html_escaped():
    assert "A &amp; B" in "\n".join(render_hourly(report_with_company("A & B")))
```

- [ ] **Step 2: Confirmar RED e implementar tablas compactas**

Run: `pytest tests/test_sdr_reporting_render.py -q`
Expected: FAIL.

Crear utilidades `html_text`, `pre_table`, `split_sections` y renderizadores de
los tres mensajes en el orden de la especificación.

- [ ] **Step 3: Probar semáforos y alertas**

Agregar casos de cierre 90/75/60/<60 y de reporte intradía que usa brecha
contra bloque transcurrido. Limitar alertas accionables a tres y suprimir una
huella sin cambios mediante `sdr_alert_state`.

- [ ] **Step 4: Ejecutar pruebas y commit**

Run: `pytest tests/test_sdr_reporting_render.py -q`
Expected: PASS.

```powershell
git add sync/scripts/sdr_reporting/render.py tests/test_sdr_reporting_render.py
git commit -m "Renderizar reporte operativo HTML de Telegram"
```

### Task 6: Reuniones nuevas, funnel y email manual

**Files:**
- Create: `sync/scripts/sdr_reporting/service.py`
- Modify: `sync/scripts/sync_snov_replies_to_ghl.py`
- Test: `tests/test_sdr_reporting_sources.py`

- [ ] **Step 1: Escribir prueba fallida de reuniones idempotentes**

```python
def test_new_meeting_alert_emitted_once_and_has_no_outcome_fields():
    first = service.detect_new_meetings([APPOINTMENT])
    second = service.detect_new_meetings([APPOINTMENT])
    assert len(first) == 1 and second == []
    text = render_meeting_alert(first[0])
    assert "NUEVA REUNIÓN" in text
    assert "no show" not in text.lower() and "válida" not in text.lower()
```

- [ ] **Step 2: Confirmar RED e implementar calendario GHL**

Run: `pytest tests/test_sdr_reporting_sources.py -q`
Expected: FAIL.

Reutilizar `list_calendars` y `list_calendar_events`; deduplicar por appointment
id y enriquecer con contacto solo cuando exista.

- [ ] **Step 3: Probar transiciones completas de funnel**

Guardar estado anterior por contacto y emitir `old -> new` solo ante cambio.
No derivar transición desde un único estado actual.

- [ ] **Step 4: Probar email manual verificable**

Los eventos Snov `reply` cuentan como recibidos, no como emails manuales
enviados. Un mensaje GHL solo cuenta como manual si posee autor/tipo confiable;
sin esa marca el KPI queda `None`.

- [ ] **Step 5: Ejecutar pruebas y commit**

Run: `pytest tests/test_sdr_reporting_sources.py tests/test_snov_ghl_matching.py -q`
Expected: PASS.

```powershell
git add sync/scripts/sdr_reporting/service.py sync/scripts/sync_snov_replies_to_ghl.py tests/test_sdr_reporting_sources.py
git commit -m "Agregar reuniones funnel y email verificable"
```

### Task 7: Cierre, gráficos y semanal

**Files:**
- Create: `sync/scripts/sdr_reporting/charts.py`
- Test: `tests/test_sdr_reporting_charts.py`

- [ ] **Step 1: Escribir pruebas fallidas de paleta**

```python
def test_daily_and_weekly_charts_use_official_palette():
    daily = render_daily_timeline(DAY_DATA)
    weekly = render_weekly_gaps(WEEK_DATA)
    for png in (daily, weekly):
        assert png.startswith(b"\x89PNG")
    assert chart_palette()["bambutech"] == "#22C55E"
    assert chart_palette()["gap"] == "#DC2626"
```

- [ ] **Step 2: Confirmar RED e implementar PNG**

Run: `pytest tests/test_sdr_reporting_charts.py -q`
Expected: FAIL.

Usar Pillow ya empleado por el script actual. Implementar timeline diario,
barras apiladas de huecos, cumplimiento y adherencia semanal.

- [ ] **Step 3: Probar agregación semanal**

Comprobar que suma cierres diarios una vez, detecta huecos por franja repetida
en al menos tres días y calcula industrias/cargos desde reuniones agendadas.

- [ ] **Step 4: Ejecutar pruebas y commit**

Run: `pytest tests/test_sdr_reporting_charts.py -q`
Expected: PASS.

```powershell
git add sync/scripts/sdr_reporting/charts.py tests/test_sdr_reporting_charts.py
git commit -m "Generar cierres y gráficos semanales"
```

### Task 8: Integración, ejecución en seco y primer envío

**Files:**
- Modify: `sync/scripts/report_sdr_telegram.py`
- Modify: `sync/scripts/report_sdr_bot.py`
- Modify: `sync/scripts/run_sdr_telegram.bat`
- Modify: `sync/scripts/run_sdr_bot.bat`
- Test: `tests/test_sdr_reporting_cli.py`

- [ ] **Step 1: Escribir prueba fallida del CLI**

```python
def test_dry_run_builds_three_clients_without_network_send(runner):
    result = runner.invoke(main, ["--dry-run", "--date", "2026-09-24"])
    assert result.exit_code == 0
    assert all(name in result.output for name in ("BAMBU TECH", "GBS", "BALIA", "TOTAL"))
    assert "Norma" not in result.output
```

- [ ] **Step 2: Confirmar RED e integrar servicio**

Run: `pytest tests/test_sdr_reporting_cli.py -q`
Expected: FAIL.

El CLI aceptará `--dry-run`, `--baseline`, `--hourly`, `--close`, `--weekly` y
`--monitor-meetings`. El modo predeterminado elige la operación por hora Chile.

- [ ] **Step 3: Corregir lanzadores**

Eliminar `--solo bambutech` de `run_sdr_telegram.bat`. Mantener los dos
lanzadores apuntando exclusivamente a `report_sdr_telegram.py` y
`report_sdr_bot.py`.

- [ ] **Step 4: Ejecutar suite completa**

Run: `pytest -q`
Expected: PASS sin errores ni warnings nuevos.

- [ ] **Step 5: Validar reporte real sin enviar**

Run: `python sync/scripts/report_sdr_telegram.py --dry-run --hourly`
Expected: tres clientes + TOTAL, máximo tres mensajes, sin resultados
posteriores de reuniones y sin datos inventados.

- [ ] **Step 6: Verificar identidad y destinatario**

Run: `python sync/scripts/report_sdr_telegram.py --verify-bot`
Expected: `@equipo_alicia_bot` y un solo chat de destino
`TELEGRAM_SDR_CHAT_ID`.

- [ ] **Step 7: Enviar exclusivamente al chat principal**

Run: `python sync/scripts/report_sdr_telegram.py --hourly --send`
Expected: envío exitoso al chat principal; ningún uso de
`TELEGRAM_SDR_CHAT_ID_NORA`, `TELEGRAM_REUNIONES_*` o `TELEGRAM_BOT_*`.

- [ ] **Step 8: Commit final**

```powershell
git add sync/scripts/report_sdr_telegram.py sync/scripts/report_sdr_bot.py sync/scripts/run_sdr_telegram.bat sync/scripts/run_sdr_bot.bat tests/test_sdr_reporting_cli.py
git commit -m "Activar reporte operativo en equipo Alicia bot"
```

## Verificación final

- [ ] `git diff --check` sin errores.
- [ ] `pytest -q` completo en verde.
- [ ] `getMe` confirma `equipo_alicia_bot`.
- [ ] El reporte de prueba usa solo el chat principal.
- [ ] `git diff` no contiene cambios en `report_reuniones_dia.py`,
  `telegram_ghl_bot.py`, `telegram_ghl_cards.py` ni configuraciones de bots por
  cliente.
- [ ] El primer envío real fue recibido por la usuaria y no por Nora.

