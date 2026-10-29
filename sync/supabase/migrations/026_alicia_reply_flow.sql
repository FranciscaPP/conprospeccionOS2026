-- Alicia · columnas del flujo de respuesta (borrador + objetivo + contacto GHL).
-- Aplicadas en producción vía alters; se documentan aquí para trazabilidad.
alter table public.alicia_email_threads
  add column if not exists pending_draft text,
  add column if not exists pending_draft_at timestamptz,
  add column if not exists pending_objetivo text,
  add column if not exists prospect_ghl_contact_id text;

-- Almacén de secretos de Alicia (credenciales para las Edge Functions).
-- Solo accesible con la service key (RLS activo, sin políticas para anon/authenticated).
create table if not exists public.alicia_secrets (
  name       text primary key,
  value      text not null,
  updated_at timestamptz not null default now()
);
alter table public.alicia_secrets enable row level security;
revoke all on public.alicia_secrets from anon, authenticated;
