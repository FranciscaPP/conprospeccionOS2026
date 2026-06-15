create table if not exists public.ghl_calendars (
  id uuid primary key default gen_random_uuid(),
  ghl_calendar_id text not null unique,
  cliente_slug text references public.clientes(slug) on update cascade on delete set null,
  location_id text,
  nombre text,
  tipo_calendario text,
  tipo_evento text,
  activo boolean,
  team_members jsonb not null default '[]'::jsonb,
  raw_data jsonb not null default '{}'::jsonb,
  synced_at timestamptz not null default now(),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.reuniones add column if not exists ghl_calendar_id text;
alter table public.reuniones add column if not exists titulo text;
alter table public.reuniones add column if not exists direccion_reunion text;
alter table public.reuniones add column if not exists notas text;

create index if not exists reuniones_ghl_calendar_id_idx on public.reuniones(ghl_calendar_id);
create index if not exists ghl_calendars_cliente_slug_idx on public.ghl_calendars(cliente_slug);

drop trigger if exists trg_ghl_calendars_updated_at on public.ghl_calendars;
create trigger trg_ghl_calendars_updated_at
before update on public.ghl_calendars
for each row execute function public.set_updated_at();
