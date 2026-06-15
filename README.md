# Conprospeccion OS2026

Proyecto oficial del sistema operativo de Con Prospeccion.

La app principal vive en Next.js y se despliega en Vercel:

- Produccion: https://conprospeccion-os-2026.vercel.app
- Dashboard interno: `/internal/meeting-followup`
- Portal cliente: `/client/meeting-validation`

## Estructura

```txt
app/                 Next.js App Router y API routes
components/          UI compartida
lib/                 Tipos, reglas de negocio y mapeos de datos
sync/                Scripts heredados para sincronizar GHL, Supabase y reporting
supabase/            Migraciones y Edge Functions
dashboard/           Streamlit legacy de validacion y seguimiento
shared/              Configuracion Python compartida legacy
scripts/             Utilidades operativas
docs/                Documentacion historica y handoff tecnico
```

## Fuente de datos

El dashboard interno consume Supabase desde `app/api/internal/meetings`.

Fuente real:

- Supabase `public.reuniones`
- Supabase `public.clientes`
- Supabase `public.sdrs`
- GoHighLevel alimenta esas tablas mediante scripts `sync/` y webhook `supabase/functions/ghl-webhook`

Clientes activos del dashboard:

- Clickie
- GBS
- BambuTech

## Variables

Usar `.env.example` como plantilla. Los valores reales no se versionan.

Para desarrollo local de Next:

```txt
.env.local
```

Para produccion:

```txt
Vercel Project Settings -> Environment Variables
```

Variables minimas para el dashboard oficial:

```txt
SUPABASE_URL
SUPABASE_SECRET_KEY
```

Tambien se soportan estos alias para compatibilidad:

```txt
SUPABASE_SERVICE_ROLE_KEY
SUPABASE_SERVICE_KEY
SUPABASE_KEY
NEXT_PUBLIC_SUPABASE_URL
```

## Desarrollo

```bash
npm install
npm run dev
```

Build:

```bash
npm run build
```

## Sincronizacion

Los scripts heredados estan en `sync/scripts`.

Ejemplo de refresco completo:

```bash
python sync/scripts/sync_ghl.py --entity all
python sync/scripts/sync_meetings.py --start-date 2026-05-01 --end-date YYYY-MM-DD
```

## Datos pesados

Las bases locales Apollo/Snov no se versionan en GitHub.

Ruta local de trabajo:

```txt
C:\Users\Admin\OneDrive\Documents\Con Prospección\ConprospeccionOS\BASES_APOLLO&SNOV
```

Si esas bases se migran definitivamente, deben ir a una persistencia controlada como Supabase Storage, Drive o un bucket privado, no al repo.
