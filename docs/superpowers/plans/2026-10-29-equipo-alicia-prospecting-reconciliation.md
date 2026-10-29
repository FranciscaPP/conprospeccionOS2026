# Equipo Alicia Prospecting Reconciliation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mostrar CON PROSPECCIÓN como unidad separada en todas las tablas del reporte, reconciliar el detalle por hora con los totales y entregar solo a las 09:00, 11:00, 13:00, 15:00, 17:00, 19:00 y 21:00 Chile de lunes a viernes.

**Architecture:** La subcuenta de Balia se divide por el usuario GHL de Nora (`assignedTo` en tareas, `userId` en mensajes/llamadas y `assignedUserId` en reuniones). Cada actividad normalizada conserva un `client` real; el desglose horario agrega esos clientes reales y nunca infiere actividad desde el bloque esperado. El gate cloud sigue despertando cada 15 minutos, pero solo acepta las siete horas de corte y mantiene una clave idempotente por hora.

**Tech Stack:** Python 3.12, Pillow, pytest, GoHighLevel API, GitHub Actions, Telegram Bot API.

---

### Task 1: Attribution rules and schedule gate

**Files:**
- Modify: `sync/scripts/sdr_reporting/config.py`
- Modify: `sync/scripts/sdr_reporting/cloud_schedule.py`
- Test: `tests/test_sdr_reporting_cloud_schedule.py`
- Test: `tests/test_sdr_reporting_hourly.py`

- [ ] **Step 1: Write failing schedule and attribution tests**

```python
def test_cloud_window_uses_seven_bihourly_chile_slots():
    monday = datetime(2026, 10, 5, tzinfo=CHILE)
    allowed = {9, 11, 13, 15, 17, 19, 21}
    assert [hour for hour in range(24) if is_report_window(monday.replace(hour=hour))] == sorted(allowed)

def test_user_id_identifies_conprospeccion():
    assert is_conprospeccion(CON_PROSPECCION_USER_ID)
    assert not is_conprospeccion("NC7mvmYoQQuKfINV1Mmp")
```

- [ ] **Step 2: Run tests and verify the old hourly gate fails**

Run: `python -m pytest tests/test_sdr_reporting_cloud_schedule.py tests/test_sdr_reporting_hourly.py -q`

Expected: the old 10:00–22:00 hourly assertions fail.

- [ ] **Step 3: Implement the exact Chile slots**

```python
REPORT_HOURS = frozenset({9, 11, 13, 15, 17, 19, 21})

def is_report_window(now=None):
    local = chile_now(now)
    return local.weekday() < 5 and local.hour in REPORT_HOURS
```

- [ ] **Step 4: Run the focused tests**

Run: `python -m pytest tests/test_sdr_reporting_cloud_schedule.py tests/test_sdr_reporting_hourly.py -q`

Expected: PASS.

### Task 2: Split Balia source records into Balia and CON PROSPECCIÓN

**Files:**
- Modify: `sync/scripts/sdr_reporting/service.py`
- Modify: `sync/scripts/sdr_reporting/sources.py`
- Test: `tests/test_sdr_reporting_service.py`

- [ ] **Step 1: Add failing source-attribution tests**

```python
def test_balia_tasks_split_by_assigned_to():
    balia, prospecting = split_balia_records([
        {"assigned_to": CON_PROSPECCION_USER_ID},
        {"assigned_to": "NC7mvmYoQQuKfINV1Mmp"},
    ], "assigned_to")
    assert len(balia) == 1
    assert len(prospecting) == 1

def test_balia_meeting_split_by_assigned_user_id():
    assert meeting_owner({"assigned_user_id": CON_PROSPECCION_USER_ID}) == "conprospeccion"
```

- [ ] **Step 2: Run the test and verify the split is absent**

Run: `python -m pytest tests/test_sdr_reporting_service.py -q`

Expected: FAIL because the helpers and complete Prospección metrics do not exist.

- [ ] **Step 3: Preserve attribution fields in adapters**

```python
def _task_adapter(task):
    return {
        # existing normalized fields
        "assigned_to": task.get("assignedTo"),
    }

def _meeting_user_id(event):
    return event.get("assignedUserId") or event.get("assignedTo") or event.get("userId")
```

- [ ] **Step 4: Build a full Prospección client record**

The `conprospeccion` record must contain tasks, calls, meetings, meetings scheduled today, email, WhatsApp availability, outside-hours calls and work time using the same field names as `clients[slug]`. Balia must exclude every record assigned to the Prospección user before its own totals are calculated.

- [ ] **Step 5: Run source and service tests**

Run: `python -m pytest tests/test_sdr_reporting_service.py tests/test_sdr_reporting_tasks.py -q`

Expected: PASS and no record appears in both Balia and Prospección.

### Task 3: Reconcile hour-by-hour activity with summary totals

**Files:**
- Modify: `sync/scripts/sdr_reporting/metrics.py`
- Modify: `sync/scripts/sdr_reporting/service.py`
- Test: `tests/test_sdr_reporting_hourly.py`

- [ ] **Step 1: Add a failing reconciliation test**

```python
def test_hourly_rows_attribute_real_clients_and_reconcile_calls():
    calls = [
        {**call(13, 5, "a", 90, 40), "client": "conprospeccion"},
        {**call(13, 20, "b", 30, 10), "client": "gbs"},
    ]
    rows = hourly_breakdown(DAY, at(14), work_blocks_for(DAY), calls, [], [])
    assert rows[0]["calls_by_client"] == {"conprospeccion": 1, "gbs": 1}
    assert sum(rows[0]["calls_by_client"].values()) == rows[0]["calls"]
```

- [ ] **Step 2: Run the test and verify the old expected-block attribution fails**

Run: `python -m pytest tests/test_sdr_reporting_hourly.py -q`

Expected: FAIL because the existing row only exposes the expected block client.

- [ ] **Step 3: Aggregate real client activity**

```python
calls_by_client = Counter(call["client"] for call in in_hour)
phone_seconds_by_client = Counter()
for call in in_hour:
    phone_seconds_by_client[call["client"]] += int(call.get("phone_seconds") or 0)
```

Keep idle time global and calculated once per hour. Do not duplicate it across client rows.

- [ ] **Step 4: Add invariants**

For each hourly row, assert calls and phone seconds equal the sum of their client breakdowns. For the complete document, assert hour-by-hour calls and minutes equal the in-jornada summary totals.

- [ ] **Step 5: Run hourly tests**

Run: `python -m pytest tests/test_sdr_reporting_hourly.py -q`

Expected: PASS.

### Task 4: Render all Prospección indicators, including zero rows

**Files:**
- Modify: `sync/scripts/sdr_reporting/tabular.py`
- Test: `tests/test_sdr_reporting_tabular.py`

- [ ] **Step 1: Add failing document tests**

```python
def test_prospecting_is_present_in_every_applicable_table_even_when_zero():
    document = build_table_document(sample_report_with_empty_prospecting())
    assert document["tasks"]["conprospeccion"]["total"] == 0
    assert any(row["client"] == "conprospeccion" for row in document["meetings"])
    assert document["scheduled"]["conprospeccion"]["count"] == 0
    assert document["calls_count"]["conprospeccion"]["today"] == 0
```

- [ ] **Step 2: Run and verify missing tables fail**

Run: `python -m pytest tests/test_sdr_reporting_tabular.py -q`

Expected: FAIL because only calls currently include Prospección.

- [ ] **Step 3: Use one complete display order**

```python
ORDER = ("bambutech", "gbs", "balia", "conprospeccion")
```

Use this order for meetings, scheduled meetings, tasks, calls, minutes, communications and outside-hours. The total row must include Prospección exactly once.

- [ ] **Step 4: Render actual hourly activity**

Replace the ambiguous `Bloque` value with `Actividad real`, formatted from `calls_by_client`, while leaving block adherence in its dedicated table.

- [ ] **Step 5: Run document and image tests**

Run: `python -m pytest tests/test_sdr_reporting_tabular.py tests/test_sdr_reporting_cli.py -q`

Expected: PASS; exactly two 1200 px PNG files are produced.

### Task 5: Verify live data, local fallback and cloud deployment

**Files:**
- Modify: `PROJECT_MASTER_CONTEXT.md`
- Modify: Windows task `SDR_Telegram_Hourly`

- [ ] **Step 1: Run the complete SDR suite**

Run: `python -m pytest tests/test_sdr_reporting_*.py tests/test_equipo_alicia_workflow.py -q`

Expected: PASS.

- [ ] **Step 2: Generate a live dry-run report**

Run: `python sync/scripts/report_sdr_telegram.py --operational`

Expected: two images; Prospección appears in tasks and both meeting tables even when zero.

- [ ] **Step 3: Reconcile live invariants**

Read the generated document and verify:

```python
assert sum(row["calls"] for row in document["hourly"]) == document["calls_count"]["total"]["today"]
assert sum(row["phone_seconds"] for row in document["hourly"]) == document["calls_minutes"]["total"]["today"]
```

- [ ] **Step 4: Update the local fallback triggers**

Configure `SDR_Telegram_Hourly` for weekdays at 09:00, 11:00, 13:00, 15:00, 17:00, 19:00 and 21:00 Chile.

- [ ] **Step 5: Commit and push only Equipo Alicia files**

```powershell
git add PROJECT_MASTER_CONTEXT.md .github/workflows/equipo-alicia-cloud.yml sync/scripts/sdr_reporting tests/test_sdr_reporting_*.py docs/superpowers
git commit -m "Fix Equipo Alicia prospecting attribution and schedule"
git push origin main
```

- [ ] **Step 6: Verify the deployed workflow**

Confirm the pushed revision is on `origin/main`, inspect the GitHub Actions result, and send one explicit live test only after all data invariants pass.
