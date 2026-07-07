## Active product scope

The official product is the Streamlit application at `dashboard/app.py`.

Read `PROJECT_MASTER_CONTEXT.md` and `ACTIVE_WORKSPACE.md` before broad repository work.

Default active scope:
- `dashboard/`
- `shared/`
- `sync/`
- `supabase/`
- `mvp_setup/`
- `tests/`
- `docs/`

State as of 2026-07-03: client portals were removed from the repo and will
be rebuilt from scratch as projections of the internal panel
(`dashboard/pages/1_Seguimiento_Reuniones.py`). The only surviving
client-facing page is `19_BambuTech_Intelligence_Insight.py`, kept as a
reference/example.

Next.js, React, and Vercel are not current implementations. If Vercel is
reconsidered in the future, build it from scratch and recover only
explicitly selected business rules or UX decisions.

## Project map

Quick orientation so any agent or new person understands the repo without
crawling file by file:

- `dashboard/` — Streamlit app (the product). `app.py` is the entry point.
  - `dashboard/pages/` — Panel pages. The main one is
    `1_Seguimiento_Reuniones.py` (internal master panel). Also:
    `2_Clientes.py`, `9_SDRs.py`, `16_Client_Setup_OS.py`,
    `19_BambuTech_Intelligence_Insight.py` (reference),
    `20_GBS_Intelligence_Insight.py`.
  - `master_auth.py`, `portal_auth.py` — login / authentication.
  - `meeting_component.py`, `meeting_shared.py` — meeting-table UI and logic.
- `shared/` — reusable code. Key: `validacion.py` (the 7 official meeting
  states), `seguimiento.py`, `meeting_scope.py`, `config.py`,
  `cp_design.py` (charcoal + gold design system), `metas.py`, `planes.py`.
- `sync/` — data sync into Supabase (`scripts/`, `migrations/`, `queries/`)
  plus CI.
- `supabase/` — database: `migrations/` and `functions/` (edge functions).
- `mvp_setup/` — client setup / onboarding module (its own app).
- `tests/` — pytest suite.
- `docs/` — functional docs (see the meetings-panel RUNBOOK).

Data source of truth: the live Supabase database (the repo does not mirror
the full schema).
