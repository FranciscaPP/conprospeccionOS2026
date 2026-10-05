# Equipo Alicia Cloud Automation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ejecutar los reportes de `@equipo_alicia_bot` en GitHub de 10:00 a 22:00 Chile, lunes a viernes, y responder consultas 24/7 mediante un webhook de Supabase, sin depender del PC.

**Architecture:** El código Python existente sigue siendo la única implementación de métricas y renderizado. Supabase almacena locks de entregas y una cola de consultas; una Edge Function recibe Telegram y dispara un workflow dedicado de GitHub, que ejecuta el reporte o una consulta individual y responde por el mismo bot privado.

**Tech Stack:** Python 3.12, pytest, GitHub Actions, Supabase PostgreSQL/Edge Functions (Deno TypeScript), Telegram Bot API, GHL API.

---

### Task 1: Persistencia cloud e idempotencia

**Files:**
- Create: `sync/supabase/migrations/029_equipo_alicia_cloud.sql`
- Create: `sync/scripts/sdr_reporting/cloud_state.py`
- Create: `tests/test_sdr_reporting_cloud_state.py`
- Modify: `sync/scripts/supabase_rest.py`

- [ ] **Step 1: Write failing tests for delivery and query state**

Create a fake Supabase client and tests for these public methods:

```python
store = CloudStateStore(fake)
assert store.claim_delivery("hourly:2026-10-05:10:America/Santiago") is True
assert store.claim_delivery("hourly:2026-10-05:10:America/Santiago") is False
store.mark_delivery_part(key, 1)
store.mark_delivery_sent(key)

query = store.claim_query(12345)
assert query["text"] == "tareas de Balia"
store.mark_query_answered(12345)
```

Also verify a stale `processing` delivery can be reclaimed once and a `sent`
delivery can never be reclaimed.

- [ ] **Step 2: Run tests and verify RED**

Run: `python -m pytest tests/test_sdr_reporting_cloud_state.py -q`

Expected: FAIL because `sdr_reporting.cloud_state` does not exist.

- [ ] **Step 3: Add the database migration**

Create `sdr_report_deliveries` with unique `delivery_key`, status, attempt count,
`part1_sent_at`, `part2_sent_at`, timestamps, and error summary. Create
`sdr_bot_queries` with unique Telegram `update_id`, authorized `chat_id`, text,
status, attempt count, timestamps, and error summary. Enable RLS and expose no
anon/authenticated policies; access is service-role only.

- [ ] **Step 4: Implement atomic REST operations**

Extend `SupabaseRestClient` with explicit `update()` and conflict-aware
`insert_returning()` methods. Implement `CloudStateStore` using insert-on-unique
for first claims and compare-and-update for retryable failed/stale rows. Store
only short exception class/message summaries.

- [ ] **Step 5: Run tests and verify GREEN**

Run: `python -m pytest tests/test_sdr_reporting_cloud_state.py -q`

Expected: all tests PASS.

### Task 2: Gate horario y envío cloud recuperable

**Files:**
- Create: `sync/scripts/sdr_reporting/cloud_schedule.py`
- Modify: `sync/scripts/sdr_reporting/cli.py`
- Modify: `sync/scripts/sdr_reporting/telegram.py`
- Create: `tests/test_sdr_reporting_cloud_schedule.py`
- Modify: `tests/test_sdr_reporting_cli.py`
- Modify: `tests/test_sdr_reporting_telegram.py`

- [ ] **Step 1: Write failing schedule tests**

Test `delivery_key_for(now)` and `is_report_window(now)` at Monday 09:59,
10:00, 22:59, 23:00, Saturday 12:00, and across both Chile UTC offsets.

```python
assert is_report_window(monday_10_chile) is True
assert delivery_key_for(monday_10_chile) == "hourly:2026-10-05:10:America/Santiago"
assert is_report_window(saturday_noon_chile) is False
```

- [ ] **Step 2: Run schedule tests and verify RED**

Run: `python -m pytest tests/test_sdr_reporting_cloud_schedule.py -q`

Expected: FAIL because the module is missing.

- [ ] **Step 3: Implement the Chile gate**

Implement the gate with `ZoneInfo("America/Santiago")`; never hard-code UTC.
Return false outside weekdays and outside hour 10 through 22 inclusive.

- [ ] **Step 4: Write failing resumable-delivery tests**

Mock image generation, Telegram, and `CloudStateStore`. Assert a fresh key sends
both images; an already-sent key sends none; and a retry with part 1 recorded
sends only part 2.

- [ ] **Step 5: Run CLI tests and verify RED**

Run: `python -m pytest tests/test_sdr_reporting_cli.py tests/test_sdr_reporting_telegram.py -q`

Expected: FAIL because cloud delivery is not connected.

- [ ] **Step 6: Implement `--cloud-scheduled`**

Add a CLI flag that checks the Chile gate, claims the delivery, builds the live
report, sends missing image parts, records each Telegram confirmation, and marks
the delivery `sent`. On failure mark `failed` and return a non-zero exit code.
Keep the existing local and manual modes compatible.

- [ ] **Step 7: Verify Task 2**

Run: `python -m pytest tests/test_sdr_reporting_cloud_schedule.py tests/test_sdr_reporting_cli.py tests/test_sdr_reporting_telegram.py -q`

Expected: all tests PASS.

### Task 3: Consultas individuales desde la cola

**Files:**
- Modify: `sync/scripts/report_sdr_bot.py`
- Modify: `tests/test_report_sdr_bot.py`

- [ ] **Step 1: Write failing one-shot query tests**

Test `process_queued_query(update_id, store, sender)` with an authorized queued
row, a duplicate answered row, and a query exception. Assert the normal path
uses `parse_query()`, `query_operational()`, sends every returned message, and
marks the row `answered` exactly once.

- [ ] **Step 2: Run tests and verify RED**

Run: `python -m pytest tests/test_report_sdr_bot.py -q`

Expected: FAIL because queued-query processing is missing.

- [ ] **Step 3: Implement `--cloud-update-id`**

Add an argparse entry point. It loads the row by numeric `update_id`, verifies
its chat matches `TELEGRAM_SDR_CHAT_ID`, claims it, generates the existing live
query response, sends via `EquipoAliciaTelegram`, and marks the row answered.
Keep long polling available only for local fallback.

- [ ] **Step 4: Run query tests and verify GREEN**

Run: `python -m pytest tests/test_report_sdr_bot.py -q`

Expected: all tests PASS.

### Task 4: Telegram webhook en Supabase

**Files:**
- Create: `supabase/functions/equipo-alicia-webhook/index.ts`
- Create: `supabase/functions/equipo-alicia-webhook/handler.ts`
- Create: `supabase/functions/equipo-alicia-webhook/handler_test.ts`

- [ ] **Step 1: Write failing Deno handler tests**

Test pure `handleTelegramUpdate()` dependencies for: wrong method, wrong secret,
unauthorized chat, non-text update, first authorized update, and duplicate
`update_id`. The accepted case inserts `queued` and dispatches only the numeric
ID to GitHub.

- [ ] **Step 2: Run tests and verify RED**

Run: `deno test supabase/functions/equipo-alicia-webhook/handler_test.ts`

Expected: FAIL because the handler is missing. If Deno is unavailable locally,
load the repository's approved runtime or run this test in the GitHub validation
job before deployment; deployment cannot proceed until it passes there.

- [ ] **Step 3: Implement the webhook handler**

Validate `x-telegram-bot-api-secret-token` using constant-time comparison,
require the configured chat, insert `sdr_bot_queries` with unique `update_id`,
and call GitHub's workflow dispatch endpoint with only `update_id`. Return 200
for accepted, duplicate, ignored, and unauthorized Telegram updates so Telegram
does not retry them; return 500 only when an authorized new update could not be
queued or dispatched.

- [ ] **Step 4: Implement the Edge Function entrypoint**

Read only `TELEGRAM_SDR_CHAT_ID`, `TELEGRAM_WEBHOOK_SECRET`,
`GITHUB_REPOSITORY`, `GITHUB_WORKFLOW_TOKEN`, `SUPABASE_URL`, and
`SUPABASE_SERVICE_ROLE_KEY`; do not log their values or message text.

- [ ] **Step 5: Run handler tests and verify GREEN**

Run: `deno test supabase/functions/equipo-alicia-webhook/handler_test.ts`

Expected: all tests PASS.

### Task 5: Workflow dedicado de GitHub

**Files:**
- Create: `.github/workflows/equipo-alicia-cloud.yml`
- Create: `tests/test_equipo_alicia_workflow.py`
- Modify: `sync/requirements.txt`

- [ ] **Step 1: Write failing workflow-contract tests**

Parse the YAML as text and assert it contains the 15-minute cron, manual
`update_id` input, Python 3.12 setup, required secret mapping, report command,
query command, timeout, and concurrency. Assert it never references
`TELEGRAM_REUNIONES_*` or `TELEGRAM_BOT_*`.

- [ ] **Step 2: Run test and verify RED**

Run: `python -m pytest tests/test_equipo_alicia_workflow.py -q`

Expected: FAIL because the workflow is missing.

- [ ] **Step 3: Implement the workflow**

Use `cron: "*/15 * * * *"` plus `workflow_dispatch.inputs.update_id`. Checkout,
setup Python, install `sync/requirements.txt`, validate secrets, then run exactly
one mode:

```text
python sync/scripts/report_sdr_telegram.py --operational --cloud-scheduled --send
python sync/scripts/report_sdr_bot.py --cloud-update-id <numeric id>
```

Set finite timeouts and least-privilege workflow permissions.

- [ ] **Step 4: Run workflow tests and verify GREEN**

Run: `python -m pytest tests/test_equipo_alicia_workflow.py -q`

Expected: all tests PASS.

### Task 6: Documentation and complete verification

**Files:**
- Modify: `PROJECT_MASTER_CONTEXT.md`
- Modify: `docs/superpowers/specs/2026-10-05-equipo-alicia-cloud-automation-design.md` only if implementation reveals an approved factual correction

- [ ] **Step 1: Update the single source of truth**

Document GitHub/Supabase ownership, 10:00–22:00 Chile weekday reporting,
24/7 query webhook, idempotency tables, and the rule that Windows jobs remain
disabled after cloud cutover.

- [ ] **Step 2: Run the targeted suite**

Run: `$tests = (Get-ChildItem tests -Filter 'test_sdr_reporting_*.py').FullName; python -m pytest @tests tests/test_report_sdr_bot.py tests/test_equipo_alicia_workflow.py -q`

Expected: all targeted tests PASS.

- [ ] **Step 3: Run the complete repository suite**

Run: `python -m pytest tests -q`

Expected: all tests PASS.

- [ ] **Step 4: Run safety checks**

Run: `python -m compileall -q sync/scripts/sdr_reporting sync/scripts/report_sdr_telegram.py sync/scripts/report_sdr_bot.py`

Run: `git diff --check`

Expected: both commands exit 0.

### Task 7: Cloud deployment and safe cutover

**Files:**
- No new versioned files unless a verified deployment correction is required.

- [ ] **Step 1: Authenticate deployment surfaces**

Use the existing authenticated GitHub/Supabase browser sessions. If either asks
for login, 2FA, organization approval, or creation of a fine-grained token,
pause for Francisca to complete that protected step; never request secret values
in chat.

- [ ] **Step 2: Apply migration and configure secrets**

Apply migration 029 to the linked Supabase project. Configure the GitHub and
Supabase secret names listed in the approved spec. Verify names/presence only,
never values.

- [ ] **Step 3: Deploy and test the Edge Function**

Deploy `equipo-alicia-webhook`, register Telegram `setWebhook` with the secret
header, then verify Telegram `getWebhookInfo` reports the expected HTTPS URL and
no pending error.

- [ ] **Step 4: Push the implementation and run cloud dry verification**

Push `main`, dispatch the workflow in report mode, and verify the job reaches
GHL, renders both PNGs, and uses only the private chat. Do not count a green job
that skipped for missing secrets as success.

- [ ] **Step 5: Verify real cloud delivery and query**

Send one cloud report with a unique delivery key and confirm two Telegram image
message IDs. Send one real question to `@equipo_alicia_bot`, verify one queued
row, one GitHub dispatch, one response, and final status `answered`.

- [ ] **Step 6: Verify duplicate protection**

Dispatch the same report key and same `update_id` again. Confirm Telegram
receives no additional report images and no second query answer.

- [ ] **Step 7: Disable Windows only after cloud proof**

Disable `SDR_Telegram_Hourly` and stop/disable `SDR_Telegram_Bot`. Re-read both
task states as `Disabled`. Keep their definitions for manual recovery.

- [ ] **Step 8: Verify the next scheduled cloud cut**

Inspect the next due Chile hour and confirm its GitHub run created one `sent`
delivery row and exactly two Telegram photos without the PC scheduler.
