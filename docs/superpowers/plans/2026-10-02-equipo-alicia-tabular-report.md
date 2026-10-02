# Equipo Alicia Tabular Report Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reemplazar el reporte horario de texto de `@equipo_alicia_bot` por dos imágenes PNG tabulares, con los cálculos aprobados para Nora y los tres clientes.

**Architecture:** Mantener `build_live_report()` como documento único de datos, ampliar sus métricas puras para separar jornada y fuera de horario, y añadir un renderizador PIL dedicado que traduzca ese documento en dos imágenes. `sdr_reporting.cli` enviará esas imágenes mediante el cliente restringido a `@equipo_alicia_bot`; las consultas conversacionales seguirán leyendo el mismo documento.

**Tech Stack:** Python 3.11+, Pillow, pytest, httpx, GHL API, Telegram Bot API.

---

### Task 1: Universos de tareas y franjas de llamadas

**Files:**
- Modify: `sync/scripts/sdr_reporting/models.py`
- Modify: `sync/scripts/sdr_reporting/metrics.py`
- Modify: `sync/scripts/sdr_reporting/service.py`
- Test: `tests/test_sdr_reporting_tasks.py`
- Test: `tests/test_sdr_reporting_activity.py`
- Test: `tests/test_sdr_reporting_work_time.py`

- [ ] **Step 1: Write failing task-progress tests**

Add assertions showing that progress uses the union of previous-day carryover and today:

```python
progress = task_progress(baseline, {"old-open", "today-done"})
assert progress.overdue_total == 1
assert progress.today_total == 2
assert progress.completed == 2
assert progress.total == 3
assert progress.pending == 1
assert progress.percent == 67
```

- [ ] **Step 2: Run the task test and verify the expected failure**

Run: `python -m pytest tests/test_sdr_reporting_tasks.py -q`

Expected: FAIL because `TaskProgress` does not yet expose the combined universe.

- [ ] **Step 3: Implement combined task progress**

Extend `TaskProgress` with `overdue_total`, combined `completed`, `total`, `pending`, and percentage properties. Update `task_progress()` so completed overdue tasks from today are counted in Avance while preserving today-only compatibility properties used by older reports.

- [ ] **Step 4: Run the task test and verify it passes**

Run: `python -m pytest tests/test_sdr_reporting_tasks.py -q`

Expected: all tests PASS.

- [ ] **Step 5: Write failing work-period tests**

Add tests for a pure `split_calls_by_period()` helper using calls at 10:30, 11:15, 16:15, 17:30, and 20:15 Chile. Assert the 11:15 and 17:30 calls are scheduled and the other calls are grouped under `before`, `lunch`, and `after`. Assert a weekend produces no scheduled calls.

- [ ] **Step 6: Run the activity tests and verify the expected failure**

Run: `python -m pytest tests/test_sdr_reporting_activity.py -q`

Expected: FAIL because `split_calls_by_period()` does not exist.

- [ ] **Step 7: Implement call-period splitting and service fields**

Add `split_calls_by_period(calls, day)` to `metrics.py`. In `service.py`, compute main call metrics only from scheduled calls and expose `outside_hours` with `before`, `lunch`, `after`, and `total`, each containing count and phone seconds. Keep adherence based on all calls so it can detect calls to other clients inside a block.

- [ ] **Step 8: Verify Task 1**

Run: `python -m pytest tests/test_sdr_reporting_tasks.py tests/test_sdr_reporting_activity.py tests/test_sdr_reporting_work_time.py -q`

Expected: all tests PASS.

### Task 2: Correos y WhatsApp por conversación

**Files:**
- Modify: `sync/scripts/sdr_reporting/sources.py`
- Modify: `sync/scripts/sdr_reporting/service.py`
- Modify: `sync/scripts/sdr_reporting/metrics.py`
- Test: `tests/test_sdr_reporting_sources.py`
- Test: `tests/test_sdr_reporting_work_time.py`

- [ ] **Step 1: Write failing two-day conversation tests**

Add tests for `summarize_conversation_work(messages, day, message_type)` covering: prior-day inbound still open at midnight, prior-day inbound answered before midnight, inbound today answered manually today, workflow output ignored, and one conversation receiving another inbound today without being counted twice.

Expected result shape:

```python
{
    "pending_previous": 1,
    "today": 1,
    "total": 2,
    "responded": 1,
    "unanswered": 1,
}
```

- [ ] **Step 2: Run source tests and verify the expected failure**

Run: `python -m pytest tests/test_sdr_reporting_sources.py -q`

Expected: FAIL because the two-day summarizer is missing.

- [ ] **Step 3: Implement the two-day summarizer**

Group by conversation ID, sort by `occurred_at`, ignore automated outbound messages, classify the open state at the start of the report day, and count each conversation once in the disjoint prior/today universe. Preserve the legacy summary helpers as wrappers for query compatibility.

- [ ] **Step 4: Update live collection and time formula**

Fetch activity from the beginning of the previous day through the cut, filter current-day calls separately, and calculate email and BAMBU TECH WhatsApp tables through the two-day summarizer. Emails are attempted for all three clients. GBS and BALIA WhatsApp remain `None`/`N/D`. Change work credit to exactly five minutes per responded email conversation and five minutes per responded WhatsApp conversation; remove the one-minute initial-WhatsApp credit from the new total.

- [ ] **Step 5: Verify Task 2**

Run: `python -m pytest tests/test_sdr_reporting_sources.py tests/test_sdr_reporting_work_time.py -q`

Expected: all tests PASS.

### Task 3: Renderizador de las dos tablas PNG

**Files:**
- Create: `sync/scripts/sdr_reporting/tabular.py`
- Create: `tests/test_sdr_reporting_tabular.py`

- [ ] **Step 1: Write failing table-data tests**

Create a representative report fixture and assert `build_table_document(report)` returns:

```python
assert document["tasks"]["total"] == {
    "overdue": 3, "today": 12, "total": 15,
    "completed": 9, "pending": 6, "percent": 60,
}
assert document["calls_count"]["total"]["today"] == 36
assert document["email"]["total"]["total"] == 30
assert document["outside"]["total"]["lunch"]["count"] == 2
```

Also assert unavailable WhatsApp values are rendered as `N/D` and the total is marked partial.

- [ ] **Step 2: Run the table-data test and verify the expected failure**

Run: `python -m pytest tests/test_sdr_reporting_tabular.py -q`

Expected: FAIL because `sdr_reporting.tabular` does not exist.

- [ ] **Step 3: Implement table-document normalization**

Create `build_table_document(report)` with rows for BAMBU TECH, GBS, BALIA, and TOTAL. Recalculate global percentages from totals, format task advance as count plus percentage, keep communication totals partial when a source is `N/D`, compute adherence result from correct/other calls, and format durations as `H h MM min`.

- [ ] **Step 4: Run the data tests and verify they pass**

Run: `python -m pytest tests/test_sdr_reporting_tabular.py -q`

Expected: table-document tests PASS.

- [ ] **Step 5: Write failing image-render tests**

Assert `render_tabular_report(report, tmp_path)` creates exactly two non-empty PNG files, each 1200 px wide, with distinct names ending in `_1.png` and `_2.png`.

- [ ] **Step 6: Run the image tests and verify the expected failure**

Run: `python -m pytest tests/test_sdr_reporting_tabular.py -q`

Expected: FAIL because the image renderer is missing.

- [ ] **Step 7: Implement the fixed-grid Pillow renderer**

Use reusable title, table, cell, and colored-client-label helpers. Image 1 renders meetings, tasks, call counts, call minutes, and phone-time summary. Image 2 renders email, WhatsApp, total worked/unworked, block adherence, and outside-hours tables. Use 1200 px width, centered numeric columns, fixed row heights, client colors from `CLIENTS`, gray TOTAL, green TOTAL TRABAJO, and yellow TOTAL SIN TRABAJAR.

- [ ] **Step 8: Verify Task 3**

Run: `python -m pytest tests/test_sdr_reporting_tabular.py -q`

Expected: all tests PASS and two PNGs are created.

### Task 4: Envío horario e integración exclusiva con Equipo Alicia

**Files:**
- Modify: `sync/scripts/sdr_reporting/cli.py`
- Modify: `sync/scripts/sdr_reporting/telegram.py`
- Modify: `tests/test_sdr_reporting_telegram.py`
- Create: `tests/test_sdr_reporting_cli.py`
- Modify: `PROJECT_MASTER_CONTEXT.md`

- [ ] **Step 1: Write failing Telegram and CLI tests**

Assert the sender uploads both images to the configured chat after verifying username `equipo_alicia_bot`. Mock `build_live_report()` and assert an hourly `--send` run sends no legacy multi-part text report and sends exactly two photos with captions `Reporte Nora · 1 de 2` and `Reporte Nora · 2 de 2`.

- [ ] **Step 2: Run integration tests and verify the expected failure**

Run: `python -m pytest tests/test_sdr_reporting_telegram.py tests/test_sdr_reporting_cli.py -q`

Expected: FAIL because the CLI still emits three text cards.

- [ ] **Step 3: Implement two-image sending**

Call `render_tabular_report()` from `cli.py`, print only the generated paths in dry-run mode, and upload only the two report images for the hourly cut. Preserve the separate weekly feature, bot identity check, single configured chat, snapshot persistence, and live-query document. Do not reference any client bot token or chat.

- [ ] **Step 4: Update the project source of truth**

Replace the outdated “tarjetas verticales” statement in `PROJECT_MASTER_CONTEXT.md` with the two-image tabular behavior, definitions of the official 11:00–20:00 schedule with 16:00–17:00 lunch, and the rule that outside-hours calls remain separate.

- [ ] **Step 5: Run the targeted suite**

Run: `python -m pytest tests/test_sdr_reporting_*.py tests/test_report_sdr_bot.py -q`

Expected: all tests PASS.

- [ ] **Step 6: Run repository safety checks**

Run: `python -m compileall -q sync/scripts/sdr_reporting sync/scripts/report_sdr_telegram.py sync/scripts/report_sdr_bot.py`

Run: `git diff --check`

Expected: both commands exit 0.

- [ ] **Step 7: Render and visually inspect a real dry run**

Run: `python sync/scripts/report_sdr_telegram.py --operational --date 2026-10-02`

Open both generated PNG files and verify every table is aligned, all three clients plus TOTAL are visible, no text overlaps, and the cut/SDR labels are correct.

- [ ] **Step 8: Verify and send the live report**

Run: `python sync/scripts/report_sdr_telegram.py --operational --verify-bot`

Expected: `@equipo_alicia_bot verificado · destinatarios: 1`.

Then run: `python sync/scripts/report_sdr_telegram.py --operational --send --date 2026-10-02`

Expected: exactly two report photos are acknowledged as sent to the single configured chat.

