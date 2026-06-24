# Handoff para Codex — Grabaciones y calendario de GBS Logistics

> Objetivo: que Codex sepa **exactamente de dónde sacar** (a) los links de acceso a las
> grabaciones de las reuniones de GBS y (b) el link de acceso abierto al calendario
> maestro de GBS. Aquí están todas las fuentes con ruta y línea.

---

## 1. Link de acceso abierto al calendario maestro de GBS

**Fuente única de verdad:** [`docs/GBS_CALENDARIO_MAESTRO.md`](GBS_CALENDARIO_MAESTRO.md)

Calendario oficial: `sam@gbs-logistics.cl` (zona horaria America/Santiago).

| Tipo de acceso | Link |
|---|---|
| Calendario Google (vista) | `https://calendar.google.com/calendar/u/0?cid=c2FtQGdicy1sb2dpc3RpY3MuY2w` |
| **Embed público** (para incrustar / acceso abierto) | `https://calendar.google.com/calendar/embed?src=sam%40gbs-logistics.cl&ctz=America%2FSantiago` |
| ICS público (suscripción/sync) | `https://calendar.google.com/calendar/ical/sam%40gbs-logistics.cl/public/basic.ics` |

Notas operativas (mismas que el doc):
- Todas las reuniones GBS deben existir en este calendario maestro.
- El dashboard debe contrastar GHL/Supabase contra este calendario cuando falten reuniones.
- El **ICS privado NO se versiona**. Si se necesita como respaldo técnico, va en la
  variable de entorno local `GBS_MASTER_CALENDAR_PRIVATE_ICS`.
- Contexto adicional de la regla del calendario maestro:
  [`docs/GBS_LOGISTICS_OPERACION.md`](GBS_LOGISTICS_OPERACION.md) (líneas 3–16).

---

## 2. Links de acceso a las grabaciones de reuniones GBS

Las grabaciones son de **tl;dv** (graba los Google Meet). En la UI se muestran como
"Transcripción IA" / "Ver grabación", **sin exponer el proveedor**.

### 2.1 Fuente única de verdad (archivo de evidencia)

[`docs/data/gbs-meeting-evidence.json`](data/gbs-meeting-evidence.json) → array `items[]`.
Cada item tiene: `title`, `dateIso`, `meetingUrl` (Google Meet), `url` y `recordingUrl`
(tl;dv), más `summary` / `evidenceSummary` / `text` (evidencia IA).

Links actuales (al 2026-06-16):

| Reunión | Fecha | Google Meet | Grabación (recordingUrl, tl;dv) |
|---|---|---|---|
| MEDIZINATECHNIK SA – GBS | 2026-06-03 | `meet.google.com/wjb-szaq-viz` | `https://tldv.io/app/meetings/6a2b05b3d3bbcb0013c53f47/` |
| Vecchhiola SA – GBS | 2026-06-09 | `meet.google.com/szt-teod-qbt` | `https://tldv.io/app/meetings/6a281c88392af400131687e1/` |
| CRISPIERI – GBS | 2026-06-11 | `meet.google.com/swr-avgd-stq` | `https://tldv.io/app/meetings/6a204f966232c30013330c13/` |

### 2.2 Otras fuentes de evidencia que alimentan lo mismo
- [`docs/data/gbs-meetings.json`](data/gbs-meetings.json) — reuniones del calendario
  maestro (salida enriquecida del sync).
- [`docs/data/gbs-manual-meetings.json`](data/gbs-manual-meetings.json) — reuniones
  cargadas a mano.
- `docs/data/google-meet-transcripts/` — carpeta de transcripciones locales (`.txt`,
  `.md`, `.json`); si un `.json` trae `recordingUrl`, también se usa.

---

## 3. Cómo viajan los links (flujo dato por dato)

```
Calendario maestro (sam@gbs-logistics.cl)
        │  (agenda real de reuniones)
        ▼
docs/data/gbs-meetings.json  +  gbs-manual-meetings.json
        │
        │  scripts/sync-google-meet-evidence.mjs
        │   - cruza cada reunión contra docs/data/gbs-meeting-evidence.json
        │   - match por: código Meet (xxx-xxxx-xxx), fecha ISO, empresa, persona, email
        │   - arrastra recordingUrl + transcript + summary IA
        ▼
docs/data/gbs-meetings.json (enriquecido, con recordingUrl por reunión)
        │
        │  webhook tl;dv/Zapier (en producción)  →  app/api/meetings/evidence/tldv
        ▼
Supabase: public.reuniones.recording_url / transcript_url / ai_*
        │
        ▼
Dashboard Streamlit → botón "Ver grabación"
```

### 3.1 Script de matching evidencia→reunión
[`scripts/sync-google-meet-evidence.mjs`](../scripts/sync-google-meet-evidence.mjs)
- Entrada/salida configurable por env: `MEETINGS_INPUT`/`MEETINGS_OUTPUT`
  (`docs/data/gbs-meetings.json`), `MANUAL_MEETINGS`, `GOOGLE_MEET_EVIDENCE`,
  `GOOGLE_MEET_TRANSCRIPTS_DIR`.
- `meetCode()` (línea 25) extrae el código `xxx-xxxx-xxx` del link de Meet — es la clave
  fuerte de cruce.
- `scoreEvidence()` (línea 89) puntúa por código Meet (+20), email (+10), fecha (+8/+5),
  empresa y persona.

### 3.2 Webhook que escribe en Supabase
[`archive/app/api/meetings/evidence/tldv/route.ts`](../archive/app/api/meetings/evidence/tldv/route.ts)
(actualmente archivado; era `app/api/meetings/evidence/tldv/route.ts`).
- Recibe payload de tl;dv/Zapier: `recordingUrl`/`videoUrl`, `transcriptUrl`,
  `summary`/`aiSummary`, `bantDetected`, `aiConfidence`, etc.
- `buildPatch()` (línea 64) arma el PATCH → `recording_url`, `transcript_url`,
  `ai_summary`, `ai_evidence`, `ai_bant_detected`, `ai_recommendation`, `ai_confidence`.
- Hace match contra `public.reuniones` por:
  1. `ghl_appointment_id = eq.<appointmentId>` (preferente), o
  2. `direccion_reunion ilike *<códigoMeet>*` (fallback por link de Meet).

### 3.3 Columnas en Supabase
[`sync/supabase/migrations/022_add_ai_evidence_columns.sql`](../sync/supabase/migrations/022_add_ai_evidence_columns.sql)
agrega a `public.reuniones`: `recording_url`, `transcript_url`, `ai_summary`,
`ai_evidence`, `ai_bant_detected`, `ai_recommendation`, `ai_confidence`,
`ai_dispute_flag`.

### 3.4 Dónde se muestran en el dashboard
[`dashboard/pages/12_GBS_Validacion_Reuniones.py`](../dashboard/pages/12_GBS_Validacion_Reuniones.py)
- Lee `recording_url` y `transcript_url` desde `reuniones` y `seguimiento_reuniones`
  (Supabase). Select de campos en líneas ~176–197.
- `valor_evidencia(row, seg, "recording_url")` (línea ~650) y botón **"Ver grabación"**
  con `st.link_button` (líneas ~656–662). Si no hay link → "Grabación no disponible".
- El prototipo HTML también tenía el botón "Grabación":
  [`archive/components/meeting-drawer.tsx`](../archive/components/meeting-drawer.tsx) líneas 1043 y 1068.

---

## 4. Resumen para Codex (qué hacer)

- **Calendario abierto de GBS** → leer de `docs/GBS_CALENDARIO_MAESTRO.md`
  (embed/ICS/Google). No inventar; ese es el doc canónico.
- **Links de grabaciones** → leer de `docs/data/gbs-meeting-evidence.json`
  (`recordingUrl`). En runtime real viven en `public.reuniones.recording_url` de Supabase.
- Para **cruzar** una reunión con su grabación, usar el **código de Google Meet**
  (`xxx-xxxx-xxx`) como clave principal, luego fecha + empresa + email.
- Para **poblar Supabase** desde tl;dv, el endpoint es el webhook
  `app/api/meetings/evidence/tldv` (hoy en `archive/`).
