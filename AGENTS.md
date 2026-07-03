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
