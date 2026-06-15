# OS2026 operacion

Este repo es la fuente de verdad del proyecto nuevo.

## App oficial

- Vercel project: `conprospeccion-os-2026`
- Production URL: `https://conprospeccion-os-2026.vercel.app`
- Internal meeting follow-up: `/internal/meeting-followup`

## Variables

Los secretos reales viven solo en entornos privados:

- Local: `.env.local`
- Produccion: Vercel Project Settings -> Environment Variables
- Supabase Edge Functions: Supabase project secrets

No commitear `.env`, `.env.local`, exports CSV/XLSX ni bases locales.

Variables minimas para que el dashboard oficial lea reuniones:

```txt
SUPABASE_URL
SUPABASE_SECRET_KEY
```

Alias soportados por compatibilidad:

```txt
SUPABASE_SERVICE_ROLE_KEY
SUPABASE_SERVICE_KEY
SUPABASE_KEY
NEXT_PUBLIC_SUPABASE_URL
```

## Reuniones

El dashboard interno lee desde:

- `public.reuniones`
- `public.clientes`
- `public.sdrs`

Reglas actuales:

- Desde `2026-05-01`.
- Clientes activos: Clickie, GBS, BambuTech.
- Excluir cualquier registro con `TEST`.
- Duplicados por empresa o email: conservar la ultima fecha agendada.
- Campos faltantes se muestran como `Sin dato`.

## Refresco manual

Desde este repo:

```bash
python sync/scripts/sync_ghl.py --entity all
python sync/scripts/sync_meetings.py --start-date 2026-05-01 --end-date YYYY-MM-DD
```

## Refresco inmediato

La funcion `supabase/functions/ghl-webhook` es la pieza destinada a recibir eventos de GHL cuando una cita se crea o actualiza.

Para activarla faltan dos pasos operativos:

1. Configurar secrets de Supabase Edge Function con `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` y tokens GHL activos.
2. Configurar webhooks de appointment create/update en GoHighLevel para Clickie, GBS y BambuTech.

## Bases Apollo/Snov

Ruta local actual:

```txt
C:\Users\Admin\OneDrive\Documents\Con Prospección\ConprospeccionOS\BASES_APOLLO&SNOV
```

No se suben a GitHub por peso y datos sensibles. Si deben centralizarse, usar almacenamiento privado controlado.
